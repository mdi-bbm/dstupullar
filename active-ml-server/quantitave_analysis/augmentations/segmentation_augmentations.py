import numpy as np
import pandas as pd
import logging
from typing import List, Tuple
from PIL import Image
import os

from quantitave_analysis.utils.image_processing import SegmentataionMaskSaver
from quantitave_analysis.utils.file_converter import ConvertorRgb2Palette
from quantitave_analysis.utils.image_processing import LabelPropertiesLoader
from quantitave_analysis.models.config import Config

MIN_INTENSITY_THRESHOLD = Config().MIN_INTENSITY_THRESHOLD
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ImageAugmenter:
    def augment(self, image: np.ndarray, mask: np.ndarray,
                do_flip: bool = True, do_scale: bool = False, do_rotate: bool = False) -> Tuple[
        List[np.ndarray], List[np.ndarray]]:
        """Single interface for all augmentations."""
        augmented_images = []
        augmented_masks = []
        logging.debug("Starting augmentation process")

        # Base case: always include the original image unless all augmentations are off
        if not (do_flip or do_scale or do_rotate):
            augmented_images.append(image)
            augmented_masks.append(mask)
            return augmented_images, augmented_masks

        # Flipping
        if do_flip:
            logging.debug("Applying flip augmentations")
            # Horizontal flip
            flip_x = np.flip(image, axis=1)
            # Vertical flip
            flip_y = np.flip(image, axis=0)
            # Both horizontal and vertical flip
            flip_xy = np.flip(np.flip(image, axis=1), axis=0)

            # Same for masks
            mask_x = np.flip(mask, axis=1)
            mask_y = np.flip(mask, axis=0)
            mask_xy = np.flip(np.flip(mask, axis=1), axis=0)

            flips = [image, flip_x, flip_y, flip_xy]
            mask_flips = [mask, mask_x, mask_y, mask_xy]
            augmented_images.extend(flips)
            augmented_masks.extend(mask_flips)
        else:
            augmented_images.append(image)
            augmented_masks.append(mask)

        # Scaling (applied to all previous images)
        if do_scale:
            logging.debug("Applying scale augmentations")
            scales = [0.5, 1.5]  # Example scales
            scaled_images = []
            scaled_masks = []
            for img, msk in zip(augmented_images[:], augmented_masks[:]):  # Copy to avoid modifying during iteration
                for scale in scales:
                    # PIL resize for better quality
                    h, w = img.shape[:2]
                    new_h, new_w = int(h * scale), int(w * scale)

                    # Convert numpy to PIL, resize, then back to numpy
                    pil_img = Image.fromarray(img)
                    pil_mask = Image.fromarray(msk)

                    scaled_pil_img = pil_img.resize((new_w, new_h), Image.BILINEAR)
                    scaled_pil_mask = pil_mask.resize((new_w, new_h), Image.NEAREST)

                    scaled_img = np.array(scaled_pil_img)
                    scaled_mask = np.array(scaled_pil_mask)

                    scaled_images.append(scaled_img)
                    scaled_masks.append(scaled_mask)
            augmented_images.extend(scaled_images)
            augmented_masks.extend(scaled_masks)

        # Rotation (applied to all previous images)
        if do_rotate:
            logging.debug("Applying rotation augmentations")
            angles = [90, 180, 270]  # Example angles
            rotated_images = []
            rotated_masks = []
            for img, msk in zip(augmented_images[:], augmented_masks[:]):  # Copy to avoid modifying during iteration
                for angle in angles:
                    # Convert numpy to PIL, rotate, then back to numpy
                    pil_img = Image.fromarray(img)
                    pil_mask = Image.fromarray(msk)

                    rotated_pil_img = pil_img.rotate(angle, Image.BILINEAR, expand=False)
                    rotated_pil_mask = pil_mask.rotate(angle, Image.NEAREST, expand=False)

                    rotated_img = np.array(rotated_pil_img)
                    rotated_mask = np.array(rotated_pil_mask)

                    rotated_images.append(rotated_img)
                    rotated_masks.append(rotated_mask)
            augmented_images.extend(rotated_images)
            augmented_masks.extend(rotated_masks)

        return augmented_images, augmented_masks


class SampleProcessor:
    def __init__(self):
        self.augmenter = ImageAugmenter()
        self.storage = SegmentataionMaskSaver()

    def process(self, img_file: str, mask_file: str, base_name: str, data_frame: pd.DataFrame) -> None:
        logging.info(f"Processing sample: image={img_file}, mask={mask_file}")
        try:
            # Open images with PIL in RGB mode
            pil_image = Image.open(img_file).convert('RGB')
            pil_mask = Image.open(mask_file).convert('RGB')

            # Convert PIL images to numpy arrays
            image = np.array(pil_image)
            mask = np.array(pil_mask)

            if image is None or mask is None:
                raise FileNotFoundError(f"Image or mask file not found: {img_file}, {mask_file}")
            logging.debug("Image and mask loaded successfully")

            # Toggle augmentations here (delete/comment lines to disable)
            do_flip = True  # Delete this line to disable flipping
            do_scale = False  # Delete or set True to enable scaling
            do_rotate = False  # Delete or set True to enable rotation

            # Apply augmentations via single interface
            img_flips, mask_flips = self.augmenter.augment(image, mask, do_flip, do_scale, do_rotate)
            logging.info(f"Generated {len(img_flips)} augmentations for {base_name}")

            # Load label properties
            label_properties_path = os.path.join(Config().UPLOAD_FOLDER, "label_properties.json")
            label_properties = LabelPropertiesLoader.load_label_properties(label_properties_path)
            logging.info(f"Loaded label properties: {label_properties}")

            # Check if we have valid label properties
            if label_properties is None:
                logging.warning("No label properties found. Defaulting to single-class segmentation.")

            for idx, (flip_img, flip_mask) in enumerate(zip(img_flips, mask_flips)):
                logging.debug(f"Processing augmentation {idx} for {base_name}")

                # Creating a mask for the background (black color)
                # Define pixels with intensity below the threshold as background
                is_background = np.mean(flip_mask, axis=2) < MIN_INTENSITY_THRESHOLD

                # Making an output image where we keep the original colors of the elements and set the background to black
                mask_output = flip_mask.copy()

                # Setting the background to black
                mask_output[is_background] = [0, 0, 0]

                # Convert numpy arrays to PIL for saving
                pil_img_to_save = Image.fromarray(flip_img)
                pil_mask_to_save = Image.fromarray(mask_output)

                # Save images using the storage class
                img_path = self.storage.save_image(np.array(pil_img_to_save), base_name, idx)
                mask_path = self.storage.save_mask(np.array(pil_mask_to_save), base_name, idx)

                ConvertorRgb2Palette(label_properties = label_properties, output = mask_path, image_array = mask_output).execute()
                # ConvertorRgb2Palette(label_properties = {'Standart_label': '#FF0000', 'Second_label': '#14FF00'}, output = mask_path, image_array = mask_output).execute()

                row_id = len(data_frame)
                data_frame.loc[row_id] = {'index': row_id, 'image': img_path, 'label': mask_path}
                logging.debug(f"Added row {row_id} to DataFrame: {img_path}, {mask_path}")

        except Exception as e:
            logging.error(f"Error processing sample {img_file} and {mask_file}: {e}")
