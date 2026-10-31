from dataclasses import dataclass, field
from typing import Optional
from src.utils.boxes import BBox
import numpy as np
@dataclass
class MobInfo:
    name : str
    bbox : BBox
    center: tuple[int, int]
    size: tuple[int, int]

@dataclass
class GameState:
    '''
    Snapshot of a single scan cycle
    '''
    player_center_loc : Optional[tuple[int,int]] = None
    player_hp : Optional[float] = None
    player_mp : Optional[float] = None
    roi_BBOX : Optional[BBox] = None
    mobs : list[MobInfo] = field(default_factory=list) 
    # frame : Optional[np.ndarray] = None
    # lost_track_count : int = 0
    mini_player_loc : Optional[tuple[int,int]] = None
