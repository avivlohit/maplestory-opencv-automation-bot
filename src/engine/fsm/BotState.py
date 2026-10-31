
from config.config_loader import config
from abc import ABC, abstractmethod
import time

class State(ABC):
    # Abstract interface constraint
    @abstractmethod
    def handle(self, context, state_data):
        pass


class PatrolState(State):
    '''Function: Anchor state / patrol state
    '''
    PATROL_TIMEOUT = config.get("auto_control_config.find_mob_time_threshold") # <-- Timeout in seconds for platform patrol before transitioning
    STUCK_CHECK_TIMEOUT = config.get("auto_control_config.stuck_check_time_threshold")
    def __init__(self):
        self.patrolling_timer = time.time() # <-- Timestamp of patrol start
        self.TOGGLE_PATROL_ACTION = config.get("auto_control_config.TOGGLE_PATROL_ACTION") # <-- Toggle patrol action
        self.TOGGLE_COMBAT_ACTION = config.get("auto_control_config.TOGGLE_COMBAT_ACTION") # <-- Toggle combat action
        self.TOGGLE_Stuck_ACTION = config.get("auto_control_config.TOGGLE_Stuck_ACTION")
        self.stuck_check_timer = time.time()

    def handle(self, context, state_data):
        # print("State: Platform patrol...")

        # Condition A: Transition to combat state if monsters found
        if state_data.mobs and self.TOGGLE_COMBAT_ACTION:
            context.change_state(CombatState())
            return None, None
        
        # Condition B: Transition to stuck check state if stationary for timeout
        elif time.time() - self.stuck_check_timer >= PatrolState.STUCK_CHECK_TIMEOUT:
            self.stuck_check_timer = time.time()
            if context.is_stuck():
                context.change_state(StuckState())
                return None, None

        # Condition C: Transition to pathfinding state (rope, jump point, etc.) on timeout
        elif time.time() - self.patrolling_timer > PatrolState.PATROL_TIMEOUT:
            context.change_state(PathfindState())
            return None, None
        
        # Continue patrol action if no monsters
        if self.TOGGLE_PATROL_ACTION :
            return context._enable_player_patrol()
    
class CombatState(State):
    '''Function: Combat state
    '''
    STUCK_CHECK_INTERVAL = 3

    def __init__(self):
        self.stuck_check_timer = time.time()

    def handle(self, context, state_data):

        if not state_data.mobs:
            context.reset_state()
            return None, None

        # Check if character is stuck
        if time.time() - self.stuck_check_timer >= self.STUCK_CHECK_INTERVAL: 
            self.stuck_check_timer = time.time()
            if context.is_stuck():
                context.change_state(StuckState())
                return None, None
            
        action, params = context._fk_that_mob(state_data)
        
        return action, params 
        


class StuckState(State):
    '''Function: Check if character is stuck
    '''
    STUCK_TIMEOUT = 1
    def __init__(self):
        self.stuck_timer = time.time()

    def handle(self, context, state_data):

        print("State: Checking if character is stuck...")
        if time.time() - self.stuck_timer > StuckState.STUCK_TIMEOUT:
            context.reset_state()
            return None, None
        return context._unstuck_player(state_data)   

class PathfindState(State):
    '''
    Routes movement methods: ropes, jumps, etc.
    '''
    def __init__(self):
        pass
    def handle(self, context, state_data):

        
        # TODO: Archived pending jump-grab state machine testing
        # Condition A: Detected nearby jump point (jump state check disabled)
        # nearest_jump_index = context._find_nearest_jump_point()
        # if nearest_jump_index is not None:
        #     print(f"Detected nearby jump point #{nearest_jump_index}, transitioning to JumpState")
        #     context.change_state(JumpState(nearest_jump_index))
        #     return None, None
        
        # Condition A: Detect vertical passage within platform
        if context._check_current_platform() is not None or context._check_vertical_passage() is not None:
            print("Detected within platform, transitioning to RopeState")
            context.change_state(RopeState())
            return None, None
        
        # Default: reset 
        context.reset_state()
        return None, None

