# caller_script.py

import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from quantitave_analysis.augmentations.segmentation_augmentations import SampleProcessor
from quantitave_analysis.models.config import Config

SUPPORTED_IMAGE_TYPES = Config().SUPPORTED_IMAGE_TYPES
PROCESSED_FOLDER = Config().PROCESSED_FOLDER
UPLOAD_FOLDER = Config().UPLOAD_FOLDER
MASK_POSTFIX = Config().MASK_POSTFIX
SEG_IMAGES_AFTER_AUG = Config().SEG_IMAGES_AFTER_AUG
SEG_MASKS_AFTER_AUG = Config().SEG_MASKS_AFTER_AUG

def process_all_samples(processor, data_table, input_path):
    files = sorted(os.listdir(input_path))
    image_files = [f for f in files if f.endswith(SUPPORTED_IMAGE_TYPES) and MASK_POSTFIX not in f]

    for filename in image_files:
        img_full_path = os.path.join(input_path, filename)
        mask_filename = f"{filename.split('.')[0]}{MASK_POSTFIX}.png"
        mask_full_path = os.path.join(input_path, mask_filename)

        if os.path.exists(mask_full_path):
            base_name = filename.split('.')[0]
            processor.process(
                img_file=img_full_path,
                mask_file=mask_full_path,
                base_name=base_name,
                data_frame=data_table
            )

def main():
    print("Calling the segmentation augmentations main function...")

    processor = SampleProcessor()
    self_columns = ["index", "image", "label"]
    data_table = pd.DataFrame(columns=self_columns)
    input_path = UPLOAD_FOLDER

    process_all_samples(processor, data_table, input_path)

    print("Finished calling main function.")
    
if __name__ == "__main__":
    main()
