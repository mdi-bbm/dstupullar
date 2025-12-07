from quantitave_analysis.models.common.base_config import BaseModelConfig
from quantitave_analysis.utils.temporary_storage import DataHandler
from quantitave_analysis.models.config import Config

ALL_MODELS_FOLDER = Config().ALL_MODELS_FOLDER
UPLOAD_FOLDER = Config().UPLOAD_FOLDER
PROCESSED_FOLDER = Config().PROCESSED_FOLDER
RETURN_FOLDER = Config().RETURN_FOLDER

class SegmentationModelConfig(BaseModelConfig):
    model_name: str = "segmentation"
    model_path: str = DataHandler.get_latest_model_path(ALL_MODELS_FOLDER, "segmentation") #or "models/segmentation/default"
    epochs: int = 50
    folder_for_train: str = PROCESSED_FOLDER
    output_folder: str = ALL_MODELS_FOLDER
    folder_for_inference: str = UPLOAD_FOLDER
    results_folder_after_inference: str = RETURN_FOLDER
    # hyperparameters for multi-class segmentation
    hyperparameters: dict = {
        # "optimization.learning_rate": 0.001,
        # "env.eval_batch_size_ratio": 10,
        # "time_limit": 432000,
        # "model.sam.checkpoint_name": "facebook/sam-vit-base",
        "model.sam.checkpoint_name": "facebook/sam-vit-large",
        "optimization.max_epochs": 50,
        "env.batch_size": 16,  # self.model_handler_config.hyperparameters["batch_size"],
        "env.precision": 32,
        "optimization.loss_function": "mask2former_loss",
        "optimization.efficient_finetune": "lora",
        "model.sam.num_mask_tokens": 10,
        "optimization.patience": 50,
    }
