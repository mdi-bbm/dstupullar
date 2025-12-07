import os
import logging
import pandas as pd
import cv2
import numpy as np
from tqdm import tqdm
from autogluon.multimodal import MultiModalPredictor

from quantitave_analysis.utils.temporary_storage import TemporaryStorageManager, DataHandler
from quantitave_analysis.utils.image_processing import LabelPropertiesLoader
from quantitave_analysis.models.segmentation.segmentation_config import SegmentationModelConfig
from quantitave_analysis.models.common.base_model import ModelHandlerBase
from quantitave_analysis.models.detection.results_processor import ResultProcessor
from quantitave_analysis.utils.file_converter import ConvertorPalette2Rgba
from common.tools.clear_routines import clear_memory
from quantitave_analysis.models.config import Config
from quantitave_analysis.models.segmentation.segmentation_erosion import SegmentationErosionProcessor

ALL_MODELS_FOLDER = Config().ALL_MODELS_FOLDER
SUPPORTED_IMAGE_TYPES = Config().SUPPORTED_IMAGE_TYPES
DATA_UPLOADS_FOLDER = Config().DATA_UPLOADS_FOLDER if hasattr(Config(), 'DATA_UPLOADS_FOLDER') else 'data/uploads'


from scipy.ndimage import maximum_filter


