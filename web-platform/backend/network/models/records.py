import os
from django.db import models
from .datasets import Assets
from .processing import Processing_Types

def record_file_path(instance, filename):
    dataset_name = instance.asset_id.dataset_id.dataset_name
    asset_name = instance.asset_id.asset_name

    return os.path.join(
        dataset_name,
        asset_name,
        'Raw',
        filename
    )

def record_metadata_dynamic_path(instance, filename):
    record = instance.record_id
    processing_type = instance.processing_type_id.processing_type
    dataset_name = record.asset_id.dataset_id.dataset_name
    asset_name = record.asset_id.asset_name
    return os.path.join(
        dataset_name,
        asset_name,
        'Processed',
        processing_type,
        filename
    )

def record_metrics_path(instance, filename):
    record = instance.record_id
    processing_type = instance.processing_type_id.processing_type
    dataset_name = record.asset_id.dataset_id.dataset_name
    asset_name = record.asset_id.asset_name
    return os.path.join(
        dataset_name,
        asset_name,
        'Processed',
        'Metrics',
        processing_type,
        filename
    )

class Records(models.Model):
    record_id = models.BigAutoField(primary_key=True)
    record_link = models.FileField(upload_to=record_file_path)
    asset_id = models.ForeignKey(Assets, on_delete=models.CASCADE, db_column='asset_id')
    validation_mask_flag = models.BooleanField(default=False)
    validation_bbox_flag = models.BooleanField(default=False)
    description_mask = models.JSONField(null=True, blank=True)
    description_bbox = models.JSONField(null=True, blank=True)

    def __str__(self):
        return str(self.record_id)

class Record_Metadata_Dynamic(models.Model):
    record_metadata_dynamic_id = models.BigAutoField(primary_key=True)
    record_metadata_dynamic_link = models.FileField(upload_to=record_metadata_dynamic_path, null=True, blank=True, max_length=500)
    processing_type_id = models.ForeignKey(Processing_Types, on_delete=models.CASCADE, db_column='processing_type_id', null=True, blank=True)
    record_id = models.OneToOneField("Records", on_delete=models.CASCADE, null=True, blank=True, db_column='record_id' )
    metrics = models.FileField(upload_to=record_metrics_path, null=True, blank=True, max_length=500)

    class Meta:
        abstract = True

class Segmentation(Record_Metadata_Dynamic):

    def __str__(self):
        return f"Segmentation {self.record_metadata_dynamic_id}"

class Detection(Record_Metadata_Dynamic):

    def __str__(self):
        return f"Detection {self.record_metadata_dynamic_id}"
