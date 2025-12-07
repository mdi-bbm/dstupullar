import os
import numpy as np
import logging
import json
from PIL import Image

from quantitave_analysis.utils.file_converter import ConversionOperationBase
from quantitave_analysis.models.config import Config

SEG_IMAGES_AFTER_AUG = Config().SEG_IMAGES_AFTER_AUG
SEG_MASKS_AFTER_AUG = Config().SEG_MASKS_AFTER_AUG
PROCESSED_FOLDER = Config().PROCESSED_FOLDER


class SegmentataionMaskSaver():
    def __init__(self):
        self.images_path = os.path.join(PROCESSED_FOLDER, SEG_IMAGES_AFTER_AUG)
        self.masks_path = os.path.join(PROCESSED_FOLDER, SEG_MASKS_AFTER_AUG)

    def save_image(self, image: np.ndarray, base_name: str, idx: int) -> str:
        path = os.path.join(self.images_path, f'{base_name}{idx}.png')
        logging.debug(f"Saving image to {path}")
        Image.fromarray(image).save(path, format='PNG')
        #logging.info(f"Image saved: {path}")
        return path

    def save_mask(self, mask: np.ndarray, base_name: str, idx: int) -> str:
        path = os.path.join(self.masks_path, f'{base_name}{idx}.png')
        logging.debug(f"Saving mask to {path}")
        # Image.fromarray(mask).save(path, format='PNG')
        #logging.info(f"Mask saved: {path}")
        return path

class LabelPropertiesLoader:
    @staticmethod
    def load_label_properties(file_path):
        """Load label properties from a JSON file"""
        try:
            if file_path.endswith('.txt'):
                # Handle TXT files containing JSON
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    label_properties = json.loads(content)
            else:
                # Handle JSON files
                with open(file_path, 'r') as f:
                    label_properties = json.load(f)

            logging.info(f"Label properties loaded from {file_path}")
            return label_properties
        except FileNotFoundError:
            logging.warning(f"Label properties file not found at {file_path}")
            return {}
        except json.JSONDecodeError:
            logging.error(f"Error parsing JSON from {file_path}")
            return {}
        except Exception as e:
            logging.error(f"Error loading label properties from {file_path}: {e}")
            return {}
class MaskSaver(ConversionOperationBase):
    """For single class mask saving"""
    # label_color: str = ''

    # def __init__(self, input, output, label_color):
    #     super().__init__(input=input, output=output)
    #     self.label_color = label_color  # String color_hex

    def execute(self):
        try:
            mask_data = np.squeeze(np.transpose(self.input, (1, 2, 0)), axis=2)

            mask_layer = np.ones_like(mask_data) * 255

            inverted_mask = (mask_layer - mask_data * 255).astype(np.uint8)

            logging.info(f"Converting predicted_mask → PNG")

            logging.info(f"The maximum value in the mask: {np.max(inverted_mask)}")

            # Creating an image from a mask
            image = Image.fromarray(inverted_mask)
            img = image.convert("RGBA")
            pixdata = img.load()

            # Pixel processing
            for y in range(img.size[1]):
                for x in range(img.size[0]):
                    if pixdata[x, y] == (0, 0, 0, 255):
                        pixdata[x, y] = (0, 0, 0, 0)
                    # if pixdata[x, y] == (255, 255, 255, 255):
                    #     pixdata[x, y] = hex_to_rgb(self.label_color)

            # Saving the image
            img.save(str(self.output) + ".png")

            logging.info(f"Conversion completed. PNG saved to {self.output}")

        except Exception as e:
            logging.error(f"Error saving the mask {self.output}: {e}")

class MaskSaverWebp(ConversionOperationBase):
    def execute(self):
        try:
            mask_data = np.squeeze(np.transpose(self.input, (1, 2, 0)), axis=2)
            white_layer = np.ones_like(mask_data) * 255
            inverted_mask = (white_layer - mask_data * 255).astype(np.uint8)

            logging.info(f"Converting predicted_mask → WEBP")

            logging.info(f"The maximum value in the mask: {np.max(inverted_mask)}")

            image = Image.fromarray(inverted_mask)

            image.save(str(self.output) + ".webp", "WEBP", quality=80)

            logging.info(f"Conversion completed. WEBP saved to {self.output}")

        except Exception as e:
            logging.error(f"Error saving the mask {self.output}: {e}")