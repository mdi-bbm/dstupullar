import logging

from quantitave_analysis.models.segmentation.dataset_pipeline import SegmentationDatasetPreparer
from quantitave_analysis.models.segmentation.segmentation_model import SegmentationModelHandler
from ML_server.ml_routines.base import MLRoutinesBase

logger = logging.getLogger(__name__)


class SegmentationRoutines(MLRoutinesBase):
    """ML routines for segmentation tasks"""

    def __init__(self):
        self.dataset_pipeline = SegmentationDatasetPreparer()
        self.model_handler = SegmentationModelHandler()

    def create_dataset(self, input_folder: str, output_folder: str) -> None:
        """
        Create a segmentation dataset from raw data

        Args:
            input_folder: Directory containing raw data
            output_folder: Directory to store the processed dataset
        """
        try:
            logger.info(f"Creating segmentation dataset from {input_folder} to {output_folder}")
            self.dataset_pipeline.create_dataset(input_folder, output_folder)
        except Exception as e:
            logger.error(f"Error creating segmentation dataset: {e}")
            raise

    def train(self, dataset_folder: str, models_directory: str, dataset_id: int, epochs: int = 3) -> bool:
        """
        Train a segmentation model

        Args:
            dataset_folder: Directory containing the processed dataset
            models_directory: Directory to store the trained model
            dataset_id: Dataset ID
            epochs: Number of training epochs
        """
        try:
            logger.info(f"Training segmentation model with data from {dataset_folder}")
            self.model_handler.run_train(dataset_id)
            return True
        except Exception as e:
            logger.error(f"Error training segmentation model: {e}")
            return False
            raise

    def predict(self, input_folder: str, output_folder: str, dataset_id: int) -> bool:
        """
        Run inference with a trained segmentation model

        Args:
            input_folder: Directory containing input data
            output_folder: Directory to store the predictions
            dataset_id: Dataset ID
        """
        try:
            logger.info(f"Running segmentation prediction from {input_folder} to {output_folder}")
            self.model_handler.run_predict(dataset_id)
            return True
        except Exception as e:
            logger.error(f"Error in segmentation prediction: {e}")
            return False
            raise
