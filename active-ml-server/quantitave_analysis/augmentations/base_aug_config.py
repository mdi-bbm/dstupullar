import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from typing import List
from quantitave_analysis.models.config import Config

class DetectionAugmentationConfig(Config):
    """Configuration for detection augmentation processor."""
    do_flip: bool = True
    do_scale: bool = True
    do_rotate: bool = True
    do_brightness: bool = True
    scale_factors: List[float] = [0.95, 1.05]
    brightness_factors: List[float] = [0.8, 1.2]
    rotation_angles: List[int] = [90, 180, 270]
    
    class Config:
        arbitrary_types_allowed = True

class SegmentationAugmentationConfig(Config):
    """Configuration for segmentation augmentation processor."""
    do_flip: bool = True
    do_scale: bool = True
    do_rotate: bool = True
    scale_factors: List[float] = [0.5, 1.5]
    rotation_angles: List[int] = [90, 180, 270]
    
    class Config:
        arbitrary_types_allowed = True