class SegmentationModelHandler(ModelHandlerBase):
    model_handler_config: SegmentationModelConfig = SegmentationModelConfig()
    temp_manager: TemporaryStorageManager = TemporaryStorageManager()
    result_processor: ResultProcessor = ResultProcessor()

    def get_data_chunks(self, csv_file, target_chunk_count=None):
        """
        Calculates chunk parameters for dynamic data loading

        Args:
            csv_file: path to the CSV file
            target_chunk_count: desired number of chunks (if None, calculated automatically)

        Returns:
            tuple: (total_rows, chunk_size, num_chunks)
        """
        df = pd.read_csv(csv_file, sep=',')
        total_rows = len(df)

        # Calculate number of chunks if not specified
        if target_chunk_count is None:
            # 1 chunk per 50 entries, minimum 1
            target_chunk_count = max(1, total_rows // 50)

        # Calculate chunk size
        chunk_size = total_rows // target_chunk_count

        return total_rows, chunk_size, target_chunk_count

    def load_data_chunk(self, csv_file, chunk_index, chunk_size, total_rows):
        """
        Dynamically loads a chunk of data from CSV file

        Args:
            csv_file: path to the CSV file
            chunk_index: index of current chunk (0-based)
            chunk_size: size of each chunk
            total_rows: total number of rows in the file

        Returns:
            DataFrame with the chunk data
        """
        start_idx = chunk_index * chunk_size

        # For the last chunk, include all remaining rows
        if chunk_index == (total_rows // chunk_size):
            nrows = total_rows - start_idx
        else:
            nrows = chunk_size

        # Load only the needed chunk
        df_chunk = pd.read_csv(
            csv_file,
            sep=',',
            skiprows=range(1, start_idx + 1),  # Skip rows before current chunk (keep header)
            nrows=nrows
        )

        return df_chunk

    def run_train(self, dataset_id: int):
        logging.info("Training segmentation model...")

        clear_memory([])

        train_file = os.path.normpath(os.path.join(self.model_handler_config.folder_for_train, "train.csv"))
        val_file = os.path.normpath(os.path.join(self.model_handler_config.folder_for_train, "val.csv"))
        logging.info(f"Train file path: {train_file}")
        logging.info(f"Validation file path: {val_file}")

        # Calculate chunk parameters for both files
        train_total, train_chunk_size, chunk_count = self.get_data_chunks(train_file)
        val_total, val_chunk_size, _ = self.get_data_chunks(val_file, target_chunk_count=chunk_count)

        logging.info(f"Train data: {train_total} rows, chunk size: {train_chunk_size}")
        logging.info(f"Validation data: {val_total} rows, chunk size: {val_chunk_size}")
        logging.info(f"Total chunks: {chunk_count}")

        # Get the base model folder path
        models_base_folder = os.path.join(ALL_MODELS_FOLDER, str(dataset_id))

        try:
            model, model_directory = self.initialize_model(models_base_folder)

            for stage in range(chunk_count):
                logging.info(f"\nStarting STAGE {stage + 1}/{chunk_count}")

                # Dynamically load training chunk
                training_data = self.load_data_chunk(train_file, stage, train_chunk_size, train_total)
                logging.info(f"Loaded training chunk {stage + 1}: {len(training_data)} rows")

                # Dynamically load validation chunk
                # validation_data = self.load_data_chunk(val_file, stage, val_chunk_size, val_total)
                # logging.info(f"Loaded validation chunk {stage + 1}: {len(validation_data)} rows")

                # Train on batch
                logging.info(f"Training on batch {stage + 1}...")
                if os.path.exists(model_directory):
                    self.temp_manager.reset_directory(model_directory)

                model.fit(
                    train_data=training_data,
                    tuning_data=training_data,  # Use validation_data if needed
                    save_path=model_directory
                )
                logging.info(f"Completed training for batch {stage + 1}")

                # Clear memory after each batch
                clear_memory()

                # Explicitly delete dataframes to free memory
                del training_data
                # del validation_data

        except Exception as error:
            logging.error(f"Training error: {error}")
            # Clean up the created directory if training fails
            TemporaryStorageManager().delete_storage(model_directory)
            exit(1)

        logging.info("Training complete.")

    
    def get_local_maxima_mask(self, prob_map, min_distance=1, threshold=0.5):
        """
        Создает бинарную маску с локальными максимумами из вероятностной карты.
        
        Parameters:
        -----------
        prob_map : numpy.ndarray
            Вероятностная карта (2D массив с вероятностями)
        min_distance : int
            Минимальное расстояние между локальными максимумами (размер окна)
        threshold : float
            Минимальный порог вероятности для отбора максимумов (0-1)
        
        Returns:
        --------
        binary_mask : numpy.ndarray
            Бинарная маска (True в позициях локальных максимумов)
        """
        # Применяем максимальный фильтр
        size = 2 * min_distance + 1
        local_max = maximum_filter(prob_map, size=size)
        
        # Локальные максимумы - это точки, где значение равно максимуму в окрестности
        is_local_max = (prob_map == local_max)
        
        # Применяем порог вероятности
        above_threshold = prob_map > threshold
        
        # Финальная маска - это пересечение условий
        binary_mask = is_local_max & above_threshold
        
        return binary_mask

    def run_predict(self, dataset_id: int):
        logging.info("Running segmentation inference...")

        folder_for_inference = os.path.normpath(self.model_handler_config.folder_for_inference)
        if not os.path.exists(folder_for_inference):
            raise FileNotFoundError(f"Data directory does not exist: {folder_for_inference}")

        models_base_folder = os.path.join(ALL_MODELS_FOLDER, str(dataset_id))

        # Get the latest model path using the same approach as in run_train
        model_directory = DataHandler.get_latest_model_path(
            base_folder=models_base_folder,
            model_name=self.model_handler_config.model_name
        )
        logging.info(f"Loading segmentation model from: {model_directory}")

        if not os.path.exists(model_directory):
            raise FileNotFoundError(f"Model directory does not exist: {model_directory}")

        # Check if this is a multi-class model by looking for label properties file
        label_properties_path = os.path.join(Config().UPLOAD_FOLDER, "label_properties.json")
        label_properties = LabelPropertiesLoader.load_label_properties(label_properties_path)
        logging.info(f"Loaded label properties for inference: {label_properties}")

        # Check if we have valid label properties
        if label_properties is None:
            logging.warning("No label properties found. Defaulting to single-class segmentation.")

        predictor_model = MultiModalPredictor.load(model_directory)

        results_folder_after_inference = os.path.normpath(self.model_handler_config.results_folder_after_inference)
        TemporaryStorageManager().create_storage(results_folder_after_inference)

        for img_file in tqdm(os.listdir(folder_for_inference)):
            img_path = os.path.normpath(os.path.join(folder_for_inference, img_file))
            if img_file.endswith('.png'):
                img_base_name = os.path.splitext(img_file)[0]
                try:
                    inference_df = pd.DataFrame({
                        "index": [img_base_name],
                        "image": [img_path]
                    })
                    # prediction = predictor_model.predict_proba(inference_df)

                    # binary_mask = self.get_local_maxima_mask(
                    #     prob_map=prediction[0],
                    #     min_distance=3,      # радиус окна для поиска максимумов
                    #     threshold=0.5        # минимальная вероятность
                    # )
                    # print(f"BINARY MASK SHAPE: {binary_mask.shape}")  # Print the shape of binary_mask.shape

                    prediction = predictor_model.predict(inference_df)
                    # prediction = predictor_model.predict({"image": [img_path]})
                    mask_file_path = os.path.normpath(
                        os.path.join(results_folder_after_inference, f"{img_base_name}_mask.png"))

                    ConvertorPalette2Rgba(label_properties=label_properties, output=mask_file_path,
                                          image_array=prediction[0]).execute()

                except Exception as e:
                    logging.error(f"Error processing image {img_file}: {e}")
            else:
                logging.info(f"Skipping unsupported file: {img_file}")

        logging.info("Segmentation inference complete.")

    def run_predict_with_erosion(self, dataset_id: int, kernel_size=3, iterations=1):
        """
        Performs segmentation inference with morphological erosion.
        Delegates to SegmentationErosionProcessor for erosion handling.

        Args:
            dataset_id: dataset identifier
            kernel_size: size of erosion kernel (default: 3)
            iterations: number of erosion iterations (default: 1)
        """
        erosion_processor = SegmentationErosionProcessor(self.model_handler_config)
        erosion_processor.run_predict_with_erosion(dataset_id, kernel_size, iterations)

    def initialize_model(self, models_base_folder):
        try:
            # Check if there are existing versions
            if DataHandler.get_number_of_version(models_base_folder, self.model_handler_config.model_name) == -1:
                # No versions exist yet, create the first one (v0)
                model_directory = DataHandler.save_model_path(models_base_folder, self.model_handler_config.model_name)
                logging.info(f"Created initial model version at: {model_directory}")

                # Initialize the segmentation model with the path where to save
                model = MultiModalPredictor(
                    presets='best_quality',
                    problem_type="semantic_segmentation",
                    validation_metric="iou",
                    eval_metric="iou",
                    label="label",
                    hyperparameters=self.model_handler_config.hyperparameters,
                    path=model_directory
                )
            else:
                # Get the latest model version and create a new one for saving updated model
                latest_model_path = DataHandler.get_latest_model_path(
                    base_folder=models_base_folder,
                    model_name=self.model_handler_config.model_name
                )
                logging.info(f"Latest model path: {latest_model_path}")

                # Create new version path for saving updated model
                model_directory = DataHandler.save_model_path(
                    base_folder=models_base_folder,
                    model_name=self.model_handler_config.model_name
                )
                logging.info(f"Will save new model to: {model_directory}")

                # Initialize the segmentation model with the path where to save
                model = MultiModalPredictor(
                    problem_type="semantic_segmentation",
                    validation_metric="iou",
                    label="label",
                    hyperparameters=self.model_handler_config.hyperparameters,
                    path=model_directory
                ).load(latest_model_path)

            return model, model_directory

        except Exception as error:
            logging.error(f"Initialize model error: {error}")
            # Clean up the created directory if training fails
            TemporaryStorageManager().delete_storage(model_directory)
            exit(1)


if __name__ == "__main__":
    # Example usage
    config = SegmentationModelConfig()
    temp_manager = TemporaryStorageManager()
    trainer = SegmentationModelHandler()

    # trainer.run_train(236)
    trainer.run_predict(236)

    # Use erosion with minimal parameters
    # trainer.run_predict_with_erosion(dataset_id=111, kernel_size=3, iterations=1)