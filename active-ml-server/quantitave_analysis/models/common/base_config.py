from pydantic import BaseModel, ConfigDict
from typing import Dict

from quantitave_analysis.models.config import Config  

class BaseModelConfig(BaseModel):
    model_name: str
    model_path: str
    stages: int = 5
    hyperparameters: Dict[str, float]
    train_data_folder: str = Config().PROCESSED_FOLDER,
    folder_for_train: str = Config().PROCESSED_FOLDER,
    output_folder: str = Config().ALL_MODELS_FOLDER,
    folder_for_inference: str = Config().UPLOAD_FOLDER,
    results_folder_after_inference: str = Config().RETURN_FOLDER,

    model_config = ConfigDict(arbitrary_types_allowed=True)
