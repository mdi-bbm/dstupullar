from abc import ABC, abstractmethod
import os
import json
import requests
from PIL import Image
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

RESULTS_JSON = 'output.json'
MAPPING_FILE = 'record_files_mapping.json'


def load_mapping_file(mapping_file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load mapping file from JSON

    Args:
        mapping_file_path: Path to the mapping file

    Returns:
        Mapping dictionary if successful, None otherwise
    """
    try:
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Mapping file not found: {mapping_file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding mapping file JSON: {e}")
        return None
    except IOError as e:
        logger.error(f"Error reading mapping file: {e}")
        return None


def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON file

    Args:
        file_path: Path to the JSON file

    Returns:
        JSON data if successful, None otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"JSON file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON file: {e}")
        return None
    except IOError as e:
        logger.error(f"Error reading JSON file: {e}")
        return None


def save_json_file(data: Dict[str, Any], file_path: str) -> bool:
    """
    Save data to JSON file

    Args:
        data: Data to save
        file_path: Path to save the file

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        logger.error(f"Error saving JSON file {file_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving JSON file: {e}")
        return False


def convert_png_to_webp(png_path: str, webp_path: str, quality: int = 90) -> bool:
    """
    Convert PNG image to WebP format

    Args:
        png_path: Path to input PNG file
        webp_path: Path to output WebP file
        quality: WebP quality (0-100)

    Returns:
        True if conversion successful, False otherwise
    """
    try:
        if not os.path.exists(png_path):
            logger.error(f"PNG file not found: {png_path}")
            return False

        with Image.open(png_path) as image:
            image.save(webp_path, 'WEBP', quality=quality)
        return True

    except IOError as e:
        logger.error(f"Error converting PNG to WebP: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during PNG to WebP conversion: {e}")
        return False


def upload_files_to_platform(files: List[Tuple], upload_url: str, task_mode: str,
                             package_id: int, headers: Dict[str, str]) -> bool:
    """
    Upload files to platform

    Args:
        files: List of file tuples for upload
        upload_url: URL to upload files to
        task_mode: Task mode identifier
        package_id: Package ID
        headers: Request headers

    Returns:
        True if upload successful, False otherwise
    """
    if not files:
        logger.warning("No files to upload")
        return True

    try:
        response = requests.post(
            upload_url,
            files=files,
            data={'mode': task_mode, 'package_id': package_id},
            headers=headers,
            verify=False
        )

        if response.status_code != 200:
            logger.error(f"Failed to upload results: HTTP {response.status_code}")
            return False

        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Error uploading files to platform: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        return False


def close_opened_files(opened_files: List) -> None:
    """
    Close all opened file handles

    Args:
        opened_files: List of file handles to close
    """
    for file_handle in opened_files:
        try:
            if hasattr(file_handle, 'close'):
                file_handle.close()
        except Exception as e:
            logger.warning(f"Error closing file handle: {e}")


def create_filename_to_record_map(record_files_map: Dict[str, str]) -> Dict[str, str]:
    """
    Create reverse mapping from filename to record ID

    Args:
        record_files_map: Mapping from record ID to filename

    Returns:
        Mapping from filename to record ID
    """
    try:
        return {v: k for k, v in record_files_map.items()}
    except Exception as e:
        logger.error(f"Error creating filename to record map: {e}")
        return {}

class BaseResultsToPlatformConverter(ABC):
    """Base class for handling post-processing of results"""

    @abstractmethod
    def run(self, return_folder: str, upload_folder: str, result_upload_url: str, package_id: int) -> bool:
        """
        Process results and upload them to the platform

        Args:
            return_folder: Directory containing the results
            upload_folder: Directory containing the input data
            result_upload_url: URL to upload the results
            package_id: Package ID

        Returns:
            bool: True if processing was successful, False otherwise
        """
        pass

