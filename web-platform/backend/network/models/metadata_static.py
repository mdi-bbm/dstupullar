import os
from django.db import models
from .devices import Device_Type, Scaling_Value

def record_metadata_path(instance, object_storage_file_name):
    object_storage_dataset_name = instance.datasets_set.first().dataset_name
    return os.path.join(
        object_storage_dataset_name,
        'Metadata_Static',
        object_storage_file_name
    )

class Metadata_Static(models.Model):
    metadata_static_id = models.BigAutoField(primary_key=True)
    arbitrary_data = models.FileField(upload_to=record_metadata_path, null=True, blank=True)
    asset_structure = models.FileField(upload_to=record_metadata_path, null=True, blank=True)
    device_type_id = models.ForeignKey(Device_Type, on_delete=models.SET_NULL, db_column='device_type_id', null=True, blank=True)
    scaling_value_id = models.ForeignKey(Scaling_Value, on_delete=models.SET_NULL, db_column='scaling_value_id', null=True, blank=True)
    scales = models.JSONField(
        default=list,
        blank=True,
        help_text="[{'barcode': 10, 'unit': 'nm', 'value_per_pixel': 0.5}]"
    )

    def __str__(self):
        return str(self.metadata_static_id)
