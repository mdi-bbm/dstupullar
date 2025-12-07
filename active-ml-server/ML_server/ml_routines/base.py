from abc import ABC, abstractmethod


class MLRoutinesBase(ABC):
    """Base class for ML routines"""

    @abstractmethod
    def create_dataset(self, input_folder: str, output_folder: str) -> None:
        """
        Create a dataset from raw data

        Args:
            input_folder: Directory containing raw data
            output_folder: Directory to store the processed dataset
        """
        pass

    @abstractmethod
    def train(self, dataset_folder: str, models_directory: str, dataset_id: int, epochs: int = 3) -> None:
        """
        Train a model on the dataset

        Args:
            dataset_folder: Directory containing the processed dataset
            models_directory: Directory to store the trained model
            dataset_id: Dataset ID
            epochs: Number of training epochs
        """
        pass

    @abstractmethod
    def predict(self, input_folder: str, output_folder: str, dataset_id: int) -> None:
        """
        Run inference with a trained model

        Args:
            input_folder: Directory containing input data
            output_folder: Directory to store the predictions
            dataset_id: Dataset ID
        """
        pass
