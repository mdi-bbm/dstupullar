import torch
import gc
import logging

logger = logging.getLogger(__name__)


def clear_cuda_memory() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        torch.cuda.synchronize()
        logger.info("CUDA memory cache cleared")

def clear_python_objects(*objs: object) -> None:
    for obj in objs:
        if obj is None:
            continue
        del obj
    logger.info("Python objects deleted")

def clear_memory(*objs: object, to_cpu: bool = True) -> None:
    for obj in objs:
        if obj is None:
            continue
        if to_cpu and hasattr(obj, "to"):
            try:
                obj.to("cpu")
            except Exception:
                pass

    clear_python_objects(*objs)
    gc.collect()
    clear_cuda_memory()
    logger.info("Memory cache cleared")
