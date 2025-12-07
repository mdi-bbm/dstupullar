from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TaskType(str, Enum):
    TRAIN = "TRAIN"
    INFERENCE = "INFERENCE"


class ProcessingMode(str, Enum):
    SEGMENTATION = "Segmentation"
    DETECTION = "Detection"


class PackageStatus(str, Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ERROR = "ERROR"


class DigitalAssistantBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class TaskPackage(DigitalAssistantBase):
    package_id: int
    user_id: int
    dataset_id: int
    task: TaskType
    mode: ProcessingMode
    package_status: PackageStatus
    package: str  # URL to package data
    label_properties: Optional[str]  # URL to label properties

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProcessingResult(DigitalAssistantBase):
    user_id: int
    mode: ProcessingMode
    files: List[tuple]