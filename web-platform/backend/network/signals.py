from django.dispatch import receiver
from django.contrib.auth.hashers import make_password
from .models import Datasets, Assets, Records, Segmentation, Processing_Types, Access_Policies, Access_Types, Group_User_Linkage, Users, Roles, Groups, Access_Group_Linkage
from django.conf import settings
import os
from django.core.files import File
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps

@receiver(post_migrate)
def create_initial_access_and_roles(sender, **kwargs):
    if sender.name != "network":
        return

    AccessType = apps.get_model('network', 'Access_Types')
    Role = apps.get_model('network', 'Roles')
    Processing_Types = apps.get_model('network', 'Processing_Types')
    Users = apps.get_model('network', 'Users')

    AccessType.objects.get_or_create(access_type_name='Private')
    AccessType.objects.get_or_create(access_type_name='Public')

    Role.objects.get_or_create(role_name='Admin')
    Role.objects.get_or_create(role_name='Editor')
    Role.objects.get_or_create(role_name='Viewer')

    Processing_Types.objects.get_or_create(processing_type_id=1, processing_type='Segmentation')
    Processing_Types.objects.get_or_create(processing_type_id=2, processing_type='Detection')
    
    Users.objects.get_or_create(
        username='user',
        defaults={
            'password': make_password('userpass') 
        }
    )
  
    create_initial_dataset()

    
def create_initial_dataset():
 
    dataset_name = '1_Blood_Cells_Image_Dataset'
    dataset_path = os.path.join(settings.MEDIA_ROOT, dataset_name)
    print(dataset_path)
    
    if os.path.isdir(dataset_path) and not Datasets.objects.filter(dataset_name=dataset_name).exists():
       
        dataset, created = Datasets.objects.get_or_create(
            dataset_name=dataset_name,
            access_policy_id=Access_Policies.objects.create(access_type_id=Access_Types.objects.get(access_type_name='Public')),
        )
        
        group_object = Groups.objects.create()
        Access_Group_Linkage.objects.create(group_id=group_object, access_policy_id=dataset.access_policy_id)
        admin_role_for_user = Roles.objects.get(role_name='Admin')
        Group_User_Linkage.objects.create(group_id=group_object, user_id= Users.objects.get(username='user'), role_id=admin_role_for_user)

        for asset_name in os.listdir(dataset_path):
            if asset_name == 'Label_Properties' or asset_name == 'Metrics':
                continue
            asset_path = os.path.join(dataset_path, asset_name)
           
            
            if os.path.isdir(asset_path):
                asset, asset_created = Assets.objects.get_or_create(
                    asset_name=asset_name,
                    dataset_id=dataset,
                )
                
                raw_path = os.path.join(asset_path, 'Raw')
                if os.path.exists(raw_path):
                   
                    process_images_and_masks(asset, raw_path, asset_path)
                
                
        label_props_path = os.path.join(dataset_path, 'Label_Properties')
        
        if os.path.exists(label_props_path):
            json_file_path = os.path.join(label_props_path, 'label_properties.json')
            
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as f:
                    dataset.label_properties = File(f, name='label_properties.json')
                    dataset.save()
                   

                    
def process_images_and_masks(asset, images_path, asset_path):
    print(images_path)
    for filename in os.listdir(images_path):
        if filename.lower().endswith('.webp'):
            file_path = os.path.join(images_path, filename)
            base_name = os.path.splitext(filename)[0]
            
            try:
              
                with open(file_path, 'rb') as f:
                    record, created = Records.objects.get_or_create(
                        asset_id=asset,
                        
                        record_link= File(f, name=filename)
                        
                    )
                
                if created:
                    
                    seg_path = os.path.join(asset_path, 'Processed/Segmentation') 
                    mask_filename = f"{base_name}_mask.webp"
                    mask_path = os.path.join(seg_path, mask_filename)
                    
                    if os.path.exists(mask_path):
                        with open(mask_path, 'rb') as f:
                            mask, mask_created = Segmentation.objects.get_or_create(
                                record_id=record,
                                processing_type_id=Processing_Types.objects.get(processing_type='Segmentation'),
                           
                                record_metadata_dynamic_link=File(f, name=mask_filename)
                                
                            )
                        
                        if mask_created:
                            record.validation_mask_flag = True
                            record.save()
                            
              
            except Exception as e:
                print(f"Error processing {filename}: {e}")

