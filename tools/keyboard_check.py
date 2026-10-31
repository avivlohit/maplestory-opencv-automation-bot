import keyboard
'''
Inspect corresponding key names in the keyboard module
'''
def print_key(event):
    print(event)

keyboard.hook(print_key)
keyboard.wait()
