import os
import shutil
import re
import logging
import time
from abc import ABC, abstractmethod
from typing import List
import glob
import json
from datetime import datetime
import tempfile

from common.models import DigitalAssistantBase
from quantitave_analysis.models.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StorageConfig(DigitalAssistantBase):
    storage_root: str


class IStorageManager(ABC):
    def __init__(self, config: StorageConfig = Config()):
        self.config = config

    @abstractmethod
    def create_storage(self, folder_name: str) -> str:
        pass

    @abstractmethod
    def delete_storage(self, folder_name: str) -> None:
        pass

    @abstractmethod
    def list_contents(self, folder_name: str) -> List[str]:
        pass


class DataHandler:
    @staticmethod
    def count_training_samples(image_dir: str) -> int:
        """
        Counts the number of training images in the folder and throws an error if there are no images.

        :param image_dir: Path to the folder with images.
        :return: Number of images.
        """
        n_samples = sum(1 for file in os.listdir(image_dir) if file.lower().endswith(('.jpg', '.jpeg', '.png')))
        logging.info(f"Number of training samples (images): {n_samples} in {image_dir}")

        if n_samples == 0:
            raise ValueError("No training samples found. Please check the image directory and annotations.")

        return n_samples

    def get_next_version(base_folder: str, model_name: str) -> str:
        """
        Determines the next version of the model by increasing the number of the last existing version.

        :param base_folder: Root folder for storing models.
        :param model_name: Name of the model.
        :return: New version of the model, full path.
        """
        folder = os.path.join(base_folder, model_name)

        version = DataHandler.get_number_of_version(base_folder=base_folder, model_name=model_name) + 1

        next_version_path = os.path.join(folder, f"v{version}-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

        # existing_versions = glob.glob(os.path.join(model_path, "v*-*"))

        # version_numbers = []
        # for folder in existing_versions:
        #     match = re.search(r"v(\d+)-", os.path.basename(folder))
        #     if match:
        #         version_numbers.append(int(match.group(1)))
        #
        # next_version = max(version_numbers, default=0) + 1  # Bump up the latest version by 1
        return next_version_path

    @staticmethod
    def get_latest_model_path(base_folder: str, model_name: str) -> str:
        """
        Finds the latest saved model version by creation time.
        If no model is found, returns the path where the first version would be.

        :param base_folder: Root folder where models are stored.
        :param model_name: Model name.
        :return: Path to the latest saved model version or the path for the first version.
        """
        model_folder = os.path.join(base_folder, model_name)

        # Create model folder if it doesn't exist
        if not os.path.exists(model_folder):
            os.makedirs(model_folder, exist_ok=True)
            logger.info(f"Created model folder at: {model_folder}")

        # Get all version folders
        model_versions = glob.glob(os.path.join(model_folder, "v*-*"))

        if not model_versions:
            logger.info(f"No models found for {model_name}.")
            return model_folder  # Return just the model folder path, not a specific version

        # Return the most recent version path
        return max(model_versions, key=os.path.getctime)

    @staticmethod
    def get_number_of_version(base_folder: str, model_name: str) -> int:
        """
        Gets the number of the latest version.

        :param base_folder: Root folder where models are stored.
        :param model_name: Model name.
        :return: Number of the latest version, or -1 if no version exists yet.
        """
        model_folder = os.path.join(base_folder, model_name)

        if not os.path.exists(model_folder):
            return -1

        # Get all version folders
        model_versions = glob.glob(os.path.join(model_folder, "v*-*"))

        if not model_versions:
            return -1

        # Extract version numbers from folder names
        version_numbers = []
        for folder in model_versions:
            match = re.search(r"v(\d+)-", os.path.basename(folder))
            if match:
                version_numbers.append(int(match.group(1)))

        return max(version_numbers) if version_numbers else -1
    
    @staticmethod
    def get_latest_result_txt(base_folder: str) -> str:

        base_path = base_folder # The path to AutogluonModels is passed to results_processor
        
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"AutogluonModels directory not found at: {base_path}")
        
        txt_dirs = [d for d in os.listdir(base_path) 
                if os.path.isdir(os.path.join(base_path, d))]
        
        if not txt_dirs:
            raise FileNotFoundError("No result.txt found after prediction")
        
        latest_dir = max(txt_dirs, key=lambda d: os.path.getmtime(os.path.join(base_path, d)))
        
        return os.path.join(base_path, latest_dir)


    @staticmethod
    def save_model_path(base_folder: str, model_name: str, temp = False) -> str:
        """
        Generates a path to save the model with auto-incremented version and timestamp.

        :param base_folder: Root folder where models are stored.
        :param model_name: Model name.
        :return: Full path to the folder where the model will be saved.
        """
        model_folder = os.path.join(base_folder, model_name)

        # Create model folder if it doesn't exist
        if not os.path.exists(model_folder):
            os.makedirs(model_folder, exist_ok=True)

        # Get the latest version number and increment it
        version = DataHandler.get_number_of_version(base_folder, model_name) + 1

        # Create the new version path with timestamp
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        new_version_path = os.path.join(model_folder, f"v{version}-{timestamp}")

        if temp:
            temp_version_path = new_version_path + '_temp'

        # Create the directory
        try:
            if temp:
                os.makedirs(temp_version_path, exist_ok=False)
                logger.info(f"Created temporary model version at: {temp_version_path}")
                return temp_version_path
            else:
                os.makedirs(new_version_path, exist_ok=False)
                logger.info(f"Created new model version directory: {new_version_path}")
                return new_version_path
        
        except FileExistsError:
            # If directory already exists (unlikely with timestamp), try again with a different timestamp
            if temp:
                logger.warning(f"Directory {temp_version_path} already exists, retrying with new timestamp")
            else:
                logger.warning(f"Directory {new_version_path} already exists, retrying with new timestamp")
            time.sleep(1)  # Wait a second to ensure different timestamp
            return DataHandler.save_model_path(base_folder, model_name)


