from autogluon.multimodal.learners import ObjectDetectionLearner
import logging
import torch
from lightning.pytorch.callbacks import Callback

logger = logging.getLogger(__name__)

class GpuMemoryLoggerCallback(Callback):
    def on_train_epoch_start(self, trainer, pl_module):
        gb = torch.cuda.memory_allocated() / 1024**3
        logger.info(f"train epoch {trainer.current_epoch} start GPU memory {gb:.2f} GB")

    def on_train_epoch_end(self, trainer, pl_module):
        gb = torch.cuda.memory_allocated() / 1024**3
        logger.info(f"train epoch {trainer.current_epoch} end GPU memory {gb:.2f} GB")

    def on_validation_epoch_start(self, trainer, pl_module):
        gb = torch.cuda.memory_allocated() / 1024**3
        logger.info(f"validation epoch {trainer.current_epoch} start GPU memory {gb:.2f} GB")

    def on_validation_epoch_end(self, trainer, pl_module):
        gb = torch.cuda.memory_allocated() / 1024**3
        logger.info(f"validation epoch {trainer.current_epoch} end GPU memory {gb:.2f} GB")

class CustomObjectDetectionLearner(ObjectDetectionLearner):
    
    def get_callbacks_per_run(self, save_path=None, config=None, litmodule=None, pred_writer=None, is_train=True):

        callbacks = super().get_callbacks_per_run(save_path, config, litmodule, pred_writer, is_train)
        
        #gpu_logger = GpuUsageLogger(memory_utilization=True, gpu_utilization=True)
        gpu_logger = GpuMemoryLoggerCallback()

        callbacks.append(gpu_logger)
        
        return callbacks