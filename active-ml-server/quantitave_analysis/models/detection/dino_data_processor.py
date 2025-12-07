import os
import shutil
import json
from typing import List, Dict
import time
import logging
from autogluon.multimodal import MultiModalPredictor
from abc import ABC

from common.models import DigitalAssistantBase
from quantitave_analysis.models.config import Config 
from quantitave_analysis.utils.temporary_storage import TemporaryStorageManager, DataHandler
from quantitave_analysis.models.detection.detection_config import DetectionModelConfig
from quantitave_analysis.models.detection.results_processor import ResultProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DinoDataProcessor(ABC, DigitalAssistantBase):
    model_handler_config: DetectionModelConfig = DetectionModelConfig()
    temp_manager: TemporaryStorageManager = TemporaryStorageManager()
    result_processor: ResultProcessor = ResultProcessor()

    def load_coco_data(self, coco_json_path: str) -> Dict:
        """Load COCO JSON file."""
        try:
            with open(coco_json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load COCO JSON file: {e}")
            raise

    def create_batch_coco_json(self, selected_images: List[Dict], coco_data: Dict, batch_dir: str, batch_idx: int, image_dir: str) -> str:
        """Create a temporary COCO JSON for a batch of images, ensuring correct image paths."""
        batch_coco = {
            "info": coco_data.get("info", {}),
            "licenses": coco_data.get("licenses", []),
            "categories": coco_data.get("categories", []),
            "images": [],
            "annotations": []
        }

        # Update image paths to point to the actual image directory
        for img in selected_images:
            img_copy = img.copy()
            # Ensure file_name is relative to image_dir or absolute
            original_file_name = img_copy.get("file_name", "")
            absolute_path = os.path.join(image_dir, os.path.basename(original_file_name))
            if os.path.exists(absolute_path):
                img_copy["file_name"] = absolute_path
                batch_coco["images"].append(img_copy)
            else:
                logger.warning(f"Image not found, skipping: {absolute_path}")

        # Filter annotations for selected images
        image_ids = {img["id"] for img in batch_coco["images"]}
        batch_coco["annotations"] = [
            ann for ann in coco_data.get("annotations", []) if ann["image_id"] in image_ids
        ]

        if not batch_coco["images"]:
            raise ValueError("No valid images found for batch after path validation.")

        # Save batch COCO JSON
        batch_json_path = os.path.join(batch_dir, f"batch_{batch_idx}.json")
        try:
            with open(batch_json_path, 'w') as f:
                json.dump(batch_coco, f)
            logger.info(f"Created batch COCO JSON at: {batch_json_path} with {len(batch_coco['images'])} images")
            return batch_json_path
        except Exception as e:
            logger.error(f"Failed to create batch COCO JSON: {e}")
            raise

    def select_batch_images(self, images: List[Dict], batch_size: int, image_dir: str, stage: int, shuffled_images: List[Dict]) -> List[Dict]:
        """Select a batch of images from the pre-shuffled list for the current stage."""
        total_images = len(shuffled_images)
        if total_images == 0:
            raise ValueError("No images available in the dataset.")

        # Calculate start and end indices for the current stage
        start_idx = stage * batch_size
        end_idx = min(start_idx + batch_size, total_images)

        # Select images for the current stage
        selected_images = shuffled_images[start_idx:end_idx]

        # Validate that selected images exist on disk
        valid_images = []
        for img in selected_images:
            file_name = img.get("file_name", "")
            image_path = os.path.join(image_dir, os.path.basename(file_name))
            if os.path.exists(image_path):
                valid_images.append(img)
            else:
                logger.warning(f"Image not found, skipping: {image_path}")

        if not valid_images:
            raise ValueError(f"No valid images found for stage {stage + 1} in directory: {image_dir}")

        # If fewer valid images than batch_size, log a warning and return what we have
        if len(valid_images) < batch_size:
            logger.warning(f"Stage {stage + 1}: Only {len(valid_images)} valid images available, less than batch_size {batch_size}.")

        return valid_images
    def extract_classes_from_coco_json(self, json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)

        # Extract class names in the order of their IDs
        categories = sorted(data['categories'], key=lambda x: x['id'])
        class_names = [cat['name'] for cat in categories]
        return class_names

    def process_predictions(self, image_files: list, dataset_id: int) -> list:
        result_paths = []
        models_base_folder = os.path.join(Config().ALL_MODELS_FOLDER, str(dataset_id))

        # Initialize lists and variables to track timing
        inference_times = []  # Store inference time for each image
        total_inference_time = 0.0  # Track total inference time

        try:
            model_dir = DataHandler.get_latest_model_path(
                base_folder=models_base_folder,
                model_name=self.model_handler_config.model_name
            )

            if not os.path.exists(os.path.join(model_dir, "assets.json")):
                logger.error(f"No model with assets.json found in {model_dir}")

            labels_path = os.path.join(self.model_handler_config.train_data_folder, "Annotations", "labels.txt")
            self.temp_manager.create_storage(labels_path)
            actual_model_labels_path = os.path.join(model_dir, "labels.txt")

            if os.path.exists(actual_model_labels_path):
                shutil.copy2(actual_model_labels_path, labels_path)
                logger.info(f"Copied labels.txt from {model_dir} to {labels_path}")
            else:
                logger.warning(f"labels.txt not found in {model_dir}")

            logger.info(f"Loading model from: {model_dir}")
            predictor = MultiModalPredictor(
                problem_type="object_detection",
                sample_data_path=self.model_handler_config.train_data_folder
            ).load(model_dir)
            
            predictor.set_num_gpus(1)
            
        except Exception as e:  
            logger.error(f"Failed to load model: {str(e)}")
            raise

        glob_json_str = "{"

        for image_path in image_files:
            data = {
                "images": [{"id": 0, "width": -1, "height": -1, "file_name": image_path}],
                "categories": []
            }
            temp_json = os.path.join(self.model_handler_config.results_folder, os.path.basename(image_path) + ".json")

            with open(temp_json, "w") as f:
                json.dump(data, f)

            # Measure inference time for this image
            start_time = time.time()
            res = predictor.predict(temp_json, save_results=True)
            end_time = time.time()
            inference_time = end_time - start_time
            inference_times.append(inference_time)
            total_inference_time += inference_time
            logger.info(f"Inference time for {image_path}: {inference_time:.4f} seconds")

            # Pass the temp_json or prediction result instead of self
            result_path = self.result_processor.process_combined_results(model_dir)
            glob_json_str += result_path
            glob_json_str += "," if image_files[-1] != image_path else "}"

            result_paths.append(result_path)

        # Calculate and log average inference time
        if inference_times:
            avg_inference_time = total_inference_time / len(inference_times)
            logger.info(f"Total inference time for {len(inference_times)} images: {total_inference_time:.4f} seconds")
            logger.info(f"Average inference time per image: {avg_inference_time:.4f} seconds")

        output_json_path = os.path.join(self.model_handler_config.results_folder, "output.json")

        with open(output_json_path, "w") as f:
            f.write(glob_json_str)
        
        return result_paths