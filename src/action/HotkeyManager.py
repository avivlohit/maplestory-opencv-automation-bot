import win32api
import logging

'''
Hotkey Manager
Uses virtual key codes (VK codes).
'''
class HotkeyManager:
    def __init__(self):
            self._bindings = {}

    def register(self, vk_code, callback):
        '''
        Args:
            vk_code: Virtual key code
            callback: Function to invoke when triggered
        '''
        self._bindings[vk_code] = callback

    def poll(self):
        '''
        Called once per main loop cycle to poll all registered hotkeys
        '''
        for vk_code, callback in self._bindings.items():
            state = win32api.GetAsyncKeyState(vk_code)

            # Key mask: check least significant bit (key pressed since last call)
            if state & 0x0001:
                try:
                    callback()
                except Exception as e:
                    logging.error(f"Hotkey callback error (vk={vk_code}): {e}")
