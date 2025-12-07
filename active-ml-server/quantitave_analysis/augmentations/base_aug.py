import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from abc import ABC, abstractmethod
import numpy as np
from typing import List, Tuple, Any
import logging
from common.models import DigitalAssistantBase
from quantitave_analysis.models.common.base_config import BaseModelConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class BaseAugmentationProcessor(ABC, DigitalAssistantBase):
    """Base class for image augmentation processors, handling configuration and abstract augmentation methods."""
    
    model_handler_config: BaseModelConfig

    @abstractmethod
    def augment(self, image: np.ndarray, annotations: Any, config: BaseModelConfig) -> Tuple[List[np.ndarray], List[Any]]:
        """
        Apply augmentations to an image and its annotations based on configuration.

        Args:
            image (np.ndarray): Input image as a NumPy array.
            annotations (Any): Annotations associated with the image (e.g., bounding boxes, masks).
            config (BaseModelConfig): Configuration object containing augmentation flags and parameters.

        Returns:
            Tuple[List[np.ndarray], List[Any]]: Lists of augmented images and their corresponding annotations.
        """
        pass