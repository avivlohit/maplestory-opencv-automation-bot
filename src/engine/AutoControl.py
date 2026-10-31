"""Automatic game controller.

The controller receives a :class:`GameState` snapshot, evaluates the current
player/map/monster information, and returns an action for the input-control
layer in the form ``(action_name, parameters)``.

High-level state selection remains the responsibility of ``BotState``. This
class provides map geometry, movement helpers, combat decisions, and health
management integration.
"""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Any, Optional

import yaml

from config.config_loader import config
from src.engine.game_state import GameState
from src.engine.HealthManager import HealthManager
from src.engine.fsm.BotState import BotState


# Time allowed for the player to remain still at the end of a vertical move.
VERTI_MOVE_STAY_TIMEOUT = 0.25

# A player is considered stuck after this many seconds without a position change.
STUCK_TIMEOUT = 1.5

# Mini-map coordinate tolerance when checking whether the player reached an
# explicitly configured action point.
ACTION_POINT_X_TOLERANCE = 2.5
ACTION_POINT_Y_TOLERANCE = 2


ActionResult = tuple[Optional[str], Optional[dict[str, Any]]]


class AutoControl:
    """Make game decisions from incoming ``GameState`` snapshots."""

    # Convert route-file action names into directions understood by the
    # controller/input layer.
    JUMP_ACTION_DIRECTION = {
        "Jump": "NONE",
        "JumpDown": "DOWN",
        "M_LEFT": "M2LEFT",
        "M_RIGHT": "M2RIGHT",
        "JumpLeft": "LEFT",
        "JumpRight": "RIGHT",
    }

    def __init__(self) -> None:
        # Components
        self.health_manager = HealthManager()
        self.bot_state = BotState(self)

        # External configuration
        self.buffer = config.get("auto_control_config.buffer", 0)
        self.verti_move_threshold = config.get(
            "auto_control_config.verti_move_threshold", 10
        )
        self.ENABLE_AOE_ATTACK = config.get(
            "player_setting.auto_control_config.enable_AOE", False
        )
        self.AOE_THRESHOLD = config.get(
            "player_setting.auto_control_config.AOE_threshold", 1
        )
        self.player_attack_range = config.get(
            "player_setting.auto_control_config.attack_range", 0
        )

        # Patrol direction. The initial direction is random.
        self.search_direction = random.choice(("LEFT", "RIGHT"))

        # Map data. ``recored_data`` retains the original attribute spelling
        # because other parts of the project may already reference it.
        self.recored_data: list[dict[str, Any]] = []
        self.mini_map: Optional[Path] = None
        self.platforms: list[dict[str, tuple[float, float]]] = []
        self.vertical_passage: list[dict[str, tuple[float, float]]] = []
        self.action_points: list[dict[str, Any]] = []

        # Player and navigation state
        self.current_platform: Optional[int] = None
        self.current_vertical_passage: Optional[int] = None
        self.mini_player_loc: Optional[tuple[float, float]] = None
        self.last_player_loc: Optional[tuple[float, float]] = None
        self.current_verti_target: Optional[str] = None
        self.last_player_y_loc: Optional[float] = None

        # Timers
        self.detect_move_stuck_timer = 0.0
        self._verti_movement_timer: Optional[float] = None

        self._load_map_data()

    # ------------------------------------------------------------------
    # Map loading and geometry
    # ------------------------------------------------------------------

    def _load_map_data(self) -> None:
        """Load the selected map route and derive platforms/passages/actions."""
        try:
            map_name = config.get("quickly_choice_map")
            map_path_value = config.get(f"mini_map.{map_name}")

            if not map_name:
                raise ValueError("'quickly_choice_map' is not configured")
            if not map_path_value:
                raise ValueError(f"No mini-map path configured for {map_name!r}")

            self.mini_map = Path(map_path_value)
            yaml_path = self.mini_map.parent / f"{map_name}.yaml"
            if not yaml_path.is_file():
                raise FileNotFoundError(f"Map file does not exist: {yaml_path}")

            with yaml_path.open("r", encoding="utf-8") as file:
                route_data = yaml.safe_load(file)

            if not isinstance(route_data, list):
                raise ValueError("The map YAML root must be a list of route points")

            self._validate_map_data(route_data)
            self.recored_data = route_data

            self.platforms = self._find_platform()
            self.vertical_passage = self._find_vertical_passage()
            self.action_points = self._find_action_points()

            message = (
                f"{map_name} map loaded successfully: "
                f"{len(self.platforms)} platforms, "
                f"{len(self.vertical_passage)} vertical passages, "
                f"{len(self.action_points)} action points"
            )
            logging.info(message)
            print(message)

        except Exception:
            # Keep the controller in a predictable, empty-map state if loading
            # fails. The failure is logged with its traceback for debugging.
            logging.exception("Failed to load map data")
            self.recored_data = []
            self.platforms = []
            self.vertical_passage = []
            self.action_points = []

    @staticmethod
    def _validate_map_data(route_data: list[Any]) -> None:
        """Validate the minimum structure required by the map parsers."""
        for index, item in enumerate(route_data):
            if not isinstance(item, dict):
                raise ValueError(f"Map entry {index} must be a dictionary")
            if "action" not in item or "loc" not in item:
                raise ValueError(
                    f"Map entry {index} must contain 'action' and 'loc'"
                )

            location = item["loc"]
            if (
                not isinstance(location, (list, tuple))
                or len(location) != 2
                or not all(
                    isinstance(value, (int, float)) for value in location
                )
            ):
                raise ValueError(
                    f"Map entry {index} has an invalid location: {location!r}"
                )

    def _find_platform(self) -> list[dict[str, tuple[float, float]]]:
        """Build platform rectangles from consecutive pairs of ``walk`` points."""
        platforms: list[dict[str, tuple[float, float]]] = []
        index = 0

        # The route format represents a platform using two consecutive walk
        # points. Advancing by two preserves that existing file-format rule.
        while index < len(self.recored_data) - 1:
            current = self.recored_data[index]
            following = self.recored_data[index + 1]

            if current["action"] == "walk" and following["action"] == "walk":
                x1, y1 = current["loc"]
                x2, y2 = following["loc"]

                top = min(y1, y2) - 2
                bottom = max(y1, y2) + 6
                left = min(x1, x2)
                right = max(x1, x2)

                platforms.append({
                    "t_l": (left, top),
                    "b_r": (right, bottom),
                })
                index += 2
            else:
                index += 1

        return platforms

    def _find_vertical_passage(
        self,
    ) -> list[dict[str, tuple[float, float]]]:
        """Build rope-passage rectangles from consecutive pairs of ``rope`` points."""
        passages: list[dict[str, tuple[float, float]]] = []
        index = 0

        while index < len(self.recored_data) - 1:
            current = self.recored_data[index]
            following = self.recored_data[index + 1]

            if current["action"] == "rope" and following["action"] == "rope":
                x1, y1 = current["loc"]
                x2, y2 = following["loc"]

                top = min(y1, y2) - 2
                bottom = max(y1, y2) + 3
                left = min(x1, x2) - 3
                right = max(x1, x2) + 3

                passages.append({
                    "t_l": (left, top),
                    "b_r": (right, bottom),
                })
                index += 2
            else:
                index += 1

        return passages

    def _find_action_points(self) -> list[dict[str, Any]]:
        """Extract configured jump/action points from the route data."""
        action_points: list[dict[str, Any]] = []

        for item in self.recored_data:
            direction = self.JUMP_ACTION_DIRECTION.get(item["action"])
            if direction is None:
                continue

            x, y = item["loc"]
            action_points.append({
                "loc": (x, y),
                "direction": direction,
            })

        logging.info("Loaded %d action points", len(action_points))
        return action_points

    # ------------------------------------------------------------------
    # Main update loop
    # ------------------------------------------------------------------

    def run(self, state: GameState) -> ActionResult:
        """Process one game-state packet and return the action for this frame."""
        if state.mini_player_loc is not None:
            self.mini_player_loc = tuple(state.mini_player_loc)

        current_time = time.time()

        # Do not use ``if not self.mini_player_loc`` here: (0, 0) is a valid
        # coordinate and must not be treated as missing data.
        if self.mini_player_loc is None or not self.platforms:
            logging.warning(
                "Missing player position or platform data; skipping this frame"
            )
            return None, None

        # Refresh the platform every frame so the cached index cannot become stale.
        self.current_platform = self._check_current_platform()

        # Health actions have priority over normal state-machine decisions.
        health_action = self.health_manager.run(
            state.player_hp, state.player_mp, current_time
        )
        if health_action is not None:
            return health_action

        return self.bot_state.handle(state)

    # ------------------------------------------------------------------
    # Unstuck / recovery helpers
    # ------------------------------------------------------------------

    def _unstuck_player(self) -> ActionResult:
        """Try to recover when the player is outside known geometry or stuck."""
        self.current_platform = self._check_current_platform()
        passage_index = self._check_vertical_passage()

        # Retain the original recovery policy: random movement when the player
        # is not currently inside a known vertical passage.
        if passage_index is None:
            return self._random_move()

        if self.current_platform is None:
            platform_index = self._find_nearest_platform()
            if platform_index is not None:
                return self._move_to_platform(platform_index)
            return None, None

        return self._random_move()

    def _random_move(self) -> tuple[str, dict[str, Any]]:
        """Choose a random jump or horizontal movement action."""
        action = random.choice(("JUMP", "MOVE"))
        direction = random.choice(("RIGHT", "LEFT"))
        return self._pack_action(action, direction=direction)

    def _find_nearest_platform(self) -> Optional[int]:
        """Return the platform rectangle nearest to the player's current position."""
        if self.mini_player_loc is None or not self.platforms:
            return None

        px, py = self.mini_player_loc
        nearest_index: Optional[int] = None
        nearest_distance = float("inf")

        for index, platform in enumerate(self.platforms):
            left, top = platform["t_l"]
            right, bottom = platform["b_r"]

            # Distance from a point to a rectangle. The gap on an axis is zero
            # when the point is already within that axis' bounds.
            dx = max(left - px, 0, px - right)
            dy = max(top - py, 0, py - bottom)
            distance = (dx * dx + dy * dy) ** 0.5

            if distance < nearest_distance:
                nearest_distance = distance
                nearest_index = index

        return nearest_index

    def _move_to_platform(self, platform_index: int) -> ActionResult:
        """Move horizontally toward the selected platform."""
        if self.mini_player_loc is None:
            return None, None
        if not 0 <= platform_index < len(self.platforms):
            logging.warning("Invalid platform index: %s", platform_index)
            return None, None

        # If movement appears blocked, release movement briefly to create a pulse.
        stuck_action = self._give_pulse_to_stuck()
        if stuck_action is not None:
            return stuck_action

        px, _ = self.mini_player_loc
        platform_left = self.platforms[platform_index]["t_l"][0]
        if px < platform_left:
            return self._pack_action("MOVE", direction="RIGHT")
        return self._pack_action("MOVE", direction="LEFT")

    def _give_pulse_to_stuck(self) -> Optional[tuple[str, dict[str, Any]]]:
        """Send a stop pulse when the player's mini-map position stops changing."""
        if self.mini_player_loc is None:
            return None

        current_time = time.time()

        if self.last_player_loc is None:
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = current_time
            return None

        if self.last_player_loc != self.mini_player_loc:
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = current_time
            return None

        if current_time - self.detect_move_stuck_timer > STUCK_TIMEOUT:
            logging.warning("Player has not moved; sending a stop pulse")
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = current_time
            return self._pack_action("IDLE", command="STOP_MOVE")

        return None

    def _is_loc_y_change(self) -> bool:
        """Return whether the player's mini-map Y coordinate changed since last check."""
        if self.mini_player_loc is None:
            return False

        current_y = self.mini_player_loc[1]
        if self.last_player_y_loc is None:
            self.last_player_y_loc = current_y
            return True

        changed = self.last_player_y_loc != current_y
        self.last_player_y_loc = current_y
        return changed

    # ------------------------------------------------------------------
    # Vertical passage navigation
    # ------------------------------------------------------------------

    def _find_nearest_verti_passage(self) -> Optional[int]:
        """Find the nearest vertical passage reachable from the current platform."""
        if self.mini_player_loc is None or not self.vertical_passage:
            return None

        self.current_platform = self._check_current_platform()
        if self.current_platform is None:
            return None

        px, py = self.mini_player_loc
        platform = self.platforms[self.current_platform]
        platform_left, platform_top = platform["t_l"]
        platform_right, platform_bottom = platform["b_r"]

        reachable_candidates: list[int] = []

        for index, passage in enumerate(self.vertical_passage):
            passage_left, passage_top = passage["t_l"]
            passage_right, passage_bottom = passage["b_r"]

            x_overlap = not (
                passage_right < platform_left or passage_left > platform_right
            )
            y_touches = (
                platform_top <= passage_top <= platform_bottom
                or platform_top <= passage_bottom <= platform_bottom
            )

            if x_overlap and y_touches:
                reachable_candidates.append(index)

        if not reachable_candidates:
            logging.debug("No reachable vertical passage found on this platform")
            return None

        nearest_index: Optional[int] = None
        nearest_distance = float("inf")

        for index in reachable_candidates:
            passage = self.vertical_passage[index]
            left, top = passage["t_l"]
            right, bottom = passage["b_r"]

            dx = max(left - px, 0, px - right)
            dy = max(top - py, 0, py - bottom)
            distance = (dx * dx + dy * dy) ** 0.5

            if distance < nearest_distance:
                nearest_distance = distance
                nearest_index = index

        return nearest_index

    def _move_to_verti_passage(self, verti_passage_index: int) -> ActionResult:
        """Move into a vertical passage, executing a nearby plain-jump point first."""
        if self.mini_player_loc is None:
            return None, None
        if not 0 <= verti_passage_index < len(self.vertical_passage):
            logging.warning("Invalid vertical-passage index: %s", verti_passage_index)
            return None, None

        px, py = self.mini_player_loc

        # A plain jump point may be needed to clear terrain before reaching the rope.
        for point in self.action_points:
            jx, jy = point["loc"]
            at_action_point = (
                abs(jx - px) <= ACTION_POINT_X_TOLERANCE
                and abs(jy - py) <= ACTION_POINT_Y_TOLERANCE
            )
            if at_action_point and point["direction"] == "NONE":
                return self._pack_action("JUMP", direction="NONE")

        current_passage = self._check_vertical_passage()
        if current_passage == verti_passage_index:
            return self._pack_action("IDLE", command="RELEASE_ALL")

        stuck_action = self._give_pulse_to_stuck()
        if stuck_action is not None:
            return stuck_action

        passage_left = self.vertical_passage[verti_passage_index]["t_l"][0]
        if px < passage_left:
            return self._pack_action("MOVE", direction="RIGHT")
        return self._pack_action("MOVE", direction="LEFT")

    # ------------------------------------------------------------------
    # Patrol and combat
    # ------------------------------------------------------------------

    def _enable_player_patrol(self) -> ActionResult:
        """Patrol left and right while keeping the player inside the platform."""
        if self.mini_player_loc is None:
            return None, None

        px, py = self.mini_player_loc
        current_platform_index = self._check_current_platform()

        # Handle configured action points before ordinary patrol movement.
        for point in self.action_points:
            jump_x, jump_y = point["loc"]
            at_action_point = (
                abs(jump_x - px) <= ACTION_POINT_X_TOLERANCE
                and abs(jump_y - py) <= ACTION_POINT_Y_TOLERANCE
            )
            if not at_action_point:
                continue

            direction = point["direction"]
            if direction in ("NONE", "DOWN", "LEFT", "RIGHT"):
                return self._pack_action("JUMP", direction=direction)
            if direction in ("M2LEFT", "M2RIGHT"):
                return self._pack_action("SMALL_MOVE", direction=direction)

        if current_platform_index is None:
            self.current_platform = None
            return None, None

        self.current_platform = current_platform_index
        platform = self.platforms[current_platform_index]
        left_bound = platform["t_l"][0]
        right_bound = platform["b_r"][0]

        if px <= left_bound + self.buffer:
            self.search_direction = "RIGHT"
        elif px >= right_bound - self.buffer:
            self.search_direction = "LEFT"

        return self._pack_action("MOVE", direction=self.search_direction)

    def _fk_that_mob(self, state: GameState) -> ActionResult:
        """Find the nearest visible mob; attack it or move toward it."""
        if state.player_center_loc is None or state.roi_BBOX is None:
            return None, None

        player_x, _ = state.player_center_loc
        best_target: Optional[dict[str, Any]] = None
        total_mobs = 0
        min_distance = float("inf")

        for mob_name, mob_details in (state.mobs or []):
            for mob_detail in mob_details:
                total_mobs += 1
                # Mob coordinates are ROI-relative; convert them to screen coordinates.
                mob_x = mob_detail["top_left"][0] + state.roi_BBOX.x1
                distance = abs(player_x - mob_x)
                direction = "RIGHT" if player_x < mob_x else "LEFT"

                if distance < min_distance:
                    min_distance = distance
                    best_target = {
                        "name": mob_name,
                        "distance": distance,
                        "direction": direction,
                    }

        # No visible targets: do not index best_target or issue a move toward it.
        if best_target is None:
            return None, None

        if best_target["distance"] <= self.player_attack_range:
            if self.ENABLE_AOE_ATTACK and total_mobs >= self.AOE_THRESHOLD:
                aoe_command = {
                    "name": None,
                    "distance": None,
                    "direction": "AOE_ATTACK",
                }
                return "ATTACK", aoe_command

            logging.info(
                "Target %s is in attack range (distance: %.1f, direction: %s)",
                best_target["name"],
                best_target["distance"],
                best_target["direction"],
            )
            return "ATTACK", best_target

        if self.current_platform is None:
            return self._pack_action("IDLE", command="STOP_MOVE")

        left_bound, right_bound = (
            self.platforms[self.current_platform]["t_l"][0],
            self.platforms[self.current_platform]["b_r"][0],
        )
        mini_player_x = (
            self.mini_player_loc[0] if self.mini_player_loc is not None else None
        )

        if mini_player_x is not None and mini_player_x <= left_bound + self.buffer:
            self.search_direction = "RIGHT"
            return self._pack_action("MOVE", direction="RIGHT")
        if mini_player_x is not None and mini_player_x >= right_bound - self.buffer:
            self.search_direction = "LEFT"
            return self._pack_action("MOVE", direction="LEFT")

        return self._pack_action("MOVE", direction=best_target["direction"])

    # ------------------------------------------------------------------
    # Climbing
    # ------------------------------------------------------------------

    def _verti_movement(self, index: int) -> ActionResult:
        """Choose rope-grab/climb actions and release controls at passage endpoints."""
        if self.mini_player_loc is None:
            return None, None
        if not 0 <= index < len(self.vertical_passage):
            logging.warning("Invalid vertical-passage index: %s", index)
            return None, None

        now = time.time()
        if self._verti_movement_timer is None:
            self._verti_movement_timer = now

        passage = self.vertical_passage[index]
        px, py = self.mini_player_loc

        top = passage["t_l"][1]
        bottom = passage["b_r"][1]
        middle_y = (top + bottom) // 2
        center_x = (
            passage["t_l"][0]
            + (passage["b_r"][0] - passage["t_l"][0]) // 2
        )

        if self.current_verti_target is None:
            self.current_verti_target = "UP" if py > middle_y else "DOWN"

        top_tolerance = 5
        bottom_tolerance = 5
        time_threshold = 0.3

        # IMPORTANT: read/update the previous Y coordinate once per frame.
        # The old code called _is_loc_y_change() several times in one decision,
        # so the first call consumed the change and later calls saw False.
        y_changed = self._is_loc_y_change()
        if y_changed:
            self._verti_movement_timer = now

        elapsed = now - self._verti_movement_timer

        if self.current_verti_target == "UP":
            # If vertical movement has stopped for long enough, assume the upper
            # endpoint has been reached and release the held controls.
            if elapsed > time_threshold and not y_changed:
                self.current_verti_target = None
                self._verti_movement_timer = None
                self.last_player_loc = None
                logging.info("Reached the upper end of the vertical passage")
                return self._pack_action("IDLE", command="RELEASE_ALL")

            # At the lower end, move sideways to align with the rope before climbing.
            if bottom - bottom_tolerance <= py <= bottom and not y_changed:
                direction = "RIGHT_UP" if px <= center_x else "LEFT_UP"
                return self._pack_action("ROPE", direction=direction)

            return self._pack_action("CLIMB", direction="UP")

        if self.current_verti_target == "DOWN":
            if elapsed > time_threshold and not y_changed:
                # The player has stopped moving vertically; release the controls.
                self.current_verti_target = None
                self._verti_movement_timer = None
                self.last_player_loc = None
                logging.info("Reached the lower end of the vertical passage")
                return self._pack_action("IDLE", command="RELEASE_ALL")

            # At the upper end, move sideways to align with the rope before descending.
            if top <= py <= top + top_tolerance:
                direction = "RIGHT_DOWN" if px <= center_x else "LEFT_DOWN"
                return self._pack_action("ROPE", direction=direction)

            return self._pack_action("CLIMB", direction="DOWN")

        return None, None

    def is_stuck(self) -> bool:
        """Return True if the player's position has not changed for 1.5 seconds."""
        if self.mini_player_loc is None:
            return False

        now = time.time()

        if self.last_player_loc is None:
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = now
            return False

        if self.last_player_loc != self.mini_player_loc:
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = now
            return False

        return now - self.detect_move_stuck_timer > STUCK_TIMEOUT

    # ------------------------------------------------------------------
    # Position checks
    # ------------------------------------------------------------------

    def _check_vertical_passage(self) -> Optional[int]:
        """Return the index of the vertical passage containing the player."""
        if self.mini_player_loc is None:
            return None

        px, py = self.mini_player_loc
        for index, passage in enumerate(self.vertical_passage):
            left, top = passage["t_l"]
            right, bottom = passage["b_r"]
            if left <= px <= right and top <= py <= bottom:
                return index

        return None

    def _check_current_platform(self) -> Optional[int]:
        """Return the index of the platform containing the player."""
        if self.mini_player_loc is None:
            return None

        px, py = self.mini_player_loc
        for index, platform in enumerate(self.platforms):
            left, top = platform["t_l"]
            right, bottom = platform["b_r"]
            if left <= px <= right and top <= py <= bottom:
                return index

        return None

    def _check_climbing_up(self) -> ActionResult:
        """Continue climbing upward until vertical movement stops at the top."""
        if self.mini_player_loc is None:
            return None, None

        now = time.time()
        if self._verti_movement_timer is None:
            self._verti_movement_timer = now

        # Only inspect the Y-coordinate once per invocation (one decision frame).
        y_changed = self._is_loc_y_change()
        if y_changed:
            self._verti_movement_timer = now

        if (
            now - self._verti_movement_timer > VERTI_MOVE_STAY_TIMEOUT
            and not y_changed
        ):
            self.current_verti_target = None
            self._verti_movement_timer = None
            self.last_player_loc = None
            logging.info("Reached the upper end of the vertical passage")
            return self._pack_action("IDLE", command="RELEASE_ALL")

        return self._pack_action("CLIMB", command="UP")

    # ------------------------------------------------------------------
    # Action output / debug helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pack_action(action_type: str, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        """Package an action name and its parameters for the control module."""
        return action_type, kwargs

    def get_debug_geometry(self) -> list[dict[str, Any]]:
        """Return platform, passage, and action-point geometry for GameBot debug UI."""
        return [
            {
                "label": "platform",
                "color": (193, 255, 193),
                "boxes": [
                    (platform["t_l"], platform["b_r"])
                    for platform in self.platforms
                ],
            },
            {
                "label": "vertical_passage",
                "color": (0, 100, 0),
                "boxes": [
                    (passage["t_l"], passage["b_r"])
                    for passage in self.vertical_passage
                ],
            },
            {
                "label": "jump",
                "color": (3, 193, 69),
                "circle": [point["loc"] for point in self.action_points],
            },
        ]

    def _reset_state(self) -> tuple[str, dict[str, Any]]:
        """Release all held keys; used by the state machine during transitions."""
        return self._pack_action("IDLE", command="RELEASE_ALL")
