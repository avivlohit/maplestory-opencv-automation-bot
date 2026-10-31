import time
import logging
from config.config_loader import config
from typing import Optional
from src.engine.game_state import GameState
import time
import random
from pathlib import Path
import yaml
import time


class HealthManager:
    def __init__(self):

        #--- [Potions, HP/MP Settings]
        self.health_setting = {} # <-- HP level configuration
        self.mp_setting = {} # <-- MP level configuration
        self.hp_sorted_levels = [] # <-- HP potion sorted levels
        self.mp_sorted_levels = [] # <-- MP potion sorted levels
        self.hp_cooldown = 5 # <-- HP potion cooldown
        self.mp_cooldown = 5 # <-- MP potion cooldown
        self._loading_config()
        #--- [Timers]
        self.last_hp_time = None # <-- Last HP potion time
        self.last_mp_time = None # <-- Last MP potion time

    def _loading_config(self):

        '''
        Function:
            Read potion config from settings, filter invalid items, and sort
        '''

        hp_raw = config.get("player_setting.health_setting") or {}
        for level, setting in hp_raw.items():
            key = setting.get("key")
            value = setting.get("value")
            if key == "None":
                key = None

            self.health_setting[level] = {
                "value" : value,
                "key" : key,
            }

        self.hp_sorted_levels = sorted(
            self.health_setting.items(),
            key=lambda item: item[1]["value"]
        )
        mp_raw = config.get("player_setting.mp_setting") or {}
        for level, setting in mp_raw.items():
            key = setting.get("key")
            value = setting.get("value")
            if key == "None":           # <-- Unset thresholds will be discarded
                key = None

            self.mp_setting[level] = {
                "value" : value,
                "key" : key,
            }

        self.mp_sorted_levels = sorted(
            self.mp_setting.items(),
            key=lambda item: item[1]["value"]
        )
    def _health_status_check(self,player_hp,current_time): 

        '''
        Purpose:
            Check HP status and route action
            Returns: HP level, corresponding hotkey
        '''

        if player_hp is None:
            return None, None  # Guard check: intercept when player_hp is None

        if not (0 < player_hp <= 100):
            logging.debug(f"Abnormal HP reading: {player_hp}")
            return None, None

        if not self.health_setting:
            return None, None 



        if self.last_hp_time is None:
            self.last_hp_time = current_time
        # Potion cooldown
        if (current_time - self.last_hp_time) < self.hp_cooldown:
            return None, None

        # Main check
        for level, setting in self.hp_sorted_levels:
            if player_hp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # No key set for this level, skip to next level check
                self.last_hp_time = current_time
                return level, key
        return None, None

    def _mp_status_check(self,player_mp,current_time): 


        if player_mp is None:
            return None, None  # Guard check: intercept when player_mp is None

        if not (0 < player_mp <= 100):
            logging.info(f"Abnormal MP reading: {player_mp}")
            return None, None


        # Return None if no potion settings configured
        if not self.mp_setting:
            return None, None 

        if self.last_mp_time is None:
            self.last_mp_time = current_time
        # Potion cooldown
        if (current_time - self.last_mp_time) < self.mp_cooldown:
            return None, None
        
        # Main check
        for level, setting in self.mp_sorted_levels:
            if player_mp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # No key set for this level, skip to next level check
                self.last_mp_time = current_time
                return level, key
            
        return None, None


    def run(self,current_player_hp,current_player_mp, current_time):
        
        level , heal_key = self._health_status_check(current_player_hp,current_time)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": heal_key}
        level , mp_key = self._mp_status_check(current_player_mp, current_time)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": mp_key}

        return None
