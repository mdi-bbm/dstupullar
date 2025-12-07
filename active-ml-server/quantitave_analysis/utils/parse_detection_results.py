import os
import json
import cv2
from typing import Dict, Any

from quantitave_analysis.models.config import Config
CONFIDENCE_THRESHOLD = Config().CONFIDENCE_THRESHOLD
from quantitave_analysis.utils.temporary_storage import TemporaryStorageManager

def parse_result_txt(txt_path: str) -> Dict[str, Any]:
    with open(txt_path, "r") as file:
        lines = file.readlines()

    header = lines[0].strip()
    rows = lines[1:]

    results = []
    for i in range(len(rows)):
    #for row in rows:
        #image_path, bboxes_str = row.split(",", 1)
        image_path, bboxes_str = rows[i].split(",", 1)
        image = cv2.imread(image_path)
        width, height = image.shape[1], image.shape[0]
        image_name = os.path.basename(image_path.strip())

        bboxes = eval(bboxes_str.strip())

        bboxes = "{ '" + image_name +"': " + bboxes + '}'
        bboxes = bboxes.replace("'", '"')

        bboxes = json.loads(bboxes)

        detections = []
        for bbox in bboxes:
            for elems in bboxes[bbox]: 
                if elems["score"] > CONFIDENCE_THRESHOLD:
                    detections.append({
                        "label_name": elems["class"],
                        "bbox_x": elems["bbox"][0],
                        "bbox_y": elems["bbox"][1],
                        "bbox_width": elems["bbox"][2] - elems["bbox"][0],
                        "bbox_height": elems["bbox"][3] - elems["bbox"][1],
                        "image_name": image_name,
                        "image_width": width,
                        "image_height": height,
                    })

        results.append({
            image_name[:-4]: detections
        })

    return results[0]

def parse_results() -> str:
    latest_model_folder = TemporaryStorageManager().find_latest_dir("AutogluonModels")
    print(f"Latest model folder: {latest_model_folder}")

    result_txt_path = os.path.join(latest_model_folder, "result.txt")

    if os.path.exists(result_txt_path):
        results_json = parse_result_txt(result_txt_path)
        results_json_str = json.dumps(results_json)
        results_json_str = results_json_str[1:-1]  # Remove starting and ending {}
    else:
        raise FileNotFoundError("result.txt not found in the latest model folder.")
    return results_json_str

if __name__ == "__main__":
    parse_results()
