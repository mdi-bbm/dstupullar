from abc import ABC, abstractmethod

from common.models import DigitalAssistantBase
from quantitave_analysis.models.common.base_config import BaseModelConfig 

class ModelHandlerBase(ABC, DigitalAssistantBase):
    model_handler_config: BaseModelConfig

    @abstractmethod
    def run_train(self, train_data_folder: str, output_folder: str, training_epochs: int = None):
        pass

    @abstractmethod
    def run_predict(self, inference_data_folder: str, results_folder: str):
        pass
