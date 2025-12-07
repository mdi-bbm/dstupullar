import os
import logging
from typing import Dict, List, Tuple

from common.results_to_platform_converter.base import BaseResultsToPlatformConverter, MAPPING_FILE
from ML_server.config import Config
from common.results_to_platform_converter.base import (
    load_mapping_file,
    convert_png_to_webp,
    upload_files_to_platform,
    close_opened_files
)

logger = logging.getLogger(__name__)


class SegmentationResultsToPlatformConverter(BaseResultsToPlatformConverter):
    """Post-processor for segmentation results"""

    def __init__(self, batch_size: int = 10):
        """
        Initialize converter with batch size for file uploads

        Args:
            batch_size: Number of files to upload in each batch
        """
        self.batch_size = batch_size

    def _process_segmentation_masks(self, record_files_map: Dict[str, List[str]],
                                    return_folder: str) -> List[Tuple[str, str, str]]:
        """
        Process segmentation masks and prepare file info for upload

        Args:
            record_files_map: Mapping from record ID to list of filenames
            return_folder: Directory containing result files

        Returns:
            List of tuples (record_id, webp_filename, webp_mask_path)
        """
        file_info = []

        for record_id, filenames in record_files_map.items():
            for filename in filenames:
                try:
                    base_filename = os.path.splitext(filename)[0]
                    png_mask_path = os.path.join(return_folder, base_filename + '_mask.png')
                    webp_mask_path = os.path.join(return_folder, base_filename + '_mask.webp')

                    # Check if PNG mask exists
                    if not os.path.exists(png_mask_path):
                        logger.warning(f"PNG mask not found: {png_mask_path}")
                        continue

                    # Convert PNG to WebP
                    if not convert_png_to_webp(png_mask_path, webp_mask_path, quality=90):
                        logger.error(f"Failed to convert PNG to WebP for {base_filename}")
                        continue

                    # Remove original PNG file after successful conversion
                    try:
                        os.remove(png_mask_path)
                    except OSError as e:
                        logger.warning(f"Could not remove PNG file {png_mask_path}: {e}")

                    webp_filename = base_filename + '_mask.webp'
                    file_info.append((record_id, webp_filename, webp_mask_path))

                except Exception as e:
                    logger.error(f"Error processing mask for {filename} in record {record_id}: {e}")
                    continue

        return file_info

    def _upload_file_batch(self, file_batch: List[Tuple[str, str, str]],
                          result_upload_url: str, task_mode: str, package_id: int) -> bool:
        """
        Upload a batch of files to the platform

        Args:
            file_batch: List of tuples (record_id, webp_filename, webp_mask_path)
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
            for record_id, webp_filename, webp_mask_path in file_batch:
                try:
                    if not os.path.exists(webp_mask_path):
                        logger.error(f"WebP file not found: {webp_mask_path}")
                        continue

                    webp_file = open(webp_mask_path, 'rb')
                    opened_files.append(webp_file)
                    files.append((record_id, (webp_filename, webp_file, 'image/webp')))

                except IOError as e:
                    logger.error(f"Error opening WebP file {webp_mask_path}: {e}")
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

            logger.info(f"Successfully uploaded batch of {len(files)} segmentation files")
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
            file_info: List of tuples (record_id, webp_filename, webp_mask_path)
            result_upload_url: URL to upload the results
            task_mode: Task mode identifier
            package_id: Package ID

        Returns:
            bool: True if all uploads were successful, False otherwise
        """
        total_files = len(file_info)
        logger.info(f"Starting batch upload of {total_files} segmentation files in batches of {self.batch_size}")

        # Process files in batches
        for i in range(0, total_files, self.batch_size):
            batch_end = min(i + self.batch_size, total_files)
            file_batch = file_info[i:batch_end]

            batch_num = (i // self.batch_size) + 1
            total_batches = (total_files + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(file_batch)} segmentation files)")

            if not self._upload_file_batch(file_batch, result_upload_url, task_mode, package_id):
                logger.error(f"Failed to upload batch {batch_num}")
                return False

        logger.info(f"Successfully completed batch upload of all {total_files} segmentation files")
        return True

    def run(self, return_folder: str, upload_folder: str, result_upload_url: str, package_id: int) -> bool:
        """
        Process and upload segmentation results

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

        # Validate mapping structure for segmentation (should be dict with lists)
        try:
            for record_id, filenames in record_files_map.items():
                if not isinstance(filenames, list):
                    logger.error(f"Invalid mapping structure: expected list for record {record_id}")
                    return False
        except Exception as e:
            logger.error(f"Error validating mapping structure: {e}")
            return False

        # Process segmentation masks to get file info
        file_info = self._process_segmentation_masks(record_files_map, return_folder)

        if not file_info:
            logger.warning("No segmentation masks were processed successfully")
            return False

        # Upload files in batches
        task_mode = "Segmentation"  # Extract from task package in real implementation

        upload_success = self._upload_files_in_batches(
            file_info,
            result_upload_url,
            task_mode,
            package_id
        )

        if not upload_success:
            logger.error("Failed to upload segmentation results")
            return False

        logger.info(f"Successfully uploaded {len(file_info)} segmentation result files")
        return True
