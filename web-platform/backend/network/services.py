import json
import yaml
import random
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Assets, Records, Access_Policies, Metadata_Static, Device_Type, Scaling_Value, Access_Group_Linkage, Datasets, Groups, Group_User_Linkage, Roles, Assets_Metadata_Dynamic, Segmentation, Detection
from .serializers import MetadataStaticSerializer, Metadata_Static, DeviceTypeSerializer, Device_Type, ScalingValueSerializer, Scaling_Value, Package
from .utils import remove_empty_dirs, remove_empty_dirs_for_asset


def generate_unique_color(used_colors):
    while True:
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        if color not in used_colors:
            used_colors.add(color)
            return color

def extract_leaf_classes(data):

    if isinstance(data, list):
        return data 

    if isinstance(data, dict):
        leaf_classes = []
        for key, value in data.items():
            if isinstance(value, dict) and value:  
                leaf_classes.extend(extract_leaf_classes(value))
            elif isinstance(value, list) and value:  
                leaf_classes.extend(value)
            else:
                leaf_classes.append(key)  
        return leaf_classes

    return []


def process_label_properties(file_content, is_yaml=False):
       
        data = yaml.safe_load(file_content) if is_yaml else json.loads(file_content)
        classes = data if isinstance(data, list) else extract_leaf_classes(data)
        used_colors = set()
        result = {cls: generate_unique_color(used_colors) for cls in classes}

        return result

def create_dataset(serializer):
    metadata_static_serializer_model_dict = {
            'metadata_static': [MetadataStaticSerializer, Metadata_Static],
            'device_type': [DeviceTypeSerializer, Device_Type],
            'scaling_value': [ScalingValueSerializer, Scaling_Value],
    }
    
    label_properties_file = serializer.validated_data.get('label_properties', None)
    
    
    access_type_id = serializer.validated_data['access_type']
    access_policies_object = Access_Policies.objects.create(access_type_id=access_type_id)
    group_object = Groups.objects.create()
    Access_Group_Linkage.objects.create(group_id=group_object, access_policy_id=access_policies_object)
    admin_role_for_user = Roles.objects.get(role_name='Admin')
    Group_User_Linkage.objects.create(group_id=group_object, user_id= serializer.validated_data['owner'], role_id=admin_role_for_user)

    dataset_object = Datasets.objects.create()
    dataset_object.dataset_name = str(dataset_object.dataset_id)+'_'+serializer.validated_data['dataset_name']
    dataset_object.access_policy_id = access_policies_object
   
    label_properties_json = json.dumps({'Standart_label': '#FF0000'})

    if label_properties_file:
        file_content = label_properties_file.read()
        is_yaml = label_properties_file.name.endswith((".yaml", ".yml")) 
        processed_data = process_label_properties(file_content, is_yaml=is_yaml)
        label_properties_json = json.dumps(processed_data, ensure_ascii=False, indent=4)

    dataset_object.label_properties = ContentFile(label_properties_json, name='label_properties.json')

    metadata_static_data = serializer.validated_data.get('metadata_static', {})
    if metadata_static_data:
        metadata_static_serializer = metadata_static_serializer_model_dict['metadata_static'][0](data=metadata_static_data)
        if metadata_static_serializer.is_valid():
            metadata_validated_data = metadata_static_serializer.validated_data
            metadata_static_object = Metadata_Static.objects.create()
            dataset_object.metadata_static_id=metadata_static_object
           
            for key, value in metadata_validated_data.items():
               
                if key in metadata_static_serializer_model_dict:
                    sub_serializer = metadata_static_serializer_model_dict[key][0](data=value)
                    if sub_serializer.is_valid():
                        obj, _ = metadata_static_serializer_model_dict[key][1].objects.get_or_create(**{key+'_name': sub_serializer.validated_data[key+'_name']})
                        setattr(metadata_static_object, key+'_id', obj)
                elif key == 'arbitrary_data':
                    metadata_static_object.arbitrary_data = ContentFile(json.dumps(metadata_validated_data['arbitrary_data']), name='arbitrary_data.json')
                elif key == 'asset_structure':
                    metadata_static_object.asset_structure = ContentFile(json.dumps(metadata_validated_data['asset_structure']), name='asset_structure.json')
                elif key == 'scales':
                    metadata_static_object.scales = metadata_validated_data['scales']
            metadata_static_object.save()
    dataset_object.save()
    return dataset_object


