import requests
import logging
import threading
from types import MappingProxyType
from collections.abc import Mapping
from typing import Type
import urllib3

from quantitave_analysis.utils.temporary_storage import TemporaryStorageManager
from quantitave_analysis.models.config import Config
from ML_server.config import Config as ConfigServer
from common.models import TaskPackage, TaskType, PackageStatus, ProcessingMode
from common.platform_to_task_converter.segmentation_converter import SegmentationPlatformToTaskConverter
from common.platform_to_task_converter.detection_converter import DetectionPlatformToTaskConverter
from common.platform_to_task_converter.base import BasePlatformToTaskConverter
from common.results_to_platform_converter.base import BaseResultsToPlatformConverter
from common.results_to_platform_converter.segmentation_converter import SegmentationResultsToPlatformConverter
from common.results_to_platform_converter.detection_converter import DetectionResultsToPlatformConverter
from ML_server.ml_routines.base import MLRoutinesBase
from ML_server.ml_routines.segmentation_routines import SegmentationRoutines
from ML_server.ml_routines.detection_routines import DetectionRoutines

logger = logging.getLogger()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONVERTERS_PLATFORM_TO_TASK: Mapping[ProcessingMode, Type[BasePlatformToTaskConverter]] = MappingProxyType({
    ProcessingMode.SEGMENTATION: SegmentationPlatformToTaskConverter,
    ProcessingMode.DETECTION: DetectionPlatformToTaskConverter
})

CONVERTERS_RESULTS_TO_PLATFORM: Mapping[ProcessingMode, Type[BaseResultsToPlatformConverter]] = MappingProxyType({
    ProcessingMode.SEGMENTATION: SegmentationResultsToPlatformConverter,
    ProcessingMode.DETECTION: DetectionResultsToPlatformConverter
})

ROUTINES: Mapping[ProcessingMode, Type[MLRoutinesBase]] = MappingProxyType({
    ProcessingMode.SEGMENTATION: SegmentationRoutines,
    ProcessingMode.DETECTION: DetectionRoutines
})


class Job:
    def __init__(self,
                 task_package: TaskPackage,
                 status_update_url,
                 update_package_status,
                 result_upload_url):
        self.task_package = task_package
        self.upload_folder = Config().UPLOAD_FOLDER
        self.processed_folder = Config().PROCESSED_FOLDER
        self.models_directory = Config().ALL_MODELS_FOLDER
        self.return_folder = Config().RETURN_FOLDER
        self.status_update_url = status_update_url
        self.update_package_status = update_package_status
        self.result_upload_url = result_upload_url
        self.storage_manager = TemporaryStorageManager()


    def send_status(self, status: str) -> None:
        """Send status updates to the platform"""
        try:
            response = requests.put(
                self.status_update_url,
                json={'status': status, 'dataset_id': self.task_package.dataset_id},
                headers=ConfigServer().authorization(),
                verify=False
            )
            logger.info(f"Status sent: {status}, Dataset ID: {self.task_package.dataset_id} Response: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending status: {e}")

    def update_package_status_for_PI(self, package_status_PI: str = PackageStatus.DONE) -> None:
        """Update package status to DONE (or CREATED if error)"""
        try:
            response = requests.put(
                self.update_package_status + str(self.task_package.package_id) + '/',
                json={'package_status': package_status_PI},
                headers=ConfigServer().authorization(),
                verify=False
            )
            logger.info(f"Status sent: {package_status_PI}, Response: {response.status_code}")
        except Exception as e:
            logger.error(f"Error updating package status: {e}")

    def prepare_directories(self) -> None:
        """Prepare directories for processing"""
        # Ensure upload folder exists
        self.storage_manager.reset_directory(self.upload_folder)
        self.storage_manager.reset_directory(self.processed_folder)

        # For inference tasks, clear and recreate return folder
        if self.task_package.task == TaskType.INFERENCE:
            self.storage_manager.reset_directory(self.return_folder)


    def run(self) -> bool:
        """Run the job processing pipeline"""
        try:
            self.prepare_directories()

            # Step 1: Data Processing - Download and prepare data
            data_processor = CONVERTERS_PLATFORM_TO_TASK[self.task_package.mode]()
            if not data_processor:
                raise ValueError(f"No processor available for mode: {self.task_package.mode}")

            if not data_processor.run(self.task_package.package, self.task_package.label_properties, self.upload_folder):
                logger.error("Data processing failed")
                return False

            # Step 2: ML Processing - Run train or inference
            ml_routine = ROUTINES[self.task_package.mode]()
            if not ml_routine:
                raise ValueError(f"No ML routine available for mode: {self.task_package.mode}")

            if self.task_package.task == TaskType.TRAIN:
                # Training workflow
                self.send_status('CREATE DATASET')
                ml_routine.create_dataset(self.upload_folder, self.processed_folder)

                self.send_status('TRAINING')
                train_success = ml_routine.train(self.processed_folder, self.models_directory, self.task_package.dataset_id)

                if train_success:
                    self.update_package_status_for_PI()
                else:  
                    self.update_package_status_for_PI(PackageStatus.CREATED)
                self.send_status('FREE')
                return True

            elif self.task_package.task == TaskType.INFERENCE:
                # Inference workflow
                self.send_status('INFERENCE')
                predict_success = ml_routine.predict(self.upload_folder, self.return_folder, self.task_package.dataset_id)

                # Step 3: Post Processing - Prepare and upload results
                self.send_status('DOWNLOAD')
                post_processor = CONVERTERS_RESULTS_TO_PLATFORM[self.task_package.mode]()
                if not post_processor:
                    raise ValueError(f"No post-processor available for mode: {self.task_package.mode}")

                if not post_processor.run(self.return_folder, self.upload_folder, self.result_upload_url, self.task_package.package_id):
                    logger.error("Post processing failed")
                    return False

                if predict_success:
                    self.update_package_status_for_PI()
                else:  
                    self.update_package_status_for_PI(PackageStatus.CREATED)
                self.send_status('FREE')
                return True

            self.update_package_status_for_PI(PackageStatus.CREATED)
            self.send_status('FREE')
            return False

        except Exception as e:
            logger.error(f"Error in job execution: {e}")
            self.update_package_status_for_PI(PackageStatus.CREATED)
            self.send_status('FREE')
            return False


def run_job_async(job: Job) -> threading.Thread:
    """Run a job in a separate thread"""
    thread = threading.Thread(target=job.run)
    thread.start()
    return thread
