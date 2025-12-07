import os
import json
import requests
import logging
from typing import Dict, List
from threading import Lock

from common.platform_to_task_converter.base import BasePlatformToTaskConverter, MAPPING_FILE, LABEL_PROPERTIES, COUNT_DOWNLOAD_FILES
from ML_server.config import Config
from common.platform_to_task_converter.base import (
    decode_filename,
    convert_webp_to_png,
    download_and_save_json,
    ensure_directory_exists,
    save_mapping_file,
    parallel_download
)

logger = logging.getLogger(__name__)


class SegmentationPlatformToTaskConverter(BasePlatformToTaskConverter):
    """Processor for segmentation data"""

    def __init__(self):
        self.record_files_map = {}
        self.record_files_lock = Lock()

    def _create_file_processor(self, upload_folder: str, url_to_record_map: Dict[str, str]):
        """
        Create a callback function for processing downloaded files

        Args:
            upload_folder: Directory to save files
            url_to_record_map: Mapping of URLs to record IDs

        Returns:
            Callback function
        """
        def process_file(url: str, img_response: requests.Response) -> bool:
            try:
                record_id = url_to_record_map.get(url)
                if not record_id:
                    logger.error(f"Could not find record_id for URL: {url}")
                    return False

                # Get and decode filename
                original_filename = url.split('/')[-1].split('?')[0]
                original_filename = decode_filename(original_filename)

                # Convert to PNG
                png_filename = convert_webp_to_png(img_response, original_filename, upload_folder)

                if png_filename:
                    # Thread-safe addition to record_files_map
                    with self.record_files_lock:
                        if record_id not in self.record_files_map:
                            self.record_files_map[record_id] = []
                        self.record_files_map[record_id].append(png_filename)
                    return True
                else:
                    logger.error(f"Failed to convert file {original_filename} for record {record_id}")
                    return False

            except Exception as e:
                logger.error(f"Unexpected error processing file from {url}: {e}")
                return False

        return process_file

    def _build_url_to_record_map(self, records: List[Dict]) -> tuple[Dict[str, str], List[str]]:
        """
        Build mapping of URLs to record IDs and collect all URLs

        Args:
            records: List of record dictionaries

        Returns:
            Tuple of (url_to_record_map, all_urls)
        """
        url_to_record_map = {}
        all_urls = []

        try:
            for record in records:
                for record_id, urls in record.items():
                    for url in urls:
                        url_to_record_map[url] = record_id
                        all_urls.append(url)

            return url_to_record_map, all_urls

        except Exception as e:
            logger.error(f"Error building URL to record map: {e}")
            return {}, []

    def run(self, package_url: str, label_properties_url: str, upload_folder: str) -> bool:
        """
        Download and process segmentation data

        Args:
            package_url: URL to download the package data
            label_properties_url: URL to download the label properties json
            upload_folder: Directory to store the processed data

        Returns:
            bool: True if processing was successful, False otherwise
        """
        # Reset record_files_map for each run
        self.record_files_map = {}

        # Ensure upload folder exists
        if not ensure_directory_exists(upload_folder):
            return False

        # Download and save label properties
        label_properties_path = os.path.join(upload_folder, LABEL_PROPERTIES)
        if not download_and_save_json(label_properties_url, label_properties_path, Config().authorization()):
            logger.error("Failed to download label properties")
            return False

        # Download package data
        try:
            logger.info("Downloading package data...")
            response = requests.get(package_url, headers=Config().authorization(), verify=False)
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading package data from {package_url}: {e}")
            return False

        # Parse package data
        try:
            data = response.json()

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding package data JSON: {e}")
            return False

        # Validate data structure
        try:
            if 'records' not in data:
                logger.error("Missing 'records' key in package data")
                return False

            # Build URL to record mapping and collect all URLs
            url_to_record_map, all_urls = self._build_url_to_record_map(data['records'])

            if not all_urls:
                logger.error("No URLs found in package data")
                return False

            logger.info(f"Starting parallel download of {len(all_urls)} files...")

            # Create file processor callback
            file_processor = self._create_file_processor(upload_folder, url_to_record_map)

            # Download and process all files in parallel
            successful, failed = parallel_download(
                urls=all_urls,
                process_callback=file_processor,
                max_workers=COUNT_DOWNLOAD_FILES
            )

            logger.info(f"Downloaded {successful} files successfully, {failed} failed")

            if not self.record_files_map:
                logger.error("No records were successfully processed")
                return False

            # Log warnings for records with no files
            for record in data['records']:
                for record_id in record.keys():
                    if record_id not in self.record_files_map or not self.record_files_map[record_id]:
                        logger.warning(f"No files were successfully processed for record {record_id}")

        except Exception as e:
            logger.error(f"Error processing package data: {e}")
            return False

        # Save mapping file
        mapping_file_path = os.path.join(upload_folder, MAPPING_FILE)
        if not save_mapping_file(self.record_files_map, mapping_file_path):
            logger.error("Failed to save mapping file")
            return False

        logger.info(f"Successfully processed {len(self.record_files_map)} records")
        return True
