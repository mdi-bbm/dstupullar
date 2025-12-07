from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Tuple, Callable
import os
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import urllib.parse
from PIL import Image
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

MERGED_JSON = 'bbox.json'
MAPPING_FILE = 'record_files_mapping.json'
LABEL_PROPERTIES = 'label_properties.json'
COUNT_DOWNLOAD_FILES = 20  # Count of files for parallel download
MAX_RETRIES = 3  # Количество попыток повтора при ошибке

# Thread-local storage for sessions
_thread_local = threading.local()


def get_session() -> requests.Session:
    """
    Get or create a requests session for the current thread
    Uses connection pooling to reduce number of open files

    Returns:
        requests.Session configured with retry strategy
    """
    if not hasattr(_thread_local, 'session'):
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        _thread_local.session = session

    return _thread_local.session


def decode_filename(filename: str) -> str:
    """
    Decode filename if necessary (for Russian names, etc.)

    Args:
        filename: Original filename

    Returns:
        Decoded filename
    """
    try:
        decoded_filename = urllib.parse.unquote(filename)
        return decoded_filename if filename != decoded_filename else filename
    except Exception as e:
        logger.warning(f"Error decoding filename {filename}: {e}")
        return filename


def convert_webp_to_png(file_response: requests.Response, filename: str, upload_folder: str) -> Optional[str]:
    """
    Convert webp file to PNG format

    Args:
        file_response: Response object containing webp file
        filename: Name of the webp file
        upload_folder: Directory to save files

    Returns:
        PNG filename if conversion successful, None otherwise
    """
    webp_path = None
    try:
        webp_path = os.path.join(upload_folder, filename)
        png_filename = os.path.splitext(filename)[0] + '.png'
        png_path = os.path.join(upload_folder, png_filename)

        # Save webp file
        with open(webp_path, 'wb') as f:
            f.write(file_response.content)

        # Convert to PNG and explicitly close
        with Image.open(webp_path) as image:
            image.save(png_path, 'PNG')

        # Remove original webp file
        if webp_path and os.path.exists(webp_path):
            os.remove(webp_path)

        return png_filename

    except IOError as e:
        logger.error(f"Error with file operations during webp conversion: {e}")
        # Clean up on error
        if webp_path and os.path.exists(webp_path):
            try:
                os.remove(webp_path)
            except:
                pass
        return None
    except Exception as e:
        logger.error(f"Unexpected error during webp conversion: {e}")
        # Clean up on error
        if webp_path and os.path.exists(webp_path):
            try:
                os.remove(webp_path)
            except:
                pass
        return None


def save_json_data(filepath: str, json_data: Dict) -> bool:
    """
    Save merged JSON file

    Args:
        filepath: Path to save files
        json_data: JSON data

    Returns:
        True if saving successful, False otherwise
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        return True

    except IOError as e:
        logger.error(f"Error saving merged JSON file: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving merged JSON: {e}")
        return False


def download_and_save_json(url: str, filepath: str, headers: dict = None) -> bool:
    """
    Download JSON from URL and save to file

    Args:
        url: URL to download JSON from
        filepath: Path to save the JSON file
        headers: Optional headers for the request

    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading JSON from {url}: {e}")
        return False

    try:
        data = response.json()

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {url}: {e}")
        return False

    return save_json_data(filepath, data)


def ensure_directory_exists(directory: str) -> bool:
    """
    Ensure directory exists, create if necessary

    Args:
        directory: Directory path

    Returns:
        True if directory exists or was created successfully
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except OSError as e:
        logger.error(f"Error creating directory {directory}: {e}")
        return False


def save_mapping_file(mapping_data: dict, filepath: str) -> bool:
    """
    Save mapping data to JSON file

    Args:
        mapping_data: Dictionary to save
        filepath: Path to save the file

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)
        return True

    except IOError as e:
        logger.error(f"Error saving mapping file to {filepath}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving mapping file: {e}")
        return False


def download_file(url: str) -> Tuple[str, Optional[requests.Response]]:
    """
    Download a single file from URL using thread-local session

    Args:
        url: URL to download from

    Returns:
        Tuple of (url, response) or (url, None) if failed
    """
    try:
        session = get_session()
        response = session.get(url, verify=False, timeout=30)
        response.raise_for_status()
        return url, response
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file from {url}: {e}")
        return url, None
    except Exception as e:
        logger.error(f"Unexpected error downloading from {url}: {e}")
        return url, None


def parallel_download(
        urls: List[str],
        process_callback: Callable[[str, requests.Response], bool],
        max_workers: int = COUNT_DOWNLOAD_FILES
) -> Tuple[int, int]:
    """
    Download multiple files in parallel and process them
    Uses batching to prevent too many open files

    Args:
        urls: List of URLs to download
        process_callback: Function to process each downloaded file
                         Takes (url, response) and returns success boolean
        max_workers: Maximum number of parallel download threads

    Returns:
        Tuple of (successful_count, failed_count)
    """
    successful = 0
    failed = 0

    # Process in batches to avoid too many open files
    batch_size = max_workers * 10

    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i + batch_size]
        logger.info(
            f"Processing batch {i // batch_size + 1}/{(len(urls) - 1) // batch_size + 1} ({len(batch_urls)} files)")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks for this batch
            future_to_url = {executor.submit(download_file, url): url for url in batch_urls}

            # Process results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    url, response = future.result()
                    if response is not None:
                        try:
                            if process_callback(url, response):
                                successful += 1
                            else:
                                failed += 1
                        finally:
                            # Explicitly close response to free resources
                            response.close()
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Error processing download result for {url}: {e}")
                    failed += 1

    logger.info(f"Parallel download completed: {successful} successful, {failed} failed")
    return successful, failed


class BasePlatformToTaskConverter(ABC):
    """Base class for handling different types of data processing"""

    @abstractmethod
    def run(self, package_url: str, label_properties_url: str, upload_folder: str) -> bool:
        """
        Download and process data from the package URL

        Args:
            package_url: URL to download the package data
            label_properties_url: URL to download the label properties json
            upload_folder: Directory to store the processed data

        Returns:
            bool: True if processing was successful, False otherwise
        """
        pass
