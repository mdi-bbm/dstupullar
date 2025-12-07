from tqdm import tqdm
import pandas as pd
import logging
import os

from quantitave_analysis.augmentations.segmentation_augmentations import SampleProcessor
from quantitave_analysis.utils.temporary_storage import TemporaryStorageManager
from quantitave_analysis.models.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SUPPORTED_IMAGE_TYPES = Config().SUPPORTED_IMAGE_TYPES
PROCESSED_FOLDER = Config().PROCESSED_FOLDER
UPLOAD_FOLDER = Config().UPLOAD_FOLDER
MASK_POSTFIX = Config().MASK_POSTFIX
SEG_IMAGES_AFTER_AUG = Config().SEG_IMAGES_AFTER_AUG
SEG_MASKS_AFTER_AUG = Config().SEG_MASKS_AFTER_AUG


class SegmentationDatasetPreparer:
    def __init__(self):
        self.processor = SampleProcessor()
        #self.output_path = SHARED_FOLDER_AFTER_AUG
        self.columns = ["index", "image", "label"]
        # self.split_fractions = [0.9, 0.1]
        self.split_fractions = [1, 0]
        self.storage = TemporaryStorageManager()
        self.images_path = os.path.join(PROCESSED_FOLDER, SEG_IMAGES_AFTER_AUG)
        self.masks_path = os.path.join(PROCESSED_FOLDER, SEG_MASKS_AFTER_AUG)
        
    def create_dataset(self, input_path: str, output_path: str) -> None:
        logging.info("Starting main execution segmentation_prepare_dataset")
        logging.info(f"Starting dataset preparation for {input_path}")
        try:
            self.storage.create_storage(self.images_path)
            self.storage.create_storage(self.masks_path)

            data_table = pd.DataFrame(columns=self.columns)
            files = sorted(os.listdir(input_path))
            image_files = [f for f in files if f.endswith(SUPPORTED_IMAGE_TYPES) and MASK_POSTFIX not in f]

            logging.info(f"Found {len(image_files)} potential image files in {input_path}")
            for filename in tqdm(image_files):
                img_full_path = os.path.join(input_path, filename)
                mask_filename = f"{filename.split('.')[0]}{MASK_POSTFIX}.png"
                mask_full_path = os.path.join(input_path, mask_filename)

                if os.path.exists(mask_full_path):
                    base_name = filename.split('.')[0]
                    self.processor.process(img_full_path, mask_full_path, base_name, data_table)
                else:
                    logging.warning(f"Mask file not found for image: {filename}")

            if data_table.empty:
                logging.warning("No valid image-mask pairs found to process.")
            else:
                logging.info(f"Processed {len(data_table)} augmented samples")
                self._split_and_save(data_table)
                logging.info("Segmentation dataset preparation completed successfully")
            
        except Exception as e:
            logging.critical(f"Critical error in dataset preparation: {e}")

    def _split_and_save(self, data_table: pd.DataFrame, output_path: str = PROCESSED_FOLDER) -> None:
        total_images = len(data_table)
        train_count = int(total_images * self.split_fractions[0])
        logging.info(f"Splitting {total_images} samples: {train_count} train, {total_images - train_count} val")
        
        train_data = data_table.iloc[:train_count].reset_index(drop=True)
        val_data = data_table.iloc[train_count:].reset_index(drop=True)

        if val_data.empty and not train_data.empty:
            val_data = train_data.iloc[-1:].reset_index(drop=True)
            train_data = train_data.iloc[:-1].reset_index(drop=True)
            logging.debug("Adjusted split: moved one sample to validation set")

        train_csv_path = os.path.join(output_path, 'train.csv')
        val_csv_path = os.path.join(output_path, 'val.csv')
        
        logging.debug(f"Saving train data to {train_csv_path}")
        train_data.to_csv(train_csv_path, sep=',', index=False)
        logging.debug(f"Saving validation data to {val_csv_path}")
        val_data.to_csv(val_csv_path, sep=',', index=False)
        logging.info(f"CSVs saved: {train_csv_path} ({len(train_data)} rows), {val_csv_path} ({len(val_data)} rows)")

if __name__ == '__main__':
    pipeline = SegmentationDatasetPreparer()
    pipeline.create_dataset(UPLOAD_FOLDER, PROCESSED_FOLDER)