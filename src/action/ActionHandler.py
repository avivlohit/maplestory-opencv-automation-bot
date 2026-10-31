import src.action.KeyBoardController as kb
import logging  
from config.config_loader import config
import time
'''
Command Dispatcher
'''
class ActionHandler:
    def __init__(self):

        #State
        self.current_state = "PRESET"  
        self.current_info = None
        #Instance
        self.keyboard = kb.KeyBoard()
        #Flag
        self.is_Night_Lord = config.get("player_setting.auto_control_config.is_Night_Lord") # <-- Is Night Lord / Assassin class

    def execute_behavior(self, new_state, target_info=None):
        """
        Executes commands triggered by state changes.
        args:
            new_state (str): New state name
            target_info (dict): {"name": mob, "distance": distance, "direction": direction}
        """
        # Convert continuous state to pulse to prevent duplicate triggers
        if self.current_state != new_state or self.current_info != target_info:
            self.current_state = new_state
            self.current_info = target_info


        # Handle ATTACK state
        if self.current_state == "ATTACK":
            '''
            Note: Priority -> AOE -> Jump Attack | Normal Attack
            '''
            # Stop moving
            direction = self.current_info.get("direction")
            self.keyboard.stop_move()

            if direction == "AOE_ATTACK":
                self.keyboard.enable_aoe_attack()

            if self.is_Night_Lord:
                self.keyboard.enable_night_lord_attack(direction)
            else:
                self.keyboard.enable_attack(direction)

        # ====
        # ROPE State Commands
        # ====
        elif self.current_state == "ROPE" and self.current_info:

            direction = self.current_info.get("direction")

            if direction == "LEFT_UP":

                self.keyboard.grab_rope_to_left()
            elif direction == "RIGHT_UP":

                self.keyboard.grab_rope_to_right()
            elif direction == "LEFT_DOWN":

                self.keyboard.move_down_left()
            elif direction == "RIGHT_DOWN":

                self.keyboard.move_down_right()  

            elif direction =="UP":

                self.keyboard.enable_up(duration=1)
                self.keyboard.enable_jump()
            elif direction == "DOWN":

                self.keyboard.enable_down(duration=1)
                


        # ====
        # CLIMB State Commands
        # ====
        elif self.current_state == "CLIMB" :
            direction = self.current_info.get("direction")
            if direction == "UP":
                self.keyboard.climb_up()
            elif direction == "DOWN":
                self.keyboard.climb_down()

        # ====
        # Continuous Movement Commands (MOVE)
        # ====
        elif self.current_state == "MOVE" and self.current_info:
            direction = self.current_info.get("direction")

            if direction == "LEFT":
                self.keyboard.enable_move_left()
            elif direction == "RIGHT":
                self.keyboard.enable_move_right()
                
            self.keyboard.enable_pick_up()


        # ====
        # JUMP State Commands
        # ====
        elif self.current_state == "JUMP":   
            direction = self.current_info.get("direction")
            if direction == "LEFT":

                self.keyboard.jump_left()
            elif direction == "RIGHT":
                self.keyboard.jump_right()

            elif direction =="NONE":  # <- Jump over obstacles during platform movement
                self.keyboard.enable_jump()

            elif direction == "DOWN": # <- Jump down
                self.keyboard.jump_down()

        # ====
        # Short Distance Movement Commands (SMALL_MOVE)
        # ====
        elif self.current_state == "SMALL_MOVE":
            direction = self.current_info.get("direction")
            if direction == "M2LEFT":
                self.keyboard.move_left_to_jump()# <- Short distance left move for jump-grab
            elif direction == "M2RIGHT":
                self.keyboard.move_right_to_jump()# <- Short distance right move for jump-grab


        # ====
        # Jump-Grab State Commands (JUMP_GRAB)
        # ====
        elif self.current_state == "JUMP_GRAB":
            direction = self.current_info.get("direction")
            self.keyboard.stop_move()
            if direction == "LEFT": # <- Jump grab left

                self.keyboard.jump_left_grab()
            elif direction == "RIGHT": # <- Jump grab right

                self.keyboard.jump_right_grab()

            elif direction == "UP": # <- Jump grab up
                self.keyboard.jump_up_grab()




        elif self.current_state == "IDLE" and self.current_info:
            command = self.current_info.get("command")
            if command == "STOP_MOVE":

                # Stop moving
                self.keyboard.stop_move()
            if command == "RELEASE_ALL":
                # Release all keys
                self.keyboard.stop_move()
                self.keyboard.release_all()

        # Handle HEAL state
        elif self.current_state.startswith("HEAL") and self.current_info:
            # Health recovery state
            key = self.current_info.get("key")
            if key:
                self.keyboard.enable_use_item(key)
            else:
                logging.info(f"{self.current_state} triggered, but no hotkey is configured for this threshold")
                pass
        else:
            self.keyboard.enable_pick_up()
