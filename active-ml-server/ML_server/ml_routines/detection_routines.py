import logging

from quantitave_analysis.models.detection.detection_dataset_pipeline import DetectionDatasetPipeline
from quantitave_analysis.models.detection.detection_model import DinoDetectionModelHandler
from ML_server.ml_routines.base import MLRoutinesBase

logger = logging.getLogger(__name__)


class DetectionRoutines(MLRoutinesBase):
    """ML routines for detection tasks"""

    def __init__(self):
        self.dataset_pipeline = DetectionDatasetPipeline()
        self.model_handler = DinoDetectionModelHandler()

    def create_dataset(self, input_folder: str, output_folder: str) -> None:
        """
        Create a detection dataset from raw data

        Args:
            input_folder: Directory containing raw data
            output_folder: Directory to store the processed dataset
        """
        try:
            logger.info(f"Creating detection dataset from {input_folder} to {output_folder}")
            self.dataset_pipeline.create_coco_dataset(input_folder, output_folder)
        except Exception as e:
            logger.error(f"Error creating detection dataset: {e}")
            raise

    def train(self, dataset_folder: str, models_directory: str, dataset_id: int, epochs: int = 3) -> bool:
        """
        Train a detection model

        Args:
            dataset_folder: Directory containing the processed dataset
            models_directory: Directory to store the trained model
            dataset_id: Dataset ID
            epochs: Number of training epochs
        """
        try:
            logger.info(f"Training detection model with data from {dataset_folder}")
            self.model_handler.run_train(dataset_id)
            return True
        except Exception as e:
            logger.error(f"Error training detection model: {e}")
            return False
            raise

    def predict(self, input_folder: str, output_folder: str, dataset_id: int) -> bool:
        """
        Run inference with a trained detection model

        Args:
            input_folder: Directory containing input data
            output_folder: Directory to store the predictions
            dataset_id: Dataset ID
        """
        try:
            logger.info(f"Running detection prediction from {input_folder} to {output_folder}")
            self.model_handler.run_predict(dataset_id)
            return True
        except Exception as e:
            logger.error(f"Error in detection prediction: {e}")
            return False
            raise
