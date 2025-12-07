import os
import json
from abc import ABC
from pydantic import PrivateAttr
from autogluon.multimodal import MultiModalPredictor
import logging

from common.models import DigitalAssistantBase
from quantitave_analysis.models.detection.detection_config import DetectionModelConfig
from quantitave_analysis.utils.temporary_storage import TemporaryStorageManager, DataHandler
from quantitave_analysis.models.detection.dino_data_processor import DinoDataProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DinoModelManager(ABC, DigitalAssistantBase):
    model_handler_config: DetectionModelConfig = DetectionModelConfig()
    temp_manager: TemporaryStorageManager = TemporaryStorageManager()
    _data_processor: DinoDataProcessor = PrivateAttr(DinoDataProcessor())

    def initialize_predictor(self, models_base_folder: str):
        try:
            if (DataHandler.get_number_of_version(models_base_folder, self.model_handler_config.model_name) == -1 or not DinoModelManager().check_classes_consistency(models_base_folder)):
                # Create a temporary folder for the new version
                temp_version_path = DataHandler.save_model_path(
                    base_folder=models_base_folder,
                    model_name=self.model_handler_config.model_name,
                    temp = True
                )
                logging.info(f"Created initial model version at: {temp_version_path}")

                # Initialize predictor
                predictor = MultiModalPredictor(
                    problem_type="object_detection",
                    presets=self.model_handler_config.hyperparameters["presets"],
                    sample_data_path=self.model_handler_config.train_data_folder,
                    hyperparameters={
                        "optimization.max_epochs": 5, # Set five epochs for the first run of the model
                        "env.batch_size":4, # self.model_handler_config.hyperparameters["batch_size"],
                        #"model.mmdet_image.frozen_layers": self.model_handler_config.hyperparameters["frozen_layers"],
                        "env.num_workers": 2,  # Reduced parallelism
                        "env.num_gpus": 1,
                        "env.strategy": "dp",
                    },

                    path=temp_version_path
                )

            else:
                # Continue from the latest model path
                latest_model_path = DataHandler.get_latest_model_path(
                    base_folder=models_base_folder,
                    model_name=self.model_handler_config.model_name
                )
                logging.info(f"Using latest model path: {latest_model_path}")

                # Create new version path for saving updated model
                temp_version_path = DataHandler.save_model_path(
                    base_folder=models_base_folder,
                    model_name=self.model_handler_config.model_name,
                    temp = True
                )
                logging.info(f"Will save new model to: {temp_version_path}")

                # Initialize or load predictor
                predictor = MultiModalPredictor(
                    problem_type="object_detection",
                    presets=self.model_handler_config.hyperparameters["presets"],
                    sample_data_path=self.model_handler_config.train_data_folder,
                    hyperparameters={
                        "optimization.max_epochs": 1, 
                        "env.batch_size":4, # self.model_handler_config.hyperparameters["batch_size"],
                        "model.mmdet_image.frozen_layers": self.model_handler_config.hyperparameters["frozen_layers"],
                        "env.num_workers": 2,  # Reduced parallelism
                        "env.num_gpus": 1,
                        "env.strategy": "dp",
                    },

                    path=temp_version_path
                ).load(latest_model_path)

            return predictor, temp_version_path
        
        except Exception as e:
            logger.error(f"Failed to initialize predictor: {e}")
            TemporaryStorageManager().delete_storage(temp_version_path)
            exit(1)

    def finalize_model_version(self, temp_version_path: str, models_base_folder: str, train_json_path: str):
        try:
            # Get final folder name (without _temp)
            final_version_path = temp_version_path.replace("_temp", "")

            temp_score = self.get_best_score(os.path.join(temp_version_path, 'assets.json'))

            # If temp_score is None, we'll treat it as a case where we want to keep the temp version
            if temp_score is None:
                logger.warning(f"Invalid score in {temp_version_path}/assets.json - keeping temp version as final")
                
            version_score = 0.0
            if os.path.exists(os.path.join(final_version_path, 'assets.json')) and temp_score is not None: 
                version_score = self.get_best_score(os.path.join(final_version_path, 'assets.json'))
                
                if version_score is None:
                    version_score = 0.0
                    
                if temp_score > version_score:
                    if os.path.exists(final_version_path):
                        self.temp_manager.delete_storage(final_version_path)
                        logger.info(f"Removed existing directory: {final_version_path}. Temporary model folder is better")
                    
                    # Rename folder
                    os.rename(temp_version_path, final_version_path)
                    logger.info(f"Successfully finalized temporary model version at: {final_version_path} with score {temp_score}")
            else:
                # If final version doesn't exist or temp_score is None - save temp as final
                if os.path.exists(final_version_path):
                    self.temp_manager.delete_storage(final_version_path)
                os.rename(temp_version_path, final_version_path)
                logger.info(f"Model version saved at: {final_version_path}")
                    
            # Create labels.txt in final version
            labels_path = os.path.join(final_version_path, "labels.txt")
            class_names = self._data_processor.extract_classes_from_coco_json(train_json_path)
            with open(labels_path, "w") as f:
                f.write("\n".join(class_names))
            logger.info(f"Created labels.txt at: {labels_path}")

            # Clean up temp directory if it still exists
            if os.path.exists(temp_version_path):
                self.temp_manager.delete_storage(temp_version_path)
                logger.info(f"Removed temporary directory: {temp_version_path}")

            return final_version_path
            
        except Exception as e:
            logger.error(f"Failed to finalize model version: {e}")
            if os.path.exists(temp_version_path):
                self.temp_manager.delete_storage(temp_version_path)
            return None

    def get_best_score(self, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                score = data.get("best_score", 0)
                return float(score) if score is not None and score != "null" else None
        except Exception as e:
            logger.error(f"Failed to read score from {file_path}: {e}")
            return None
        
    def check_classes_consistency(self, models_base_folder):
        """Checks if the number of classes matches between the previous version and the current data"""
        # Getting the path to the latest version of the model
        latest_model_path = DataHandler.get_latest_model_path(
            base_folder=models_base_folder,
            model_name=self.model_handler_config.model_name
        )
        
        # Checking labels.txt in the previous version
        latest_labels_path = os.path.join(latest_model_path, "labels.txt")
        if not os.path.exists(latest_labels_path):
            logger.warning("labels.txt not found in previous version - treating as first initialization")
            return False
        
        with open(latest_labels_path, 'r') as f:
            latest_classes = f.read().splitlines()
        
        # Getting classes from the current training data
        current_labels_path = os.path.join(self.model_handler_config.train_data_folder, "labels.txt")
        with open(current_labels_path, 'r') as f:
            current_classes = f.read().splitlines() 

        # Comparing the number of classes
        if len(latest_classes) != len(current_classes):
            logger.warning(f"Class count mismatch! Previous version has {len(latest_classes)} classes, "
                            f"current data has {len(current_classes)} classes. Initializing new model.")
            return False
        
        return True
