import os

from quantitave_analysis.models.common.base_config import BaseModelConfig
from quantitave_analysis.utils.temporary_storage import DataHandler
from quantitave_analysis.models.config import Config  

PROCESSED_FOLDER = Config().PROCESSED_FOLDER
UPLOAD_FOLDER = Config().UPLOAD_FOLDER
RETURN_FOLDER = Config().RETURN_FOLDER


class DetectionModelConfig(BaseModelConfig):
    model_name: str = "detection"
    train_data_folder: str = PROCESSED_FOLDER
    detection_model_folder: str = os.path.join(Config().ALL_MODELS_FOLDER, "detection")
    model_path: str = DataHandler.get_latest_model_path(Config().ALL_MODELS_FOLDER, "detection") #or "models/detection/default"
    stages: int = 3 # one technically implemented to prevent memory problems - stages
    batch_size_per_stage: int = 30
    epochs: int = 10  # Ensure this matches or is compatible with optimization.max_epochs
    
    hyperparameters: dict = {
        # "num_gpus": 1,
        # "threshold": 0.05,
        # "model_save_path": model_path,
        # "time_limit": 6000,
        # "n_train_partitions": 5,
        # "per_gpu_batch_size": 8,

    #     "presets": "best_quality",
    #     "optimization.max_epochs": 5,
    #     "env.batch_size": 4,
    #     "env.num_workers": 2, 
    #     "env.strategy": "dp",
    #     "model.mmdet_image.frozen_layers": ["backbone"] #, "neck"], 
    # }
        "num_gpus": 1,
        "model_save_path": model_path,
        "presets": "best_quality",
        "batch_size": 2,
        "max_epochs": 20,
        "time_limit": 6000,
        "n_train_partitions": 15,
        "per_gpu_batch_size": 2,
        "frozen_layers":  ["backbone"] ,# "neck"], 
    }


    inference_data_folder: str = UPLOAD_FOLDER
    results_folder: str = RETURN_FOLDER
    single_json_per_image: bool = False
