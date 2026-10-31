'''
Shared Data Store
'''

class SharedInfo:
    def __init__(self):
        # Bulletin board data content
        self.minimap_tl = (0,0)
        self.is_initialized = False

    def update_minimap_anchor(self, tl: tuple):
        self.minimap_tl = tl
        self.is_initialized = True
        print(f"Updated minimap anchor: {self.minimap_tl}")


shared_info =  SharedInfo()
