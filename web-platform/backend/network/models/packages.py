import os
from django.db import models
from .users import Users
from .datasets import Datasets

def package_path(instance, filename):
    dataset_name = instance.dataset_id.dataset_name
    return os.path.join(
        dataset_name,
        'Packages',
        filename
    )

def record_label_path(instance, object_storage_file_name):
    object_storage_dataset_name = instance.dataset_id.dataset_name
    return os.path.join(
        object_storage_dataset_name,
        'Label_Properties',
        object_storage_file_name
    )

class Package(models.Model):
    package_id = models.BigAutoField(primary_key=True)
    mode = models.CharField(max_length=255)
    task = models.CharField(max_length=255)
    package_status = models.CharField(max_length=255)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    dataset_id = models.ForeignKey(Datasets, on_delete=models.CASCADE, db_column='dataset_id')
    package = models.FileField(upload_to=package_path, null=True, blank=True)
    label_properties = models.FileField(upload_to=record_label_path, null=True, blank=True)

    def __str__(self):
        return str(self.package_id)
