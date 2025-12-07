import os
# import cv2
import logging
from abc import ABC, abstractmethod
import numpy as np
from PIL import Image
from typing import List, Optional
import numpy.typing as npt
import json
import csv
from pathlib import Path

from common.models import DigitalAssistantBase
from quantitave_analysis.models.config import Config  

CONFIDENCE_THRESHOLD = Config().CONFIDENCE_THRESHOLD

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

class ConversionOperationBase(DigitalAssistantBase, ABC):
    input: str | Path | np.ndarray = ''
    output: str | Path
    label_properties: Optional[dict] = None
    image_array: Optional[np.array] = None

    @abstractmethod
    def execute(self):
        raise NotImplementedError("Subclasses must implement the execute method")


class ConvertorBboxJson2Csv:
    def __init__(self, input_path, output_folder):
        self.input_path = Path(input_path)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)  # Create a folder if it doesn't exist
    
    def execute(self):
        """Converts JSON with bbox into separate CSV files by image names"""
        with self.input_path.open('r') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            raise ValueError("Expected JSON data to be a dictionary")
        
        for image_name, annotations in data.items():
            if isinstance(annotations, str):
                #logging.warning(f"Skipping invalid entry for image {image_name}: annotations is a string")
                continue
            
            if not isinstance(annotations, list):
                raise ValueError(f"Expected annotations for {image_name} to be a list")
            
            output_file = self.output_folder / f"{image_name}.csv"
            
            with output_file.open('w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(['label_name', 'bbox_x', 'bbox_y', 'bbox_width', 'bbox_height', 'image_name', 'image_width', 'image_height'])
                
                for ann in annotations:
                    if not isinstance(ann, dict):
                        raise ValueError(f"Expected annotation to be a dictionary, got {type(ann)}")
                    
                    writer.writerow([
                        ann['label_name'], ann['bbox_x'], ann['bbox_y'], ann['bbox_width'], ann['bbox_height'],
                        image_name, ann['image_width'], ann['image_height']
                    ])

class ConvertorRgb2Palette(ConversionOperationBase):
    def save_image_to_palette(
            self,
            image: npt.NDArray,
            palette: List[List[int]],
            save_path: str
    ) -> None:
        """Save an image as a palette-based PNG

        Args:
            image: An indexed numpy array where each value is an index into the palette
            palette: A list of RGB colors, where each color is a list of [R, G, B] values
            save_path: Path where to save the image
        """
        # Convert the numpy array to a PIL image in mode 'P' (palette)
        image = Image.fromarray(image.astype(np.uint8)).convert("P")

        # Convert palette to flat list as required by putpalette
        flat_palette = [value for color in palette for value in color]

        # Apply palette to the image
        image.putpalette(flat_palette)

        # Save the image
        image.save(save_path)

    def execute(self):
        # Getting the values and turning them into a list
        colors_list = list(self.label_properties.values())

        palette = [[0,0,0]]
        for i in range(len(colors_list)):
            palette.append(ConvertorHex2Rgb.hex_to_rgb(colors_list[i]))

        img_arr = self.image_array

        # Creating a palette image
        height, width = img_arr.shape[:2]

        # Turn the palette into a numpy array
        palette_np = np.array(palette)

        # Taking the RGB channels of the image
        rgb_pixels = img_arr[:, :, :3].reshape(-1, 3)

        # Calculating the distance matrix from each pixel to each color in the palette
        # Transforming the data shape for broadcasting operations
        pixels_expanded = rgb_pixels.reshape(-1, 1, 3)
        palette_expanded = palette_np.reshape(1, -1, 3)

        # Calculating the square of the Euclidean distance
        distances = np.sum((pixels_expanded - palette_expanded) ** 2, axis=2)

        # Finding the index of the closest color for each pixel
        nearest_indices = np.argmin(distances, axis=1)

        # Convert it back to image form
        palette_image = nearest_indices.reshape(height, width)

        self.save_image_to_palette(
            palette_image,
            palette,   
            self.output
        )


class ConvertorPalette2Rgba(ConversionOperationBase):
    def execute(self):
        # Get the values and turn them into a list
        colors_list = list(self.label_properties.values())

        palette = [[0, 0, 0]]
        for i in range(len(colors_list)):
            palette.append(ConvertorHex2Rgb.hex_to_rgb(colors_list[i]))

        # Uploading an image with indices
        palette_arr = self.image_array

        # Getting rid of the extra dimension (taking the first layer)
        palette_arr = palette_arr[0]
        height, width = palette_arr.shape

        # Creating a new image with RGBA
        rgba_image = np.zeros((height, width, 4), dtype=np.uint8)

        # Making masks for each index in the palette
        for index, color in enumerate(palette):
            mask = (palette_arr == index)
            # For the RGB channels (the first 3)
            rgba_image[mask, :3] = color  # RGB components

            # Setting the alpha channel (0 for index 0, 255 for the others)
            rgba_image[mask, 3] = 0 if index == 0 else 255

        # Creating an image from an array
        rgba_image_pil = Image.fromarray(rgba_image, mode='RGBA')

        # Saving the new image
        rgba_image_pil.save(self.output)

class ConvertorHex2Rgb(ConversionOperationBase):
    def hex_to_rgb(hex_color):
            """Convert hex color string to RGB tuple"""
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

class ConvertorCsv2CocoJson:
    def __init__(self, input, output):
        self.input = input
        self.output = output
    
    def execute(self):
        """Converts CSV to COCO JSON with the right structure"""
        with self.input.open('r') as csv_file:
            reader = csv.DictReader(csv_file)
            required_columns = ['bbox_x', 'bbox_y', 'bbox_width', 'bbox_height', 'label_name', 'image_name', 'image_width', 'image_height']
            
            for column in required_columns:
                if column not in reader.fieldnames:
                    raise KeyError(f"Missing mandatory column: {column}")
            
            images = {}
            annotations = []
            categories = {}
            annotation_id = 1
            image_id = 1
            
            for row in reader:
                if row['image_name'] not in images:
                    images[row['image_name']] = {
                        "id": image_id,
                        "file_name": f"images/{row['image_name']}",
                        "width": int(row['image_width']),
                        "height": int(row['image_height'])
                    }
                    image_id += 1
                
                if row['label_name'] not in categories:
                    categories[row['label_name']] = len(categories) + 1
                
                annotations.append({
                    "id": annotation_id,
                    "image_id": images[row['image_name']]['id'],
                    "category_id": categories[row['label_name']],
                    "bbox": [
                        int(round(float(row['bbox_x']))),
                        int(round(float(row['bbox_y']))),
                        int(round(float(row['bbox_width']))),
                        int(round(float(row['bbox_height'])))
                    ],
                    "area": int(round(float(row['bbox_width']) * float(row['bbox_height']))),
                    "iscrowd": 0
                })
                annotation_id += 1
            
        coco_output = {
            "images": list(images.values()),
            "annotations": annotations,
            "categories": [{"id": cid, "name": name} for name, cid in categories.items()]
        }
        
        with self.output.open('w') as f:
            json.dump(coco_output, f, indent=4)

class ConvertorWebp2Png(ConversionOperationBase):
    def execute(self):
        logging.info(f"Converting WEBP → PNG: {self.input}")

        image = Image.open(self.input)
        image.save(self.output, "PNG")

        logging.info(f"Conversion completed. PNG saved to {self.output}")


class ConvertorPng2Webp(ConversionOperationBase):
    def execute(self):
        logging.info(f"Converting PNG → WEBP: {self.input}")

        image = Image.open(self.input)
        image.save(self.output, "WEBP")

        logging.info(f"Conversion completed. WEBP saved to {self.output}")

# class ConvertorTxt2BboxJson(ConversionOperationBase):
#     def parse_result_txt(self):
#         with open(self.input, "r") as file:
#             lines = file.readlines()
#
#         if not os.path.exists(self.input):
#             raise FileNotFoundError(f"{self.input} not found.")
#
#         # Skip the header
#         rows = lines[1:]
#
#         results = []
#         for i in range(len(rows)):
#             image_path, bboxes_str = rows[i].split(",", 1)
#             image = cv2.imread(image_path)
#             width, height = image.shape[1], image.shape[0]
#             image_name = os.path.basename(image_path.strip())
#
#             # Convert the bounding boxes string to a Python list
#             bboxes = eval(bboxes_str.strip())
#
#             bboxes = "{ '" + image_name +"': " + bboxes + '}'
#             bboxes = bboxes.replace("'", '"')
#
#             bboxes = json.loads(bboxes)
#
#             detections = []
#             for bbox in bboxes:
#                 for elems in bboxes[bbox]:
#                     if elems["score"] > CONFIDENCE_THRESHOLD:
#                         detections.append({
#                             "label_name": elems["class"],
#                             "bbox_x": elems["bbox"][0],
#                             "bbox_y": elems["bbox"][1],
#                             "bbox_width": elems["bbox"][2] - elems["bbox"][0],
#                             "bbox_height": elems["bbox"][3] - elems["bbox"][1],
#                             #"image_name": image_name,
#                             "image_width": width,
#                             "image_height": height,
#                         })
#
#             results.append({
#                 image_name[:-4]: detections
#             })
#
#         return results[0]
#
#
#     def execute(self):
#
#         results_json = self.parse_result_txt()
#         if not results_json:
#             logging.warning("No valid detections found. Output JSON will be empty.")
#         with open(self.output, "w") as output_file:
#             json.dump(results_json, output_file, indent=4)
#         logging.info(f"Conversion completed. Output saved to {self.output}")