import os
from pydantic import PrivateAttr
import shutil
import glob
import random
import warnings
import gc
import json
import logging
import torch

from quantitave_analysis.models.config import Config
from quantitave_analysis.utils.temporary_storage import TemporaryStorageManager, DataHandler
from common.tools.clear_routines import clear_memory
from quantitave_analysis.models.common.base_model import ModelHandlerBase
from quantitave_analysis.models.detection.results_processor import ResultProcessor
from quantitave_analysis.models.detection.detection_config import DetectionModelConfig
from quantitave_analysis.models.detection.dino_model_manager import DinoModelManager
from quantitave_analysis.models.detection.dino_data_processor import DinoDataProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='training.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# torch.cuda.set_per_process_memory_fraction(0.8)
print(f"Available GPU memory: {torch.cuda.get_device_properties(0).total_memory/1024**3:.2f}GB")
print(f"Currently allocated: {torch.cuda.memory_allocated(0)/1024**3:.2f}GB")
# At start of your training script
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.deterministic = False
torch.set_float32_matmul_precision('medium')
# Reduce pytorch lightning memory usage
os.environ["PL_FAULT_TOLERANT_TRAINING"] = "1"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"
#logging.info("Setting torch.float32_matmul_precision to 'medium'")
torch.set_float32_matmul_precision("medium")

#from autogluon.multimodal import MultiModalPredictor

# Suppress specific warnings
warnings.filterwarnings("ignore", message="torch.meshgrid: in an upcoming release.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torchmetrics.utilities.prints")


