from pydantic import BaseModel
import os

class Config(BaseModel):
    # Define your configuration fields with type hints and default values
    storage_root: str = os.path.abspath((os.path.join(os.path.dirname(__file__), '../')))
    UPLOAD_FOLDER: str = os.path.join(storage_root, 'data', 'uploads')
    RETURN_FOLDER: str = os.path.join(storage_root, 'data', 'return_files')
    PROCESSED_FOLDER: str = os.path.join(storage_root, 'data', 'processed')
    MODELS_DIRECTORY: str = os.path.join(storage_root,'data', 'models')
    ALL_MODELS_FOLDER: str = os.path.join(storage_root, 'saved_models')
    MIN_INTENSITY_THRESHOLD: int = 5
    SHARED_FOLDER_AFTER_AUG: str = os.path.join('data', 'processed')
    SEG_IMAGES_AFTER_AUG: str = 'all_images'
    SEG_MASKS_AFTER_AUG: str = 'all_masks'
    MASK_POSTFIX: str = '_mask'
    SPLIT_FRACTIONS: list = [0.9, 0.1]
    CONFIDENCE_THRESHOLD: float = 0.99
    OUTPUT_JSON_NAME: str = 'output.json'
    SUPPORTED_IMAGE_TYPES: str = ".png"
    IMAGE_TYPES_FROM_FRONT: str = '.webp'
    DEFAULT_CREATE_DATASET_RATIO: float = 0.9
    INTERSECTION_THRESHOLD: float = 0.9

    # Optional: Add validation for fields
    class Settings:
        # Use environment variables to override defaults (optional)
        env_prefix = "APP_"  # Environment variables will be prefixed with "APP_"
        case_sensitive = False  # Allow case-insensitive environment variables

# Create an instance of the Config class
config = Config()
