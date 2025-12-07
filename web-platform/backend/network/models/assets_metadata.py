import os
from django.db import models
from .datasets import Assets
from .taxonomy import Object_Metadata
from .localization import Localization, Diagnosis

def record_dynamic_path(instance, filename):
    dataset_name = instance.asset_id.dataset_id.dataset_name
    asset_name = instance.asset_id.asset_name

    return os.path.join(
        dataset_name,
        asset_name,
        'Arbitrary_Metadata',
        filename
    )

class Assets_Metadata_Dynamic(models.Model):
    asset_metadata_dynamic_id = models.BigAutoField(primary_key=True)
    asset_id = models.ForeignKey(Assets, on_delete=models.CASCADE, db_column='asset_id')
    object_metadata_id = models.ForeignKey(Object_Metadata, on_delete=models.SET_NULL, db_column='object_metadata_id', null=True, blank=True)
    arbitrary_data_json_link = models.FileField(upload_to=record_dynamic_path, null=True, blank=True)
    localization_id = models.ForeignKey(Localization, on_delete=models.SET_NULL, db_column='localization_id', null=True, blank=True)
    diagnosis_id = models.ForeignKey(Diagnosis, on_delete=models.SET_NULL, db_column='diagnosis_id', null=True, blank=True)

    def __str__(self):
        return str(self.asset_metadata_dynamic_id)
