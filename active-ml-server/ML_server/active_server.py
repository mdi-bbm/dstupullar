import time
import requests
import threading
import logging
from flask import Flask
from waitress import serve
from flask_cors import CORS
from urllib.parse import urljoin
import urllib3
import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from ML_server.config import Config
from common.models import TaskPackage, ProcessingMode, PackageStatus
from ML_server.jobs import Job

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

app = Flask(__name__)
CORS(app)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



class ActiveServer:
    def __init__(self,
                 get_package_url=Config().GET_PACKAGE_URL,
                 status_update_url=Config().STATUS_UPDATE_URL,
                 update_package_status=Config().UPDATE_PACKAGE_STATUS,
                 result_upload_url=Config().RESULT_UPLOAD_URL,
                 check_interval=10):
        self.get_package_url = get_package_url
        self.status_update_url = status_update_url
        self.update_package_status = update_package_status
        self.result_upload_url = result_upload_url
        self.check_interval = check_interval

        self._task_lock = threading.Lock()
        self._is_busy = False
        self.current_task = None


    def build_full_url(self, url):
        if url.startswith('https'):
            return url

        return urljoin(Config().BASE_URL, url)

    def process_package(self, package_data: dict) -> bool:
        try:
            with self._task_lock:
                self._is_busy = True
                self.current_task = TaskPackage.model_validate(package_data)

            self.current_task.package = self.build_full_url(self.current_task.package)
            self.current_task.label_properties = self.build_full_url(self.current_task.label_properties)

            # Create an instance of Job and start it in a separate thread
            job = Job(
                task_package=self.current_task,
                status_update_url=self.status_update_url,
                update_package_status=self.update_package_status,
                result_upload_url=self.result_upload_url
            )

            # Start job processing in a separate thread
            job_thread = threading.Thread(target=self._run_job, args=(job,))
            job_thread.start()
            return True

        except Exception as e:
            requests.put(
                        self.update_package_status + str(package_data['package_id']) + '/',
                        json={'package_id': package_data['package_id'], 'package_status': PackageStatus.CREATED},
                        headers=Config().authorization(),
                        verify=False
                    )

            logger.error(f"Error processing package: {e}")
            # We release the server only when the error of creating a task
            with self._task_lock:
                self._is_busy = False
                self.current_task = None
            return False

    def _run_job(self, job: Job):
        try:
            success = job.run()
            if not success:
                logger.error("Job failed to complete")
        except Exception as e:
            logger.error(f"Error running job: {e}")
            job.update_package_status(PackageStatus.CREATED)
        finally:
            # We free the server after the completion of the task (successful or not)
            with self._task_lock:
                self._is_busy = False
                self.current_task = None
            logger.info("Server is now free")

    def check_packages(self):
        while True:
            if self._is_busy:
                time.sleep(self.check_interval)
                continue

            try:
                # Requesting a new package
                response = requests.get(
                    self.get_package_url,
                    headers=Config().authorization(),
                    verify=False
                )


                if response.status_code == 200 and response.json().get('package_status') == PackageStatus.CREATED:
                    logger.info("Package available")
                    package = response.json()

                    # Check if the processing mode is supported
                    if package['mode'] in (ProcessingMode.DETECTION, ProcessingMode.SEGMENTATION):
                        # Update the status of the package to "in processing"
                        try:
                            update_response = requests.put(
                                self.update_package_status + str(package['package_id']) + '/',
                                json={'package_id': package['package_id'], 'package_status': PackageStatus.IN_PROGRESS},
                                headers=Config().authorization(),
                                verify=False
                            )
                            if update_response.status_code == 200:
                                # Start processing the packet
                                if not self.process_package(package):
                                    # If it was not possible to start processing, reset the status of the package
                                    logger.error("Failed to start package processing")
                                    requests.put(
                                        self.update_package_status + str(package['package_id']) + '/',
                                        json={'package_id': package['package_id'],
                                              'package_status': PackageStatus.CREATED},
                                        headers=Config().authorization(),
                                        verify=False
                                    )
                            else:
                                logger.error(f"Failed to update package status: {update_response.status_code}")
                        except Exception as e:
                            logger.error(f"Error updating package status: {e}")
                    else:
                        logger.error(f"Unsupported processing mode: {package['mode']}")
                        # Return the package to the status of Created, because We cannot process it
                        requests.put(
                            self.update_package_status + str(package['package_id']) + '/',
                            json={'package_id': package['package_id'], 'package_status': PackageStatus.CREATED},
                            headers=Config().authorization(),
                            verify=False
                        )

            except Exception as e:
                logger.error(f"Error in package checking: {e}")

            time.sleep(self.check_interval)


def start_package_checker(active_server):
    threading.Thread(target=active_server.check_packages, daemon=True).start()


def run_active_server():
    active_server = ActiveServer()
    start_package_checker(active_server)
    logger.info("Starting active server")
    serve(app, host='*', port=8000)


if __name__ == '__main__':
    run_active_server()