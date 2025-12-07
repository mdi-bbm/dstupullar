import os
import logging
import json
from typing import Dict, List, Tuple, Optional

from common.results_to_platform_converter.base import BaseResultsToPlatformConverter, RESULTS_JSON, MAPPING_FILE
from ML_server.config import Config
from common.results_to_platform_converter.base import (
    load_mapping_file,
    load_json_file,
    save_json_file,
    upload_files_to_platform,
    close_opened_files,
    create_filename_to_record_map
)

logger = logging.getLogger(__name__)


class DetectionResultsToPlatformConverter(BaseResultsToPlatformConverter):
    """Post-processor for detection results"""

    def __init__(self, batch_size: int = 100):
        """
        Initialize converter with batch size for file uploads

        Args:
            batch_size: Number of files to upload in each batch
        """
        self.batch_size = batch_size

    def _process_detection_results(self, output_data: Dict, filename_to_record: Dict[str, str],
                                   return_folder: str) -> List[Tuple[str, str, str]]:
        """
        Process detection results and create file info for upload

        Args:
            output_data: Detection results data
            filename_to_record: Mapping from filename to record ID
            return_folder: Directory to save temporary files

        Returns:
            List of tuples (record_id, json_filename, temp_json_path)
        """
        file_info = []

        for image_name, detections in output_data.items():
            try:
                base_image_name = image_name.split('_bbox')[0] + '.png'

                if base_image_name not in filename_to_record:
                    logger.warning(f"No record found for image: {base_image_name}")
                    continue

                record_id = filename_to_record[base_image_name]

                # Create individual JSON for this detection
                individual_json = {
                    image_name.split('_bbox')[0]: detections
                }

                json_filename = f"{image_name.split('_bbox')[0]}_bbox.json"
                temp_json_path = os.path.join(return_folder, json_filename)

                # Save temporary JSON file
                if not save_json_file(individual_json, temp_json_path):
                    logger.error(f"Failed to save detection JSON for {image_name}")
                    continue

                file_info.append((record_id, json_filename, temp_json_path))

            except Exception as e:
                logger.error(f"Error processing detection result for {image_name}: {e}")
                continue

        return file_info

    def _upload_file_batch(self, file_batch: List[Tuple[str, str, str]],
                          result_upload_url: str, task_mode: str, package_id: int) -> bool:
        """
        Upload a batch of files to the platform

        Args:
            file_batch: List of tuples (record_id, json_filename, temp_json_path)
            result_upload_url: URL to upload the results
            task_mode: Task mode identifier
            package_id: Package ID

        Returns:
            bool: True if upload was successful, False otherwise
        """
        files = []
        opened_files = []

        try:
            # Open files for this batch
            for record_id, json_filename, temp_json_path in file_batch:
                try:
                    if not os.path.exists(temp_json_path):
                        logger.error(f"File not found: {temp_json_path}")
                        continue

                    json_file = open(temp_json_path, 'rb')
                    opened_files.append(json_file)
                    files.append((record_id, (json_filename, json_file, 'application/json')))

                except IOError as e:
                    logger.error(f"Error opening JSON file {temp_json_path}: {e}")
                    continue

            if not files:
                logger.warning("No files to upload in this batch")
                return True

            # Upload files
            upload_success = upload_files_to_platform(
                files,
                result_upload_url,
                task_mode,
                package_id,
                Config().authorization()
            )

            if not upload_success:
                logger.error(f"Failed to upload batch of {len(files)} files")
                return False

            logger.info(f"Successfully uploaded batch of {len(files)} files")
            return True

        except Exception as e:
            logger.error(f"Error during batch upload: {e}")
            return False

        finally:
            # Always close opened files
            close_opened_files(opened_files)

    def _upload_files_in_batches(self, file_info: List[Tuple[str, str, str]],
                                 result_upload_url: str, task_mode: str, package_id: int) -> bool:
        """
        Upload files in batches

        Args:
            file_info: List of tuples (record_id, json_filename, temp_json_path)
            result_upload_url: URL to upload the results
            task_mode: Task mode identifier
            package_id: Package ID

        Returns:
            bool: True if all uploads were successful, False otherwise
        """
        total_files = len(file_info)
        logger.info(f"Starting batch upload of {total_files} files in batches of {self.batch_size}")

        # Process files in batches
        for i in range(0, total_files, self.batch_size):
            batch_end = min(i + self.batch_size, total_files)
            file_batch = file_info[i:batch_end]

            batch_num = (i // self.batch_size) + 1
            total_batches = (total_files + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(file_batch)} files)")

            if not self._upload_file_batch(file_batch, result_upload_url, task_mode, package_id):
                logger.error(f"Failed to upload batch {batch_num}")
                return False

        logger.info(f"Successfully completed batch upload of all {total_files} files")
        return True

    def _load_detection_results(self, return_folder: str) -> Optional[Dict]:
        """
        Load detection results from JSON file

        Args:
            return_folder: Directory containing results

        Returns:
            Detection results data or None if not found/invalid
        """
        json_path = os.path.join(return_folder, RESULTS_JSON)

        if not os.path.exists(json_path):
            logger.warning(f"Results JSON file not found: {json_path}")
            return None

        return load_json_file(json_path)

    def run(self, return_folder: str, upload_folder: str, result_upload_url: str, package_id: int) -> bool:
        """
        Process and upload detection results

        Args:
            return_folder: Directory containing the results
            upload_folder: Directory containing the input data
            result_upload_url: URL to upload the results
            package_id: Package ID

        Returns:
            bool: True if processing was successful, False otherwise
        """
        # Load mapping file
        mapping_file_path = os.path.join(upload_folder, MAPPING_FILE)
        record_files_map = load_mapping_file(mapping_file_path)

        if record_files_map is None:
            logger.error("Failed to load mapping file")
            return False

        # Create filename to record mapping
        filename_to_record = create_filename_to_record_map(record_files_map)
        if not filename_to_record:
            logger.error("Failed to create filename to record mapping")
            return False

        # Load detection results
        output_data = self._load_detection_results(return_folder)
        if output_data is None:
            logger.error("Failed to load detection results")
            return False

        # Process detection results
        file_info = self._process_detection_results(
            output_data, filename_to_record, return_folder
        )

        if not file_info:
            logger.warning("No files to upload")
            return True

        # Upload files to platform
        task_mode = "Detection"  # Extract from task package in real implementation

        upload_success = self._upload_files_in_batches(
            file_info,
            result_upload_url,
            task_mode,
            package_id
        )

        if not upload_success:
            logger.error("Failed to upload detection results")
            return False

        logger.info(f"Successfully uploaded {len(file_info)} detection result files")
        return True