class TemporaryStorageManager(IStorageManager):
    config: StorageConfig = Config()
    # path - the path to the storage up to the folder name
    # folder_name - the name of the folder, for example, dataset 1

    def _get_storage_path(self, folder_name: str) -> str:
        return os.path.join(self.config.storage_root, folder_name)

    def create_storage(self, folder_name: str) -> str:
        path = self._get_storage_path(folder_name)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.info(f"Storage folder '{path}' created.")
        else:
            logger.info(f"Storage folder '{path}' already exists.")

        return path # returning path so that the calling party can immediately use this path, for example, to write files

    def delete_storage(self, folder_name: str) -> None:
        path = self._get_storage_path(folder_name)
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            logger.info(f"Storage folder '{path}' deleted.")
        else:
            logger.warning(f"Storage folder '{path}' does not exist.")

    def list_contents(self, folder_name: str) -> List[str]:
        path = self._get_storage_path(folder_name)

        if not os.path.exists(path):
            logger.error(f"Storage folder '{path}' not found.")
            raise FileNotFoundError(f"Storage folder '{folder_name}' not found.")

        contents = os.listdir(path)
        logger.info(f"Contents of '{path}': {contents}")
        return contents

    def reset_directory(self, folder_name: str) -> None:
        self.delete_storage(folder_name)
        self.create_storage(folder_name)

    """def get_model_path(directory_with_model_directories, model_name: str) -> Optional[str]:
        try:
            model_dirs = [folder for folder in os.listdir(os.path.join(directory_with_model_directories), model_name) if os.path.isdir(os.path.join(directory_with_model_directories, folder))]
            if not model_dirs:
                raise Exception("No model directories found in the cache folder!")
            elif len(model_dirs) > 1:
                logging.warning(f"Multiple model directories found. Using: {model_dirs[0]}")
            return os.path.join(directory_with_directories, model_dirs[0])
        except Exception as e:
            logging.error(f"Error getting model directory: {e}")
            raise
        """

        
    def get_model_folder(self, base_path:str): # results.txt (base_path="AutogluonModels"):
        """Returns the last folder with the model or the result of inference"""
        #
        model_dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        logging.info(model_dirs)
        latest_dir = max(model_dirs, key=lambda d: os.path.getmtime(os.path.join(base_path, d)))
        model_path = os.path.join(base_path, latest_dir)
        return model_path

    def find_latest_dir(self,
                        directory_with_directories: str):  # for the latest model in iterative learning of detection and for the txt parser
        dir_dirs = glob.glob(f"{directory_with_directories}/*")
        if not dir_dirs:
            raise FileNotFoundError("No model directories found in the specified directory.")

        for model_dir in sorted(dir_dirs, key=os.path.getmtime, reverse=True):
            if os.path.exists(os.path.join(model_dir, "assets.json")):
                return model_dir

        raise FileNotFoundError("No valid model directories with assets.json found.")

    def create_temp_json(self, image_path, output_dir):
        data = {
            "images": [{"id": 0, "width": -1, "height": -1, "file_name": image_path}],
            "categories": []
        }
        json_file = os.path.join(output_dir, os.path.basename(image_path) + ".json")

        with open(json_file, "w") as f:
            json.dump(data, f)

        return json_file

    def create_temp_directory(self) -> str:
        """Create a temporary directory and return its path."""
        try:
            temp_dir = tempfile.mkdtemp(prefix="dino_training_")
            logger.info(f"Created temporary directory: {temp_dir}")
            return temp_dir
        except Exception as e:
            logger.error(f"Failed to create temporary directory: {e}")
            raise