class DinoDetectionModelHandler(ModelHandlerBase):
    model_handler_config: DetectionModelConfig = DetectionModelConfig()
    temp_manager: TemporaryStorageManager = TemporaryStorageManager()
    result_processor: ResultProcessor = ResultProcessor()
        
    _data_processor: DinoDataProcessor = PrivateAttr(DinoDataProcessor())
    _model_manager: DinoModelManager = PrivateAttr(DinoModelManager())
    
    def __post_init__(self):
        self._data_processor = DinoDataProcessor(
            model_handler_config=self.model_handler_config,
            temp_manager=self.temp_manager,
            result_processor=self.result_processor
        )
        self._model_manager = DinoModelManager()

    def run_train(self, dataset_id: int):
        """Train the detection model using iterative batches of 30 images per stage."""
        logger.info("Training detection model...")
        clear_memory()

        # Paths and configuration
        image_dir = os.path.join(self.model_handler_config.train_data_folder, 'images')
        annotations_dir = os.path.join(self.model_handler_config.train_data_folder, "Annotations")

        labels_path = os.path.join(self.model_handler_config.train_data_folder, "labels.txt")
        train_json_path = os.path.join(annotations_dir, "train.json")

        labels_path = os.path.join(self.model_handler_config.train_data_folder, "labels.txt")

        class_names = self._data_processor.extract_classes_from_coco_json(train_json_path)
        try:
            with open(labels_path, "w") as f:
                f.write("\n".join(class_names))
            logger.info(f"Created labels.txt at: {labels_path} with classes: {class_names}")
        except Exception as e:
            logger.error(f"Failed to create labels.txt: {e}")

        # Creating a mapping and updating labels.txt
        class_mapping = self.create_class_mapping(labels_path, self.model_handler_config.train_data_folder)

        # Updating with the mapping from train.json and test.json
        train_json_path = os.path.join(self.model_handler_config.train_data_folder, "Annotations", "train.json")
        test_json_path = os.path.join(self.model_handler_config.train_data_folder, "Annotations", "test.json")
        self.update_json_classes(train_json_path, class_mapping)
        self.update_json_classes(test_json_path, class_mapping)

        class_names = self._data_processor.extract_classes_from_coco_json(train_json_path)

        models_base_folder = os.path.join(Config().ALL_MODELS_FOLDER, str(dataset_id))

        # Load full training data
        with open(train_json_path, 'r') as f:
            full_train_data = json.load(f)

        all_images = full_train_data['images']
        n_total_images = len(all_images)
        logging.info(f"Found {n_total_images} training images")

        # Calculate number of stages based on batch size of 30
        batch_size = 30
        n_stages = (n_total_images + batch_size - 1) // batch_size  # Ceiling division
        logging.info(f"Calculated {n_stages} stages with batch size {batch_size}")                

        try:
            # Validate image directory
            if not os.path.exists(image_dir):
                raise FileNotFoundError(f"Image directory not found: {image_dir}")

            # Load COCO dataset
            coco_data = self._data_processor.load_coco_data(train_json_path)
            images = coco_data.get("images", [])
            if not images:
                raise ValueError("No images found in COCO dataset.")

            # Shuffle images once at the start
            shuffled_images = random.sample(images, len(images))
            logging.info("Shuffled all images for training")

            # Create temporary directory for batch JSONs
            temp_dir = self.temp_manager.create_temp_directory()
            
            predictor, temp_version_path  = self._model_manager.initialize_predictor(models_base_folder)

            try:
                # Training iterations
                for stage in range(n_stages):
                    self.check_memory_available(min_gb=4)

                    # Select batch of images for the current stage
                    selected_images = self._data_processor.select_batch_images(images, batch_size, image_dir, stage, shuffled_images)

                    # Create batch COCO JSON with corrected paths
                    batch_json_path = self._data_processor.create_batch_coco_json(selected_images, coco_data, temp_dir, stage, image_dir)

                    # Train on batch
                    logger.info(f"Training on batch {stage + 1}...")

                    predictor.fit(
                        train_data=batch_json_path,
                        # time_limit=self.model_handler_config.hyperparameters["time_limit"],
                        save_path=temp_version_path,
                    )
                    logger.info(f"Completed training for batch {stage + 1}")
                    logger.info(f"{n_stages - stage - 1} batches left.")
            
                    clear_memory()
                    
                    # Removes the temporary folder that fills up during training and moves the files to just a version folder
                    final_version_path = self._model_manager.finalize_model_version(temp_version_path, models_base_folder, train_json_path) 
            
            except Exception as e:
                logger.error(f"Training failed for batch {stage + 1}: {e}")

                del predictor
                self.temp_manager.delete_storage(temp_version_path)
                gc.collect()
                clear_memory()

            # Create labels.txt in the final version
            labels_path = os.path.join(final_version_path, "labels.txt")
            class_names = self._data_processor.extract_classes_from_coco_json(train_json_path)
            with open(labels_path, "w") as f:
                f.write("\n".join(class_names))
            
            class_mapping_path = os.path.join(self.model_handler_config.train_data_folder, "class_mapping.json")
            new_class_mapping_path = os.path.join(final_version_path, "class_mapping.json")
            shutil.move(class_mapping_path, new_class_mapping_path)
        
            logger.info(f"class_mapping.json moved to final version {final_version_path}.")
            logger.info("Training complete.")
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
    
    def run_predict(self, dataset_id: int):

        logging.info("Starting detection inference...")
        
        try:            
            image_files = glob.glob(f"{self.model_handler_config.inference_data_folder}/*.png")
            if not image_files:
                raise FileNotFoundError("No images found in inference folder")
                
            result_paths = self._data_processor.process_predictions(image_files, dataset_id)
            
            logging.info("Detection inference completed successfully")
            return result_paths
            
        except Exception as e:
            logging.error(f"Inference failed: {str(e)}")
            raise
            
    def check_memory_available(self, *, min_gb=4):
        free, total = torch.cuda.mem_get_info()
        free_gb = free / (1024**3)
        if free_gb < min_gb:
            clear_memory()
            free, total = torch.cuda.mem_get_info()
            free_gb = free / (1024**3)
            if free_gb < min_gb:
                raise RuntimeError(f"Insufficient GPU memory. Required: {min_gb}GB, Available: {free_gb:.2f}GB")

    def create_class_mapping(self, labels_path, model_dir):
        class_mapping = {}
        reverse_class_mapping = {}
        
        # Reading actual classes from labels.txt.
        if os.path.exists(labels_path):
            with open(labels_path, 'r') as f:
                real_classes = [line.strip() for line in f if line.strip()]
            
            # Creating a mapping: real_name -> classN
            for idx, real_class in enumerate(real_classes, 1):
                class_mapping[real_class] = f"class{idx}"
                reverse_class_mapping[f"class{idx}"] = real_class
            
            # Saving the mapping to a file
            mapping_path = os.path.join(model_dir, "class_mapping.json")
            with open(mapping_path, 'w') as f:
                json.dump({"forward": class_mapping, "reverse": reverse_class_mapping}, f)
            
            # Create a new labels.txt with the aliases
            new_labels_path = os.path.join(model_dir, "labels.txt")
            with open(new_labels_path, 'w') as f:
                for idx in range(1, len(real_classes) + 1):
                    f.write(f"class{idx}\n")
            
            logger.info(f"Created class mapping and updated labels.txt at {new_labels_path}")
            return class_mapping
        else:
            logger.warning(f"labels.txt not found at {labels_path}")
            return {}

    def update_json_classes(self, json_path, class_mapping):
        if not os.path.exists(json_path):
            logger.warning(f"JSON file not found at {json_path}")
            return

        with open(json_path, 'r') as f:
            data = json.load(f)

        # Checking for the 'categories' key in the JSON
        if 'categories' not in data:
            logger.warning(f"No 'categories' key found in {json_path}")
            return

        # Mapping the old category_ids to the new ones
        category_id_mapping = {}
        new_categories = []
        for idx, cat in enumerate(data['categories'], 1):
            real_class = cat['name']
            if real_class in class_mapping:
                new_class = class_mapping[real_class]
                category_id_mapping[cat['id']] = idx  # Old ID -> New ID
                new_categories.append({
                    'id': idx,
                    'name': new_class,
                    'supercategory': cat.get('supercategory', '')
                })
            else:
                logger.warning(f"Class {real_class} not found in class_mapping")
                # Keep the original category if there's no mapping
                category_id_mapping[cat['id']] = cat['id']
                new_categories.append(cat)

        # Updating the categories
        data['categories'] = new_categories

        # Updating category_id in the annotations
        if 'annotations' in data:
            for ann in data['annotations']:
                old_category_id = ann['category_id']
                if old_category_id in category_id_mapping:
                    ann['category_id'] = category_id_mapping[old_category_id]
                else:
                    logger.warning(f"Category ID {old_category_id} not found in category_id_mapping")

        # Saving the updated JSON
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Updated classes in {json_path}")


if __name__ == "__main__":
    # Example usage
    config = DetectionModelConfig()
    temp_manager = TemporaryStorageManager()
    trainer = DinoDetectionModelHandler()
    
    # Specify COCO JSON path and number of iterations
    coco_json_path = os.path.join(config.train_data_folder, "Annotations", "train.json")
    num_iterations = config.epochs
    
    trainer.run_train(181)