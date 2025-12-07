import json
import os
from django.db import models

from .roles import Group_User_Linkage
from .metadata_static import Metadata_Static
from .access import Access_Group_Linkage, Access_Policies


def record_label_path(instance, object_storage_file_name):
    object_storage_dataset_name = instance.dataset_name
    return os.path.join(
        object_storage_dataset_name,
        'Label_Properties',
        object_storage_file_name
    )

def dataset_metrics_path(instance, filename):
    print(instance)
    dataset = Datasets.objects.get(dataset_id=instance.dataset_id)
    dataset_name = dataset.dataset_name

    return os.path.join(
        dataset_name,
        'Metrics',
        filename
    )

def asset_metrics_path(instance, filename):


    
    asset = Assets.objects.get(asset_id=instance.asset_id)
    asset_name = asset.asset_name
    dataset_name = asset.dataset_id.dataset_name
    return os.path.join(
        dataset_name,
        asset_name,
        'Metrics',
        
        filename
    )


class Datasets(models.Model):
    dataset_id = models.BigAutoField(primary_key=True)
    dataset_name = models.CharField(max_length=255, null=True, blank=True)
    label_properties = models.FileField(upload_to=record_label_path, null=True, blank=True)
    metadata_static_id = models.ForeignKey(Metadata_Static, on_delete=models.SET_NULL, db_column='metadata_static_id', null=True, blank=True)
    access_policy_id = models.ForeignKey(Access_Policies, on_delete=models.CASCADE, db_column='access_policy_id', null=True, blank=True)
    metrics = models.FileField(upload_to=dataset_metrics_path, null=True, blank=True, max_length=500)
    status = models.CharField(max_length=50, default='FREE', blank=True, null=True)

    def __str__(self):
        return str(self.dataset_id)
    
    @property
    def label_properties_json(self):
        if self.label_properties:
            with self.label_properties.open('r') as f:
                return json.load(f)
        return {}

    def has_admin_access(self, user):
        access_group = Access_Group_Linkage.objects.get(access_policy_id=self.access_policy_id)
        group_user_ids = Group_User_Linkage.objects.filter(
            group_id=access_group.group_id,
            role_id__role_name__in=['Admin']
        ).values_list('user_id', flat=True)
        return user.user_id in group_user_ids
    
    def has_editor_access(self, user):
        access_group = Access_Group_Linkage.objects.get(access_policy_id=self.access_policy_id)
        group_user_ids = Group_User_Linkage.objects.filter(
            group_id=access_group.group_id,
            role_id__role_name__in=['Editor']
        ).values_list('user_id', flat=True)
        return user.user_id in group_user_ids

 

class Assets(models.Model):
    asset_id = models.BigAutoField(primary_key=True)
    asset_name = models.CharField(max_length=255)
    dataset_id = models.ForeignKey(Datasets, on_delete=models.CASCADE, db_column='dataset_id')
    metrics = models.FileField(upload_to=asset_metrics_path, null=True, blank=True, max_length=500)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.asset_id)