def delete_record(record_id, record_db_path):
    record_mask = Segmentation.objects.filter(record_id= record_id).first()
    if record_mask is not None:
        mask_storage_path = record_mask.record_metadata_dynamic_link.name
        mask_storage_path_metric = record_mask.metrics.name
        default_storage.delete(mask_storage_path)
        default_storage.delete(mask_storage_path_metric)
        remove_empty_dirs(record_mask.record_metadata_dynamic_link)
        remove_empty_dirs(record_mask.metrics)
    record_bbox = Detection.objects.filter(record_id= record_id).first()
    if record_bbox is not None:
        bbox_storage_path = record_bbox.record_metadata_dynamic_link.name
        bbox_storage_path_metric = record_bbox.metrics.name

        if bbox_storage_path: 
            default_storage.delete(bbox_storage_path)

        if bbox_storage_path_metric:
            default_storage.delete(bbox_storage_path_metric)
        remove_empty_dirs(record_bbox.record_metadata_dynamic_link)
        remove_empty_dirs(record_bbox.metrics)
    default_storage.delete(record_db_path)
    record_link = Records.objects.get(record_id = record_id).record_link
    remove_empty_dirs(record_link)
    Records.objects.get(record_id = record_id).delete()

def delete_asset(asset_id):
    asset_records = Records.objects.filter(asset_id=asset_id)
    asset=Assets.objects.get(asset_id = asset_id)
    asset_metadata_dynamic = Assets_Metadata_Dynamic.objects.filter(asset_id=asset_id).first()
    if asset_metadata_dynamic:
        if asset_metadata_dynamic.arbitrary_data_json_link:
            arbitrary_metadata = asset_metadata_dynamic.arbitrary_data_json_link.name
            default_storage.delete(arbitrary_metadata)
        if asset_metadata_dynamic.object_metadata_id:
            if len(Assets_Metadata_Dynamic.objects.filter(object_metadata_id = asset_metadata_dynamic.object_metadata_id))==1:
                asset_metadata_dynamic.object_metadata_id.delete()
    for record in asset_records:
        record_db_path = record.record_link.name
        record_id = record.record_id
        delete_record(record_id, record_db_path)
    
    if asset.metrics:
        asset_metrics_path = asset.metrics.name
        default_storage.delete(asset_metrics_path)
        remove_empty_dirs(asset.metrics)
    remove_empty_dirs_for_asset(Assets.objects.get(asset_id = asset_id).asset_name)
    asset.delete()


def delete_dataset(dataset_id):
    dataset_assets = Assets.objects.filter(dataset_id=dataset_id)
    for asset in dataset_assets:
        delete_asset(asset.asset_id)
    dataset_package = Package.objects.filter(dataset_id=dataset_id).first()
    if dataset_package:
        dataset_package_link = dataset_package.package.name
        default_storage.delete(dataset_package_link)
        dataset_package.delete()
        remove_empty_dirs(dataset_package.package)

    dataset_object = Datasets.objects.get(dataset_id=dataset_id)
    dataset_access_policy = dataset_object.access_policy_id
    access_group_linkage = Access_Group_Linkage.objects.get(access_policy_id=dataset_object.access_policy_id.access_policy_id)
    group = access_group_linkage.group_id
    group.delete()
    dataset_access_policy.delete()
    if dataset_object.metrics:
        dataset_object_metrics_path = dataset_object.metrics.name
        default_storage.delete(dataset_object_metrics_path)
        remove_empty_dirs(dataset_object.metrics)
    if dataset_object.metadata_static_id:
        dataset_metadata_static = dataset_object.metadata_static_id
        if dataset_metadata_static.arbitrary_data:
            dataset_arbitrary_data = dataset_metadata_static.arbitrary_data.name
            default_storage.delete(dataset_arbitrary_data)
            remove_empty_dirs(dataset_metadata_static.arbitrary_data)
        elif dataset_metadata_static.asset_structure:
            dataset_asset_structure = dataset_metadata_static.asset_structure.name
            default_storage.delete(dataset_asset_structure)
        
        dataset_metadata_static.delete()

    if dataset_object.label_properties:
        dataset_label_properties = dataset_object.label_properties.name
        default_storage.delete(dataset_label_properties)
        remove_empty_dirs(dataset_object.label_properties)

    dataset_object.delete()