# TODO: Archived pending jump-grab state machine testing

# class JumpState(State):
#     '''
#     Function:
#         Walks to specified single jump point coordinates (JumpLeft / JumpRight from YAML),
#         and executes jump in configured direction upon arrival.
#     '''
#     TIMEOUT = 5  # <-- Primary safety timeout: abandon jump if unreachable
#     NEXT_TIMEOUT = 5 # <-- Secondary safety timeout: max timeout for chained jumps
#     AIR_TIME = 1.0  # Air time wait duration

#     def __init__(self, jump_index):
#         self.jump_index = jump_index
#         self.start_time = time.time()
#         self.last_jump_index = None
#         # Flag
#         self.next_start_jump_time = None
#         self.has_jumped = False
#     def handle(self, context, state_data):

#         now = time.time()
#         # Timeout safety: abandon jump and return to patrol
#         if now  - self.start_time > JumpState.TIMEOUT:
#             print("Timeout moving to jump point, abandoning jump")
#             context.reset_state()
#             return None, None

#         print(f"State: Moving to jump point #{self.jump_index}...")
#         current_jump_index = context._check_jump_point()

#         # Case A: Already jumped, check if landing point is another jump point
#         if self.has_jumped:
            
#             if now  - self.jump_start_time > self.AIR_TIME: # <- 1s delay for character in midair
#                 # Check if standing on jump point
#                 new_jump_index = context._check_jump_point()
#                 self.last_jump_index = new_jump_index # Record previous jump point

#                 # Timeout protection for consecutive jumps
#                 if self.next_start_jump_time is not None and (now - self.next_start_jump_time > JumpState.NEXT_TIMEOUT):
#                     print("Timeout moving to jump point, abandoning jump")
#                     context.change_state(ClimbState())
#                     return None, None
                
#                 if new_jump_index is not None and self.last_jump_index != new_jump_index:

#                     print(f"Landed on next jump point: {new_jump_index}, staying in JumpState!")

                    
#                     # Update target to new jump point, reset state for next jump
#                     self.jump_index = new_jump_index
#                     self.start_time = now 
#                     self.has_jumped = False
#                     self.next_start_jump_time = now # <- Reset timestamp for consecutive jump sequence
#                     return None, None
#                 else:
#                     print("Not on jump point after landing, chained jumps ended, leaving JumpState")
#                     context.change_state(ClimbState())
#                     return None, None
            
#             return None, None 
            
#         # Case B: Reached target jump point, execute jump
#         if current_jump_index == self.jump_index:
#             print(f"Reached jump point #{self.jump_index}, executing jump!")
#             action, params = context._do_jump(self.jump_index)
#             self.has_jumped = True
#             self.jump_start_time = now   # Record jump start time
#             self.next_start_jump_tim = now # Base timestamp for chained jump timeout safety
#             return action, params
        
#         # Case C: Not yet arrived, continue moving toward jump point
#         return context._move_to_jump_point(self.jump_index)

class ClimbState(State):
    '''
    Function:
        Monitors Y-axis changes and resets keys.
        Handles rope climbing after jumping; executes subsequent jump if another jump point detected above.
    '''
    TIMEOUT = 5  # Rope climb timeout protection (prevents getting stuck on rope)

    def __init__(self):
        self.start_time = time.time()
        self.has_reached_rope = False

    def handle(self, context, state_data):
        now = time.time()
        
        # 1. Timeout protection: abandon and reset if climbing too long
        if now - self.start_time > ClimbState.TIMEOUT:
            print("Rope climbing timeout, abandoning and resetting state")
            context.reset_state()
            return None, None

        print("State: Climbing rope after jump...")
        
        # 2. Core check: rope climb action and state
        action, params = context._check_climbing_up()
        
        # # 3. Check if reached new jump point (JumpState disabled)
        # new_jump_index = context._check_jump_point()
        
        # if new_jump_index is not None:
        #     print(f"Detected new jump point ({new_jump_index})! Transitioning back to JumpState for chained jump")
        #     # Transition to JumpState with new jump_index
        #     context.change_state(JumpState(new_jump_index))
        #     return None, None

        # 4. Handle IDLE completion and reset
        if action == "IDLE":
            print("Climbing complete, no new jump point found, resetting state")
            context.reset_state()
            
        return action, params
                
