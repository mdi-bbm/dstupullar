import os
import json
import logging
import cv2

from quantitave_analysis.utils.temporary_storage import DataHandler
from quantitave_analysis.models.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIDENCE_THRESHOLD = Config().CONFIDENCE_THRESHOLD
INTERSECTION_THRESHOLD = Config().INTERSECTION_THRESHOLD  # Configurable IoU threshold


class Rectangle:
    def __init__(self, x, y, width, height, score, detection):
        self.x = x  # The x-coordinate of the top left corner
        self.y = y  # The y-coordinate of the top left corner
        self.width = width
        self.height = height
        self.score = score  # Score for choosing when intersecting
        self.detection = detection  # Full detection data

    def area(self):
        """Calculates the area of a rectangle"""
        return self.width * self.height

def get_intersection_area(rect1, rect2):
    """Calculates the area of intersection of two rectangles"""
    x_left = max(rect1.x, rect2.x)
    x_right = min(rect1.x + rect1.width, rect2.x + rect2.width)
    y_top = max(rect1.y, rect2.y)
    y_bottom = min(rect1.y + rect1.height, rect2.y + rect2.height)
    
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    
    return (x_right - x_left) * (y_bottom - y_top)

def get_iou(rect1, rect2):
    """Calculates the IoU (Intersection over Union) of two rectangles"""
    intersection_area = get_intersection_area(rect1, rect2)
    if intersection_area == 0:
        return 0.0
    union_area = rect1.area() + rect2.area() - intersection_area
    iou = intersection_area / union_area
    # logging.info(f"Calculated IoU: {iou} for rectangles at ({rect1.x}, {rect1.y}) and ({rect2.x}, {rect2.y})")
    return iou

def is_touching_or_contained(rect1, rect2):
    """Checks if the rectangles touch each other or if one is inside the other"""
    # Boundary coordinates
    r1_left, r1_right = rect1.x, rect1.x + rect1.width
    r1_top, r1_bottom = rect1.y, rect1.y + rect1.height
    r2_left, r2_right = rect2.x, rect2.x + rect2.width
    r2_top, r2_bottom = rect2.y, rect2.y + rect2.height

    contained = (
        (r1_left >= r2_left and r1_right <= r2_right and r1_top >= r2_top and r1_bottom <= r2_bottom) or
        (r2_left >= r1_left and r2_right <= r1_right and r2_top >= r1_top and r2_bottom <= r1_bottom)
    )
    # Checking the nesting
    # Checking the intersection using IoU
    iou = get_iou(rect1, rect2)
    # logging.info(f"Using INTERSECTION_THRESHOLD: {INTERSECTION_THRESHOLD}")
    intersection = iou > INTERSECTION_THRESHOLD

    return contained or intersection

def filter_overlapping_rectangles(rectangles):
    """Filters overlapping rectangles, keeping the one with the highest score"""
    if not rectangles:
        return []
    
    # logging.info(f"Starting with {len(rectangles)} rectangles")
    # Sort by score in descending order
    rectangles.sort(key=lambda r: r.score, reverse=True)
    keep = []
    
    while rectangles:
        # Take the rectangle with the highest score
        current = rectangles.pop(0)
        keep.append(current.detection)
        # logging.info(f"Keeping rectangle at ({current.x}, {current.y}) with score {current.score}")
        
        # Get rid of all the rectangles that overlap with the current one.
        remaining = []
        for rect in rectangles:
            if not is_touching_or_contained(current, rect):
                remaining.append(rect)
            # else:
            #     logging.info(f"Removing rectangle at ({rect.x}, {rect.y}) due to overlap")
        
        rectangles = remaining
    
    # logging.info(f"Kept {len(keep)} rectangles after filtering")
    return keep

class ResultProcessor:
    @staticmethod
    def process_single_result(txt_path: str, model_dir) -> dict:
        # Open and read the result.txt file
        with open(txt_path, "r") as file:
            lines = file.readlines()

        # Skip the header
        rows = lines[1:]

        # Uploading the reverse mapping
        reverse_class_mapping = ResultProcessor.load_reverse_class_mapping(model_dir)

        results = []
        for i in range(len(rows)):
            image_path, bboxes_str = rows[i].split(",", 1)
            image = cv2.imread(image_path)
            width, height = image.shape[1], image.shape[0]
            image_name = os.path.basename(image_path.strip())

            # Convert the bounding boxes string to a Python list
            bboxes = eval(bboxes_str.strip())
            bboxes = "{ '" + image_name + "': " + bboxes + '}'
            bboxes = bboxes.replace("'", '"')
            bboxes = json.loads(bboxes)

            detections = []
            rectangles = []
            for bbox in bboxes:
                for elems in bboxes[bbox]:
                    label = elems["class"]
                    real_label = reverse_class_mapping.get(label, label)
                    
                    detection = {
                        "label_name": real_label,
                        "bbox_x": elems["bbox"][0],
                        "bbox_y": elems["bbox"][1],
                        "bbox_width": elems["bbox"][2] - elems["bbox"][0],
                        "bbox_height": elems["bbox"][3] - elems["bbox"][1],
                        "image_name": image_name,
                        "image_width": width,
                        "image_height": height,
                        "score": elems["score"]
                    }
                    
                    if elems["score"] > CONFIDENCE_THRESHOLD:
                        detections.append(detection)
                        # Creating a Rectangle object to check for intersections
                        rectangles.append(Rectangle(
                            x=elems["bbox"][0],
                            y=elems["bbox"][1],
                            width=elems["bbox"][2] - elems["bbox"][0],
                            height=elems["bbox"][3] - elems["bbox"][1],
                            score=elems["score"],
                            detection=detection
                        ))

            # Filtering overlapping rectangles
            filtered_detections = filter_overlapping_rectangles(rectangles)

            results.append({
                image_name[:-4]: filtered_detections
            })
        return results[0]

    @staticmethod
    def load_reverse_class_mapping(model_dir):
        mapping_path = os.path.join(model_dir, "class_mapping.json")
        if os.path.exists(mapping_path):
            with open(mapping_path, 'r') as f:
                mappings = json.load(f)
                return mappings["reverse"]
        logging.warning(f"Class mapping not found at {mapping_path}")
        return {}

    @staticmethod
    def process_combined_results(model_dir) -> str:
        """Process result.txt and create one combined JSON file."""
        project_folder = os.path.abspath(os.path.join(Config().storage_root, '../'))
        base_path = os.path.join(project_folder, "AutogluonModels")
        
        latest_txt_file = DataHandler.get_latest_result_txt(base_path)
        logging.info(f"Latest result.txt folder: {latest_txt_file}")

        result_txt_path = os.path.join(latest_txt_file, "result.txt")

        if os.path.exists(result_txt_path):
            results_json = ResultProcessor.process_single_result(result_txt_path, model_dir)
            results_json_str = json.dumps(results_json)
            results_json_str = results_json_str[1:-1]  # Remove starting and ending {}
        else:
            raise FileNotFoundError("result.txt not found in the latest model folder.")
        return results_json_str