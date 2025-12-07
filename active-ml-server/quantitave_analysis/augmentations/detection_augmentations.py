import random
import cv2
import logging
from typing import List, Dict, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DetectionAugmentationProcessor:

    @staticmethod
    def scale(image: np.ndarray, bboxes: List[Dict], scale_range: Tuple[float, float] = (0.95, 1.05)) -> Tuple[np.ndarray, List[Dict]]:
        scale_factor = random.uniform(*scale_range)
        new_width = int(image.shape[1] * scale_factor)
        new_height = int(image.shape[0] * scale_factor)
        scaled_image = cv2.resize(image, (new_width, new_height))
        scaled_bboxes = [
            {
                **bbox,
                "bbox_x": int(bbox["bbox_x"] * scale_factor),
                "bbox_y": int(bbox["bbox_y"] * scale_factor),
                "bbox_width": int(bbox["bbox_width"] * scale_factor),
                "bbox_height": int(bbox["bbox_height"] * scale_factor)
            }
            for bbox in bboxes
        ]
        #logging.info(f"Scaled image by factor {scale_factor}. New dimensions: {new_width}x{new_height}")
        return scaled_image, scaled_bboxes

    @staticmethod
    def flip(image: np.ndarray, bboxes: List[Dict], flip_code: int, image_width: int, image_height: int) -> Tuple[np.ndarray, List[Dict]]:
        flip_types = {0: "vertical", 1: "horizontal", -1: "both"}
        flipped_image = cv2.flip(image, flip_code)
        flipped_bboxes = []
        for bbox in bboxes:
            new_bbox = {**bbox}
            if flip_code in (1, -1):  # Horizontal flip
                new_bbox["bbox_x"] = image_width - bbox["bbox_x"] - bbox["bbox_width"]
            if flip_code in (0, -1):  # Vertical flip
                new_bbox["bbox_y"] = image_height - bbox["bbox_y"] - bbox["bbox_height"]
            flipped_bboxes.append(new_bbox)
        #logging.info(f"Applied {flip_types[flip_code]} flip to image")
        return flipped_image, flipped_bboxes

    @staticmethod
    def rotate(image: np.ndarray, bboxes: List[Dict], angle: int, image_width: int, image_height: int) -> Tuple[np.ndarray, List[Dict]]:
        angle_map = {
            cv2.ROTATE_90_CLOCKWISE: 90,
            cv2.ROTATE_180: 180,
            cv2.ROTATE_90_COUNTERCLOCKWISE: 270
        }
        rotated_image = cv2.rotate(image, angle)
        new_width, new_height = (image_height, image_width) if angle in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE) else (image_width, image_height)
        rotated_bboxes = []
        for bbox in bboxes:
            x, y, w, h = bbox["bbox_x"], bbox["bbox_y"], bbox["bbox_width"], bbox["bbox_height"]
            if angle == cv2.ROTATE_90_CLOCKWISE:
                new_bbox = {"bbox_x": y, "bbox_y": image_width - x - w, "bbox_width": h, "bbox_height": w}
            elif angle == cv2.ROTATE_180:
                new_bbox = {"bbox_x": image_width - x - w, "bbox_y": image_height - y - h, "bbox_width": w, "bbox_height": h}
            elif angle == cv2.ROTATE_90_COUNTERCLOCKWISE:
                new_bbox = {"bbox_x": image_height - y - h, "bbox_y": x, "bbox_width": h, "bbox_height": w}
            rotated_bboxes.append(new_bbox)
        #logging.info(f"Rotated image by {angle_map[angle]} degrees")
        return rotated_image, rotated_bboxes

    @staticmethod
    def adjust_brightness(image: np.ndarray, bboxes: List[Dict], factor: float = 1.5) -> Tuple[np.ndarray, List[Dict]]:
        bright_image = cv2.convertScaleAbs(image, alpha=factor, beta=0)
        #logging.info(f"Adjusted brightness by factor {factor}")
        return bright_image, bboxes.copy()

    @staticmethod
    def fix_bbox(bbox: Dict, image_width: int, image_height: int) -> List[int]:
        x = max(0, min(bbox["bbox_x"], image_width - 1))
        y = max(0, min(bbox["bbox_y"], image_height - 1))
        w = max(1, min(bbox["bbox_width"], image_width - x))
        h = max(1, min(bbox["bbox_height"], image_height - y))
        return [x, y, w, h]