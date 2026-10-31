import time
import interception
import logging
from config.config_loader import config
import threading
import random
class KeyBoard:
    def __init__(self):
        # Capture and bind devices
        interception.auto_capture_devices(keyboard=True, mouse=True)

        # Track keys currently held down; release_all uses this set dynamically rather than a fixed list
        self._pressed_keys = set()
        self._pressed_keys_lock = threading.Lock()

        #states and lock
        self._release_all_lock = threading.Lock()
        self._attack_lock = threading.Lock()
        self._night_lord_attack_lock = threading.Lock()
        self._move_lock = threading.Lock()
        self._item_lock = threading.Lock()
        self._pick_up_lock = threading.Lock()
        self._jump_lock = threading.Lock()
        self._down_lock = threading.Lock()
        self._up_lock = threading.Lock()
        self._down_lock = threading.Lock()
        self._right_lock = threading.Lock()
        self._left_lock = threading.Lock()
        self._move_down_right_lock = threading.Lock()
        self._move_down_left_lock = threading.Lock()
        self._jump_left_lock = threading.Lock()
        self._jump_right_lock = threading.Lock()
        self._jump_left_grab_lock = threading.Lock()
        self._jump_right_grab_lock =threading.Lock()
        self._jump_down_lock = threading.Lock()
        self._jump_up_grab_lock = threading.Lock()

        self._status_release_all = False
        self._status_attack = False
        self._status_night_lord_attack = False #Night_Lord_attack
        self._status_jump = False
        self._status_up = False
        self._status_down = False
        self._status_right = False
        self._status_left = False
        self._status_item = False  
        self._pick_up = False
        self._status_move_down_right = False
        self._status_move_down_left = False
        self._status_jump_left = False
        self._status_jump_right = False
        self._status_jump_left_grab = False 
        self._status_jump_right_grab = False
        self._status_jump_up_grab = False
        self._status_jump_down = False

        #key value
        self.attack_key = config.get("keyboard.attack")
        self.aoe_attack_key = config.get("keyboard.aoe_attack")
        self.up_key = config.get("keyboard.up")
        self.down_key = config.get("keyboard.down")
        self.left_key = config.get("keyboard.left")
        self.right_key = config.get("keyboard.right")
        self.pick_up_key = config.get("keyboard.pick_up")
        self.jump_key = config.get("keyboard.jump")
        #action logging
        self._current_move = None # <- Record current movement command

    ''' 
    Low-level key wrapper: All key_down / key_up pass through here to track pressed state and enable unified release.
    '''

    def _key_down(self, key):
        interception.key_down(key)
        with self._pressed_keys_lock:
            self._pressed_keys.add(key)

    def _key_up(self, key):
        interception.key_up(key)
        with self._pressed_keys_lock:
            self._pressed_keys.discard(key)

    ''' Attack Behaviors '''
    def _attack_command(self, direction):
        try: 
            key = self.right_key if direction == "RIGHT" else self.left_key
            with self._move_lock:
                self._key_down(key)
                self._key_up(key)
            self._key_down(self.attack_key)
            time.sleep(0.3)
        except Exception as e:
            logging.error(f"Error during attack action: {e}")
            
        finally:
            self._key_up(self.attack_key)
            with self._attack_lock:
                self._status_attack = False


    def enable_attack(self,direction):
        '''Normal attack'''
        with self._attack_lock:
            if self._status_attack:
                # Attack in progress, skip duplicate command
                return
            self._status_attack = True
            threading.Thread(target=self._attack_command,args=(direction,),daemon=True).start() 

    def _aoe_attack_command(self):
        try: 
            self._key_down(self.aoe_attack_key)
            time.sleep(0.3)
        except Exception as e:
            logging.error(f"Error during attack action: {e}")
            
        finally:
            self._key_up(self.aoe_attack_key)
            with self._attack_lock:
                self._status_attack = False

    def enable_aoe_attack(self):
        '''AOE attack'''
        with self._attack_lock:
            if self._status_attack:
                # Attack in progress, skip duplicate command
                return
            self._status_attack = True
            threading.Thread(target=self._aoe_attack_command, daemon=True).start()


    def _night_lord_att_command(self, direction):
        try: 
            key = self.right_key if direction == "RIGHT" else self.left_key
            with self._move_lock:
                self._key_down(key)
                self._key_up(key)

            time.sleep(0.1)

            self._key_down(self.jump_key)
            self._key_down(self.attack_key)
            time.sleep(0.3)
        except Exception as e:
            logging.error(f"Error during attack action: {e}")
            
        finally:
            self._key_up(self.attack_key)
            self._key_up(self.jump_key)
            with self._attack_lock:
                self._status_night_lord_attack = False

    def enable_night_lord_attack(self,direction):
        '''
        Night Lord / Jump attack
        '''
        with self._night_lord_attack_lock:
            if self._status_night_lord_attack:
                # Attack in progress, skip duplicate command
                return
            self._status_night_lord_attack = True
            threading.Thread(target=self._night_lord_att_command,args=(direction,),daemon=True).start()
            
    ''' Movement Behaviors '''

    def _press_direction(self, direction):
        """
        Controls key down for left/right direction keys with mutual exclusion
        """
        with self._move_lock:
            self._press_direction_locked(direction)

    def _press_direction_locked(self, direction):
        """
        Locked helper for pressing direction keys
        """
        if self._current_move == direction:
            return
        if self._current_move == "LEFT":
            self._key_up(self.left_key)
        elif self._current_move == "RIGHT":
            self._key_up(self.right_key)

        key = self.left_key if direction == "LEFT" else self.right_key
        self._key_down(key)
        self._current_move = direction

    def _release_direction(self):
        """Controls release for left/right direction keys with mutual exclusion"""
        with self._move_lock:
            self._release_direction_locked()

    def _release_direction_locked(self):
        """Locked helper for releasing direction keys"""
        if self._current_move is not None:
            try:
                self._key_up(self.left_key)
                self._key_up(self.right_key)
            except Exception as e:
                logging.error(f"Error releasing movement keys: {e}")
            finally:
                self._current_move = None

    def enable_move_right(self):
        self._press_direction("RIGHT")

    def enable_move_left(self):
        self._press_direction("LEFT")

    def _jump_command(self,duration):
        try:
            self._key_down(self.jump_key)
            time.sleep(duration)
        finally:
            self._key_up(self.jump_key)
            if self._status_jump:
                self._status_jump = False

    def enable_jump(self,duration=0.1):
        '''Action: Simple jump'''
        with self._jump_lock:
            if self._status_jump:
                return
        self._status_jump = True
        threading.Thread(target=self._jump_command,args=(duration,),daemon=True).start() 

    def _down_command(self,duration):
        try:
            self._key_down(self.down_key)
            time.sleep(duration)
        finally:
            self._key_up(self.down_key)
            if self._status_down:
                self._status_down = False

    def enable_down(self,duration=0.1):
        with self._down_lock:
            if self._status_down:
                return
            self._status_down = True
        threading.Thread(target=self._down_command, args=(duration,), daemon=True).start()

    def _up_command(self,duration):
        try:
            self._key_down(self.up_key)
            time.sleep(duration)
        finally:
            self._key_up(self.up_key)
            if self._status_up:
                self._status_up = False

    def enable_up(self,duration=0.1):

        with self._up_lock:
            if self._status_up:
                return
            self._status_up = True
        threading.Thread(target=self._up_command,args=(duration,), daemon=True).start()

    def _right_command(self,duration):
        with self._move_lock:
            try:
                self._press_direction_locked("RIGHT")
                time.sleep(duration)
            finally:
                self._release_direction_locked()
                if self.right_key:
                    self._status_right = False

    def enable_right(self,duration=0.1):
        with self._right_lock:
            if self._status_right:
                return
            self._status_right = True
        threading.Thread(target=self._right_command,args=(duration,), daemon=True).start()

    def _left_command(self,duration):
        with self._move_lock:
            try:
                self._press_direction_locked("LEFT")
                time.sleep(duration)
            finally:
                self._release_direction_locked()
                if self.left_key:
                    self._status_left = False

    def enable_left(self,duration=0.1):
        with self._left_lock:
            if self._status_left:
                return
            self._status_left = True
        threading.Thread(target=self._left_command,args=(duration,), daemon=True).start()

    '''Vertical Movement'''
    # Temporary implementation, to be refined
    
    def grab_rope_to_left(self):
        '''Jump left to grab rope'''
        self.enable_left()
        time.sleep(0.03)
        self.enable_jump()
        self.enable_up(duration=0.5)

    def grab_rope_to_right(self):
        '''Jump right to grab rope'''
        self.enable_right()
        time.sleep(0.03)
        self.enable_jump()
        self.enable_up(duration=0.5)

    def _move_down_right_command(self, duration):
        with self._move_lock:
            try:
                self._press_direction_locked("RIGHT")   # Allow character brief step to face right
                time.sleep(0.03)
                self._key_down(self.down_key)             # Press down to slide down and grab rope
                time.sleep(duration)
            except Exception as e:
                logging.error(f"Error during slide down action: {e}")
            finally:
                self._key_up(self.down_key)
                self._release_direction_locked()
        with self._move_down_right_lock:
            self._status_move_down_right = False

    def move_down_right(self, duration=0.5):
        '''Move down-right'''
        with self._move_down_right_lock:
            if self._status_move_down_right:
                return
            self._status_move_down_right = True
        threading.Thread(target=self._move_down_right_command, args=(duration,), daemon=True).start()

    def _move_down_left_command(self, duration):
        with self._move_lock:
            try:
                self._press_direction_locked("LEFT")    # Allow character brief step to face left
                time.sleep(0.03)
                self._key_down(self.down_key)             # Press down to slide down and grab rope
                time.sleep(duration)
            except Exception as e:
                logging.error(f"Error during slide down action: {e}")
            finally:
                self._key_up(self.down_key)
                self._release_direction_locked()
        with self._move_down_left_lock:
            self._status_move_down_left = False

    def move_down_left(self, duration=0.5):
        '''Move down-left'''
        with self._move_down_left_lock:
            if self._status_move_down_left:
                return
            self._status_move_down_left = True
        threading.Thread(target=self._move_down_left_command, args=(duration,), daemon=True).start()

    #======
    # Jump Grab
    #=====

    def jump_left_grab_command(self, duration, delay):

        with self._move_lock:               # Lock movement during action to prevent interference with other commands
            try:
                self._press_direction_locked("LEFT")
                time.sleep(delay)          # Small delay so direction key registers before jump
                self._key_down(self.jump_key)
                time.sleep(duration)
                self._key_down(self.up_key)
            except Exception as e:
                logging.error(f"Error during jump left action: {e}")
            finally:
                self._key_up(self.jump_key)
                time.sleep(1)  # Hold longer to maintain direction
                self._release_direction_locked()   # Release left key and reset _current_move = None
                time.sleep(0.2)             # Wait for jump completion
                self._key_down(self.up_key)
        with self._jump_left_grab_lock:
            self._status_jump_left_grab = False

    def jump_left_grab(self, duration=0.02, delay=0.02):

        with self._jump_left_grab_lock:
            self.stop_move()  # Stop movement
            if self._status_jump_left_grab:
                return
            self._status_jump_left_grab = True
        threading.Thread(target=self.jump_left_grab_command, args=(duration, delay), daemon=True).start()

    def jump_right_grab_command(self, duration, delay):

        with self._move_lock:               # Lock movement during action to prevent interference with other commands
            try:
                self._press_direction_locked("RIGHT")
                time.sleep(delay)          # Small delay so direction key registers before jump
                self._key_down(self.jump_key)
                time.sleep(duration)
                self._key_down(self.up_key)
            except Exception as e:
                logging.error(f"Error during jump right action: {e}")
            finally:
                self._key_up(self.jump_key)
                time.sleep(1) # Hold longer to maintain direction
                self._release_direction_locked()   # Release right key and reset _current_move = None
                time.sleep(0.2)             # Wait for jump completion
                self._key_down(self.up_key)
        with self._jump_right_grab_lock:
            self._status_jump_right_grab = False

    def jump_right_grab(self, duration=0.02, delay=0.02):

        with self._jump_right_grab_lock:
            self.stop_move()  # Stop movement
            if self._status_jump_right_grab:
                return
            self._status_jump_right_grab = True
        threading.Thread(target=self.jump_right_grab_command, args=(duration, delay), daemon=True).start()

    def _jump_up_grab_command(self, duration, delay):
        '''Jump up (composite action: tap up -> hold up -> small delay -> jump)'''
        try:
            # Tap up once to interact/trigger portal
            self._key_down(self.up_key)
            self._key_up(self.up_key)

            self._key_down(self.up_key)
            time.sleep(delay)          # Small delay so up key registers before jump
            self._key_down(self.jump_key)
            time.sleep(duration)
        except Exception as e:
            logging.error(f"Error during jump up action: {e}")
        finally:           # Wait for jump completion
            self._key_up(self.jump_key)


            with self._jump_up_grab_lock:
                self._status_jump_up_grab = False

    def jump_up_grab(self, duration=0.02, delay=0.02):
        '''Jump up external interface'''
        with self._jump_up_grab_lock:
            self.stop_move()  # Stop movement
            time.sleep(0.1)
            if self._status_jump_up_grab:
                return
            self._status_jump_up_grab = True
        threading.Thread(target=self._jump_up_grab_command, args=(duration, delay), daemon=True).start()

    def move_left_to_jump(self,delay=0.4):
        '''Small left shift for jump state'''
        with self._move_lock:
            self._press_direction_locked("LEFT")
            time.sleep(delay)
            self._release_direction_locked()

    def move_right_to_jump(self,delay=0.4):
        '''Small right shift for jump state'''
        with self._move_lock:
            self._press_direction_locked("RIGHT")
            time.sleep(delay)
            self._release_direction_locked()
    #======
    # Single Jump
    #=====


    def _jump_down_command(self, duration=0.1, delay=0.03):
        '''Jump down (composite action: hold down -> small delay -> jump)'''
        try:
            self._key_down(self.down_key)
            time.sleep(delay)          # Small delay so down key registers before jump
            self._key_down(self.jump_key)
            time.sleep(duration)
        except Exception as e:
            logging.error(f"Error during jump down action: {e}")
        finally:
            self._key_up(self.jump_key)
            self._key_up(self.down_key)
            time.sleep(0.2)             # Wait for jump completion

            with self._jump_down_lock:
                self._status_jump_down = False

    def jump_down(self, duration=0.1, delay=0.03):
        '''Action: Jump down'''
        with self._jump_down_lock:
            if self._status_jump_down:
                return
            self._status_jump_down = True
        threading.Thread(target=self._jump_down_command, args=(duration, delay), daemon=True).start()

    def _jump_left_command(self, duration=0.1, delay=0.03):
        '''Jump left'''
        with self._move_lock:
            try:
                self._press_direction_locked("LEFT")
                time.sleep(delay)          # Small delay so direction key registers before jump
                self._key_down(self.jump_key)
                time.sleep(duration)

            except Exception as e:
                logging.error(f"Error during jump left action: {e}")
            finally:
                self._key_up(self.jump_key)
                self._release_direction_locked()
                time.sleep(0.2)             # Wait for jump completion

        with self._jump_left_lock:
            self._status_jump_left = False

    def jump_left(self, duration=0.1, delay=0.03):
        '''Jump left (composite action: direction key -> delay -> jump key)'''
        with self._jump_left_lock:
            if self._status_jump_left:
                return
            self._status_jump_left = True
        threading.Thread(target=self._jump_left_command, args=(duration, delay), daemon=True).start()



    def _jump_right_command(self, duration=0.1, delay=0.03):
        '''Jump right'''
        with self._move_lock:
            try:
                self._press_direction_locked("RIGHT")
                time.sleep(delay)          # Small delay so direction key registers before jump
                self._key_down(self.jump_key)
                time.sleep(duration)

            except Exception as e:
                logging.error(f"Error during jump right action: {e}")
            finally:
                self._key_up(self.jump_key)
                self._release_direction_locked()
                time.sleep(0.2)             # Wait for jump completion

        with self._jump_right_lock:
            self._status_jump_right = False

    def jump_right(self, duration=0.1, delay=0.03):
        '''Jump right (composite action: direction key -> delay -> jump key)'''
        with self._jump_right_lock:
            if self._status_jump_right:
                return
            self._status_jump_right = True
        threading.Thread(target=self._jump_right_command, args=(duration, delay), daemon=True).start()

    #======
    # Climb Up / Down
    #=====

    def climb_up(self):
        self._key_down(self.up_key)

    def climb_down(self):
        '''Action: Jump off rope downwards'''
        direction_key = random.choice([self.right_key, self.left_key])  # Randomize direction for natural behavior
        self._key_down(direction_key)
        time.sleep(0.03)
        self._key_down(self.jump_key)
        self._key_up(direction_key)
        self._key_up(self.jump_key)


    ''' Stop / Release '''

    def _release_all(self):
        # Release all keys currently tracked as pressed
        # Supports dynamic additions (potions, items) without hardcoding
        with self._pressed_keys_lock:
            keys_to_release = list(self._pressed_keys)

        self._key_up(self.up_key) # Ensure UP key is explicitly released

        for key in keys_to_release:
            self._key_up(key)
            time.sleep(0.01)  # Brief delay for driver/game event dispatch
        
    def release_all(self):
        # Release all active and stuck keys
        self._packet_wrapper(self._release_all_lock, "_status_release_all", self._release_all)

    def stop_move(self):
        self._release_direction()

    ''' Item Usage (HP/MP Potions, etc.) '''

    def _item_command(self, key):
        try:
            self._key_down(key)
            time.sleep(3)
        except Exception as e:
            logging.error(f"Error using item: {e}")
        finally:
            self._key_up(key)
            with self._item_lock:
                self._status_item = False

    def enable_use_item(self, key):
        if not key:
            return
        with self._item_lock:
            if self._status_item:
                # Previous usage still in progress, skip duplicate trigger
                return
            self._status_item = True
            threading.Thread(target=self._item_command, args=(key,), daemon=True).start()

    ''' Pick Up Behaviors '''
    def _pick_up_command(self, key):
        try:
            self._key_down(key)
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error executing pick up command: {e}")
        finally:
            self._key_up(key)
            self._pick_up = False

    def enable_pick_up(self):
        with self._pick_up_lock:
            if not self.pick_up_key:
                return
            if self._pick_up: 
                return
            self._pick_up = True
        threading.Thread(target=self._pick_up_command, args=(self.pick_up_key,), daemon=True).start()

    def _packet_wrapper(self, lock, status_attr, target, *args):
        """
        Shared reentrancy prevention and background execution wrapper.
        lock: Corresponding threading.Lock
        status_attr: Flag attribute name string (e.g. "_status_rope")
        target: Target method to execute
        """
        with lock:
            if getattr(self, status_attr):
                return
            setattr(self, status_attr, True)

        def _wrapper():
            try:
                target(*args)
            except Exception as e:
                logging.error(f"{target.__name__} error: {e}")
            finally:
                with lock:
                    setattr(self, status_attr, False)

        threading.Thread(target=_wrapper, daemon=True).start()