class RopeState(State):

    TIMEOUT = 20  # <-- Safety timeout: 20s inactive indicates stuck state

    def __init__(self):
        self.start_time = time.time()

    def handle(self, context, state_data):

        # Check if player is already within vertical passage bounds
        current_passage_index = context._check_vertical_passage()
        current_play_indx =context._check_current_platform()
        print(f"Current platform: #{current_play_indx}; Current vertical passage: #{current_passage_index}")

        # Timeout safety: abandon rope climb and return to patrol
        if time.time() - self.start_time > RopeState.TIMEOUT:
            print("Timeout moving to rope, abandoning climb")
            context.reset_state()
            return None, None
        
        # If not in vertical passage, find nearest vertical passage
        if current_passage_index is None:  
            next_rope_index = context._find_nearest_verti_passage()

            if next_rope_index is None: # <- Reset if not found
                return context.reset_state()
            
            if next_rope_index != current_passage_index:
                return context._move_to_verti_passage(next_rope_index)

        elif current_passage_index is not None: # <- If inside vertical passage
            action, params = context._verti_movement(current_passage_index) # Vertical movement
            # Reached passage end, IDLE triggers state reset
            if action == "IDLE":
                context.reset_state()
                # nearest_jump_index = context._find_nearest_jump_point()
                # if nearest_jump_index is not None: # <- Jump point reached at end of rope
                #     context.change_state(PathfindState())
                        
            return action, params



class BotState():
    '''
    state manager    
    '''
    def __init__(self,owner):
        self.owner = owner
        self.initial_state_cls = PatrolState   # <-- Initial state class

        self.current_state = self.initial_state_cls()

    def change_state(self, new_state):
        print(f"[State Transition] {self.current_state.__class__.__name__} -> {new_state.__class__.__name__}")
        self.current_state = new_state

    def reset_state(self):
        '''Reset to default initial state class'''

        self.change_state(self.initial_state_cls())
        return self._reset_state()
    # Invocation
    def handle(self, state_data):
        result = self.current_state.handle(self, state_data)

        # Guard check: pad missing None if single return 
        if result is None:
            return None, None
        return result

    #==== Delegation helper methods
    def _enable_player_patrol(self):
        return self.owner._enable_player_patrol()

    def _fk_that_mob(self, state_data):
        return self.owner._fk_that_mob(state_data)
    
    def _unstuck_player(self, state_data):
        return self.owner._unstuck_player()
    
    def is_stuck(self):
        return self.owner.is_stuck()

    def _check_vertical_passage(self):
        return self.owner._check_vertical_passage()

    def _find_nearest_verti_passage(self):
            return self.owner._find_nearest_verti_passage()

    def  _move_to_verti_passage(self,index):
            return self.owner._move_to_verti_passage(index)

    def _verti_movement(self,index):
            return self.owner._verti_movement(index)
    def _check_current_platform(self):
            return self.owner._check_current_platform()
    def _reset_state(self):
            return self.owner._reset_state()
    
    #==== Single point jump (JumpLeft/JumpRight) delegation

    def _check_jump_point(self):
            return self.owner._check_jump_point()

    def _find_nearest_jump_point(self):
            return self.owner._find_nearest_jump_point()

    def _move_to_jump_point(self, jump_index):
            return self.owner._move_to_jump_point(jump_index)

    def _do_jump(self, jump_index):
            return self.owner._do_jump(jump_index)
    
    def _check_climbing_up(self):
            return self.owner._check_climbing_up()
    
    def _is_loc_y_change(self):
            return self.owner._is_loc_y_change()
