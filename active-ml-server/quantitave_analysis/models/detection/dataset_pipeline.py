import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from quantitave_analysis.utils.file_converter import ConvertorBboxJson2Csv
from quantitave_analysis.models.config import Config  

PROCESSED_FOLDER = Config().PROCESSED_FOLDER
UPLOAD_FOLDER = Config().UPLOAD_FOLDER
DEFAULT_CREATE_DATASET_RATIO = Config().DEFAULT_CREATE_DATASET_RATIO
from quantitave_analysis.augmentations.detection_augmentations import DetectionAugmentationProcessor # flip, scale, rotate, adjust_brightness, fix_bbox

import csv
import json
import random
import cv2
import logging
from pathlib import Path
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DetectionDatasetPipeline:

    def __init__(self, train_ratio: float = DEFAULT_CREATE_DATASET_RATIO):
        self.train_ratio = train_ratio

    def create_coco_dataset(self, input_folder: str, output_folder: str) -> None:
        logging.info("Starting detection dataset preparation...")
        input_path = Path(input_folder)
        output_path = Path(output_folder)
        images_folder = output_path / "images"
        images_folder.mkdir(parents=True, exist_ok=True)

        json_files = [f for f in os.listdir(input_path) if f.endswith('.json')]
        if not json_files:
            logging.warning("No JSON files found in input directory.")
            return
        logging.info(f"Found {len(json_files)} original JSON files")
        for json_file in json_files:
            converter = ConvertorBboxJson2Csv(input_path / json_file, input_folder)
            converter.execute()

        csv_files = [f for f in os.listdir(input_path) if f.endswith('.csv')]
        if not csv_files:
            logging.warning("No CSV files found in input directory.")
            return
        images_data = {}
        for csv_file in csv_files:
            with (input_path / csv_file).open('r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    image_name = row["image_name"]
                    if image_name not in images_data:
                        images_data[image_name] = {
                            "bboxes": [],
                            "label_names": [],
                            "image_width": int(row["image_width"]),
                            "image_height": int(row["image_height"])
                        }
                    images_data[image_name]["bboxes"].append({
                        "bbox_x": int(float(row["bbox_x"])),
                        "bbox_y": int(float(row["bbox_y"])),
                        "bbox_width": int(float(row["bbox_width"])),
                        "bbox_height": int(float(row["bbox_height"]))
                    })
                    images_data[image_name]["label_names"].append(row["label_name"])
        
        logging.info(f"Found {len(images_data)} original images")

        all_images_pool = []
        processor = DetectionAugmentationProcessor()
        augmentation_funcs = {
            "original": lambda img, bbs, w, h: (img, bbs),
            "scale": lambda img, bbs, w, h: processor.scale(img, bbs),
            "flip_hor": lambda img, bbs, w, h: processor.flip(img, bbs, 1, w, h),
            "flip_vert": lambda img, bbs, w, h: processor.flip(img, bbs, 0, w, h),
            "flip_both": lambda img, bbs, w, h: processor.flip(img, bbs, -1, w, h),
            "rotate_90": lambda img, bbs, w, h: processor.rotate(img, bbs, cv2.ROTATE_90_CLOCKWISE, w, h),
            "rotate_180": lambda img, bbs, w, h: processor.rotate(img, bbs, cv2.ROTATE_180, w, h),
            "rotate_270": lambda img, bbs, w, h: processor.rotate(img, bbs, cv2.ROTATE_90_COUNTERCLOCKWISE, w, h),
            "bright": lambda img, bbs, w, h: processor.adjust_brightness(img, bbs)
        }

        for image_name, img_info in images_data.items():
            image_path = Path(UPLOAD_FOLDER) / (image_name + '.png')
            if not image_path.exists():
                logging.warning(f"Image {image_path.name} not found!")
                continue

            image = cv2.imread(str(image_path))
            original_bboxes = img_info["bboxes"]
            label_names = img_info["label_names"]
            image_width, image_height = img_info["image_width"], img_info["image_height"]

            for aug_name, aug_func in augmentation_funcs.items():
                aug_image, aug_bboxes = aug_func(image, original_bboxes, image_width, image_height)
                aug_filename = f"{aug_name}_{image_path.stem}.png" if aug_name != "original" else image_path.name
                aug_image_path = images_folder / aug_filename
                cv2.imwrite(str(aug_image_path), aug_image)
                #logging.info(f"Saved augmented image: {aug_image_path}")

                all_images_pool.append({
                    "image_name": aug_filename,
                    "width": aug_image.shape[1],
                    "height": aug_image.shape[0],
                    "bboxes": aug_bboxes,
                    "label_names": label_names
                })

        random.shuffle(all_images_pool)
        train_size = int(self.train_ratio * len(all_images_pool))
        train_pool = all_images_pool[:train_size]
        test_pool = all_images_pool[train_size:]

        train_json = self._pool_to_coco(train_pool)
        test_json = self._pool_to_coco(test_pool)

        train_json_string = json.dumps(train_json, indent=4)
        train_json_string = train_json_string.replace("\n", "")
        train_json_string = train_json_string.replace(" ", "")
        
        annotations_folder = output_path / "Annotations"
        annotations_folder.mkdir(parents=True, exist_ok=True) 

        with (annotations_folder / "train.json").open('w') as f:
            #f.write(train_json_string)
            json.dump(train_json, f, indent=4)
        with (annotations_folder / "test.json").open('w') as f:
            json.dump(test_json, f, indent=4)
        
        logging.info(f"Dataset completed: {len(train_json['images'])} augmented images in train.json, "
                    f"{len(test_json['images'])} augmented images in test.json")
    
    def _pool_to_coco(self, pool: List[Dict]) -> Dict:
        coco_data = {
            "images": [],
            "annotations": [],
            "categories": []
        }
        
        categories = {}
        for item in pool:
            for label_name in item["label_names"]:
                if label_name not in categories:
                    category_id = len(categories) + 1
                    categories[label_name] = category_id
                    coco_data["categories"].append({
                        "id": category_id,
                        "name": label_name,
                        "supercategory": "Undefined" 
                    })

        image_id = 1
        annotation_id = 1
        processor = DetectionAugmentationProcessor()

        for item in pool:
            coco_data["images"].append({
                "id": image_id,
                "file_name": f"images/{item['image_name']}",
                "width": item["width"],
                "height": item["height"]
            })

            for i, bbox in enumerate(item["bboxes"]):
                fixed_bbox = processor.fix_bbox(bbox, item["width"], item["height"])
                category_id = categories[item["label_names"][i]]

                coco_data["annotations"].append({
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": category_id,
                    "bbox": fixed_bbox,
                    "area": fixed_bbox[2] * fixed_bbox[3],
                    "iscrowd": 0
                })
                annotation_id += 1
            image_id += 1

        return coco_data
    
if __name__ == "__main__":
    pipeline = DetectionDatasetPipeline()
    pipeline.create_coco_dataset(UPLOAD_FOLDER, PROCESSED_FOLDER)