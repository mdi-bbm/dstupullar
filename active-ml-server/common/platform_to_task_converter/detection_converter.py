import os
import json
import requests
import logging
from typing import Dict, List, Optional
from threading import Lock

from common.platform_to_task_converter.base import BasePlatformToTaskConverter, MERGED_JSON, MAPPING_FILE, COUNT_DOWNLOAD_FILES
from ML_server.config import Config
from common.platform_to_task_converter.base import (
    decode_filename,
    convert_webp_to_png,
    ensure_directory_exists,
    save_mapping_file,
    save_json_data,
    parallel_download
)

logger = logging.getLogger(__name__)


class DetectionPlatformToTaskConverter(BasePlatformToTaskConverter):
    """Processor for detection data"""

    def __init__(self):
        self.merged_json = {}
        self.merged_json_lock = Lock()

    def _find_webp_file(self, urls: List[str]) -> Optional[str]:
        """
        Find webp file in URLs and return corresponding PNG filename

        Args:
            urls: List of URLs to search

        Returns:
            PNG filename if webp found, None otherwise
        """
        try:
            for url in urls:
                if '.webp' in url:
                    original_filename = url.split('/')[-1].split('?')[0]
                    png_filename = os.path.splitext(original_filename)[0] + '.png'
                    return png_filename
            return None
        except Exception as e:
            logger.error(f"Error finding webp file: {e}")
            return None

    def _process_json_file(self, file_response: requests.Response, filename: str) -> bool:
        """
        Process JSON file and add to merged_json (thread-safe)

        Args:
            file_response: Response object containing JSON file
            filename: Name of the JSON file

        Returns:
            True if processing successful, False otherwise
        """
        try:
            json_content = file_response.json()
            image_name = os.path.splitext(filename)[0]

            if image_name.endswith('_bbox'):
                image_name = image_name[:-5]

            with self.merged_json_lock:
                self.merged_json[image_name] = json_content.get(image_name, {})

            return True

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON file {filename}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error processing JSON file {filename}: {e}")
            return False

    def _build_record_files_map(self, records: List[Dict]) -> Dict[str, str]:
        """
        Build mapping of record IDs to PNG filenames

        Args:
            records: List of record dictionaries

        Returns:
            Dictionary mapping record IDs to filenames
        """
        record_files_map = {}

        try:
            for record in records:
                for record_id, urls in record.items():
                    png_filename = self._find_webp_file(urls)
                    png_filename = decode_filename(png_filename)
                    if png_filename:
                        record_files_map[record_id] = png_filename
            return record_files_map

        except Exception as e:
            logger.error(f"Error building record files map: {e}")
            return {}

    def _create_file_processor(self, upload_folder: str):
        """
        Create a callback function for processing downloaded files

        Args:
            upload_folder: Directory to save files

        Returns:
            Callback function
        """

        def process_file(url: str, file_response: requests.Response) -> bool:
            try:
                # Get and decode filename
                filename = url.split('/')[-1].split('?')[0]
                filename = decode_filename(filename)

                # Process based on file type
                if filename.endswith('.webp'):
                    png_filename = convert_webp_to_png(file_response, filename, upload_folder)
                    return png_filename is not None

                elif filename.endswith('.json'):
                    return self._process_json_file(file_response, filename)

                return True

            except Exception as e:
                logger.error(f"Unexpected error processing file from {url}: {e}")
                return False

        return process_file

    def _collect_all_urls(self, records: List[Dict]) -> List[str]:
        """
        Collect all URLs from records

        Args:
            records: List of record dictionaries

        Returns:
            List of all URLs
        """
        all_urls = []
        for record in records:
            for record_id, urls in record.items():
                all_urls.extend(urls)
        return all_urls

    def run(self, package_url: str, label_properties_url: str, upload_folder: str) -> bool:
        """
        Download and process detection data

        Args:
            package_url: URL to download the package data
            label_properties_url: URL to download the label properties json
            upload_folder: Directory to store the processed data

        Returns:
            bool: True if processing was successful, False otherwise
        """
        # Reset merged_json for each run
        self.merged_json = {}

        # Ensure upload folder exists
        if not ensure_directory_exists(upload_folder):
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

            # Build record files mapping
            record_files_map = self._build_record_files_map(data['records'])

            # Collect all URLs for parallel download
            all_urls = self._collect_all_urls(data['records'])

            logger.info(f"Starting parallel download of {len(all_urls)} files...")

            # Create file processor callback
            file_processor = self._create_file_processor(upload_folder)

            # Download and process all files in parallel
            successful, failed = parallel_download(
                urls=all_urls,
                process_callback=file_processor,
                max_workers=COUNT_DOWNLOAD_FILES
            )

            logger.info(f"Downloaded {successful} files successfully, {failed} failed")

            # Save results
            merged_json_path = os.path.join(upload_folder, MERGED_JSON)
            json_success = save_json_data(merged_json_path, self.merged_json)

            mapping_file_path = os.path.join(upload_folder, MAPPING_FILE)
            mapping_success = save_mapping_file(record_files_map, mapping_file_path)

            # Consider successful if most files downloaded and mappings saved
            return json_success and mapping_success and (failed == 0 or successful > 0)

        except Exception as e:
            logger.error(f"Unexpected error in detection processing: {e}")
            return False
