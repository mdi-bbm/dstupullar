import shutil
from pydantic import BaseModel
from abc import ABC, abstractmethod

class ZipProcessorConfig(BaseModel):
    storage_root: str

class IZipProcessor(ABC):
    @abstractmethod
    def create_zip(self, source_dir: str, zip_path: str) -> None:
        pass

    @abstractmethod
    def extract_zip(self, zip_path: str, extract_to: str) -> None:
        pass
    
class ZipProcessor(IZipProcessor):
    def create_zip(self, source_dir: str, zip_path: str) -> None:
        shutil.make_archive(zip_path.replace(".zip", ""), 'zip', source_dir)

    def extract_zip(self, zip_path: str, extract_to: str) -> None:
        shutil.unpack_archive(zip_path, extract_to, 'zip')