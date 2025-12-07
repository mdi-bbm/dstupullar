from typing import Dict, Type
from common.models import TaskPackage, ProcessingMode
from .base import MLRoutinesBase
from .segmentation_routines import SegmentationRoutines
from .detection_routines import DetectionRoutines


class MLRoutinesFactory:
    """Factory for creating ML routines based on processing mode"""

    _routines: Dict[ProcessingMode, Type[MLRoutinesBase]] = {
        ProcessingMode.SEGMENTATION: SegmentationRoutines,
        ProcessingMode.DETECTION: DetectionRoutines
    }

    @classmethod
    def create(cls, task_package: TaskPackage) -> MLRoutinesBase:
        """
        Create an ML routine based on the task package

        Args:
            task_package: Task package containing processing mode

        Returns:
            MLRoutinesBase: Instance of the appropriate ML routine

        Raises:
            ValueError: If no routine is available for the specified mode
        """
        routine_class = cls._routines.get(task_package.mode)
        if not routine_class:
            raise ValueError(f"No ML routine available for mode: {task_package.mode}")

        return routine_class()
