import io
from django.utils import timezone
from celery import shared_task, group, chain
from .models import Datasets, Access_Policies, DownloadDataset, Access_Types, Access_Group_Linkage, Group_User_Linkage, Groups, Users, Roles, Scaling_Value, Device_Type, Metadata_Static, Assets, Records, Species, Diagnosis, Assets_Metadata_Dynamic, Localization, Object_Metadata, Package, Sex, Segmentation, Detection
from .serializers import AccessTypesSerializer, AssetsSerializer, CopyDatasetSerializer, DatasetsSerializer, DeviceTypeSerializer, MetadataStaticSerializer, MetadataDynamicSerializer, LocalizationSerializer, DiagnosisSerializer, RecordsCopySerializer, RecordsSerializer, ScalingValueSerializer, SexSerializer, SpeciesSerializer, ObjectMetadataSerializer
import json 
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
import yaml
import random
import re
import numpy as np
from PIL import Image
from .utils import calculate_segmentation_metrics, download_dataset_files
import tempfile
import os, shutil, zipfile
from django.core.files import File


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
        """Обрабатывает загруженные данные."""
        data = yaml.safe_load(file_content) if is_yaml else json.loads(file_content)

        # Определение конечных классов
        classes = data if isinstance(data, list) else extract_leaf_classes(data)

        # Генерация цветов
        used_colors = set()
        
        result = {cls: generate_unique_color(used_colors) for cls in classes}

        return result

def create_asset_copy(serializer_validated_data):
    metadata_dynamic_serializer_model_dict = {
            'localization': [LocalizationSerializer, Localization],
            'diagnosis': [DiagnosisSerializer, Diagnosis],
           
            }
    object_metadata_data_dict = {
            'species_id': None, 
            'age': None,
            'weight': None,
            'sex_id': None,
        }
    dataset_id = serializer_validated_data['asset_name']['dataset_id'].dataset_id
    serializer_validated_data['asset_name']['dataset_id'] = dataset_id
    asset_data_serializer = AssetsSerializer(data=serializer_validated_data['asset_name'])
    if asset_data_serializer.is_valid():
        asset_data, _ = Assets.objects.get_or_create(asset_name=asset_data_serializer.validated_data['asset_name'], dataset_id=asset_data_serializer.validated_data['dataset_id'])
        metadata_dynamic_data = serializer_validated_data.get('metadata_dynamic', None)
        if metadata_dynamic_data is not None:
            metadata_dynamic_serializer = MetadataDynamicSerializer(data=metadata_dynamic_data)
            if metadata_dynamic_serializer.is_valid():
                metadata_validated_data = metadata_dynamic_serializer.validated_data
                not_none_data = [key for key, value in metadata_validated_data.items() if value is not None]
                metadata_dynamic_object, _ = Assets_Metadata_Dynamic.objects.get_or_create(asset_id=asset_data)
                for data in not_none_data:
                    if data in metadata_dynamic_serializer_model_dict:
                        data_serializer = metadata_dynamic_serializer_model_dict[data][0](data=metadata_dynamic_serializer.validated_data[data])
                        if data_serializer.is_valid():
                            data_id, _= metadata_dynamic_serializer_model_dict[data][1].objects.get_or_create(**{data+'_name' : data_serializer.validated_data[data+'_name']})
                            setattr(metadata_dynamic_object, data+'_id', data_id)
                    elif data == 'arbitrary_data_json_link':
                        metadata_dynamic_object.arbitrary_data_json_link = ContentFile(json.dumps(metadata_dynamic_serializer.validated_data['arbitrary_data_json_link']), name='arbitrary_data.json')
                    elif data == 'object_metadata':
                        object_metadata_serializer = ObjectMetadataSerializer(data=metadata_dynamic_serializer.validated_data['object_metadata'])
                        if object_metadata_serializer.is_valid():
                            object_metadata_validated_data = object_metadata_serializer.validated_data
                            not_obj_none_data = [key for key, value in object_metadata_validated_data.items() if value is not None]
                            for data in not_obj_none_data:
                                if data in object_metadata_data_dict:
                                    object_metadata_data_dict[data]  = object_metadata_serializer.validated_data[data]
                                elif data == 'species':
                                    species_serializer = SpeciesSerializer(data=object_metadata_serializer.validated_data[data])
                                    if species_serializer.is_valid():
                                        species_object, _ = Species.objects.get_or_create(**species_serializer.validated_data)
                                        object_metadata_data_dict['species_id'] = species_object
                                elif data == 'sex':
                                    sex_serializer = SexSerializer(data=object_metadata_serializer.validated_data[data])
                                    if sex_serializer.is_valid():
                                        sex_object = Sex.objects.get(**sex_serializer.validated_data)
                                        object_metadata_data_dict['sex_id'] = sex_object
                            object_metadata_object, _ = Object_Metadata.objects.get_or_create(**object_metadata_data_dict)
                            metadata_dynamic_object.object_metadata_id = object_metadata_object
                metadata_dynamic_object.save()
        records_arr_id = []
        record_links = serializer_validated_data['record_links']
        for record_link in record_links:
            if record_link.content_type.startswith('image/'):
                record_link_data = Image.open(record_link)
                record_link_data_bytes = io.BytesIO()
                record_link_data.save(record_link_data_bytes, format='WEBP', quality=80)
                record_link_name, _ = os.path.splitext(record_link.name) 
                record = Records.objects.create(asset_id = asset_data)
                record_id_str = str((record.record_id))
                record_link_name = f"{record_id_str}_{record_link_name}"
                record.record_link = ContentFile(record_link_data_bytes.getvalue(), name=f"{record_link_name}.webp")
                record.save()
                records_arr_id.append(record)
    return records_arr_id

@shared_task
def create_dataset(serializer, user_id, not_copy):
    metadata_static_serializer_model_dict = {
            
            'metadata_static': [MetadataStaticSerializer, Metadata_Static],
            'device_type': [DeviceTypeSerializer, Device_Type],
            'scaling_value': [ScalingValueSerializer, Scaling_Value],
            }
    dataset_access_type_serializer = AccessTypesSerializer(data=serializer.validated_data['access_type'])
    label_properties_file = serializer.validated_data.get('label_properties', None)
    if dataset_access_type_serializer.is_valid():
        access_type_id = Access_Types.objects.get(access_type_name=dataset_access_type_serializer.validated_data['access_type_name'])
        access_policies_object = Access_Policies.objects.create(access_type_id=access_type_id)
        group_object = Groups.objects.create()
        access_group_linkage_object = Access_Group_Linkage.objects.create(group_id=group_object, access_policy_id=access_policies_object)
        admin_role_for_user = Roles.objects.get(role_name='Admin')
        user = Users.objects.get(user_id=user_id)
        group_user_linkage_object = Group_User_Linkage.objects.create(group_id=group_object, user_id=user, role_id=admin_role_for_user)
        dataset_object = Datasets.objects.create()
        dataset_object.dataset_name = str(dataset_object.dataset_id)+'_'+serializer.validated_data['dataset_name']
        dataset_object.access_policy_id = access_policies_object
        dataset_object.save()
        if label_properties_file is not None:
            file_content = label_properties_file[0].read()
            if not_copy:
                is_yaml = label_properties_file[0].name.endswith((".yaml", ".yml")) 
                processed_data = process_label_properties(file_content, is_yaml=is_yaml)
                processed_json = json.dumps(processed_data, ensure_ascii=False, indent=4)
            else:
                processed_json = file_content
            dataset_object.label_properties.save("label_properties.json", ContentFile(processed_json))
        metadata_static_data = serializer.validated_data.get('metadata_static', None)
        if metadata_static_data is not None:
            metadata_static_serializer = metadata_static_serializer_model_dict['metadata_static'][0](data=metadata_static_data)
            if metadata_static_serializer.is_valid():
                metadata_validated_data = metadata_static_serializer.validated_data
                not_none_data = [key for key, value in metadata_validated_data.items() if value is not None]
                metadata_static_object = Metadata_Static.objects.create()
                dataset_object.metadata_static_id=metadata_static_object
                dataset_object.save()
                for data in not_none_data:
                    if data in metadata_static_serializer_model_dict:
                        data_serializer = metadata_static_serializer_model_dict[data][0](data=metadata_validated_data[data])
                        if data_serializer.is_valid():
                            data_id, _= metadata_static_serializer_model_dict[data][1].objects.get_or_create(**{data+'_name' : data_serializer.validated_data[data+'_name']})
                            setattr(metadata_static_object, data+'_id', data_id)
                    elif data == 'arbitrary_data':
                        metadata_static_object.arbitrary_data = ContentFile(json.dumps(metadata_validated_data['arbitrary_data']), name='arbitrary_data.json')
                    elif data == 'asset_structure':
                        metadata_static_object.asset_structure = ContentFile(json.dumps(metadata_validated_data['asset_structure']), name='asset_structure.json')
                metadata_static_object.save()
    return dataset_object

@shared_task
def copy_dataset(dataset_id, dataset_name, records_validation, user_id, download_id):

    try:
        download = DownloadDataset.objects.get(transfer_id=download_id)
        download.status = 'in_progress'
        download.phase = 'copying'
        download.progress = 0
        download.started_at = timezone.now()
        download.save()

        total_steps = 0
        dataset = Datasets.objects.get(dataset_id=dataset_id)
        assets = Assets.objects.filter(dataset_id=dataset)

        if dataset.metadata_static_id:
            static = dataset.metadata_static_id
            total_steps += int(bool(static.arbitrary_data))
            total_steps += int(bool(static.asset_structure))

        total_steps += int(bool(dataset.label_properties))

        for asset in assets:
            records = Records.objects.filter(asset_id=asset)
            total_steps += records.count()  
            if records_validation:
                
                for record in records:
                    total_steps += Detection.objects.filter(record_id=record).count()
                    total_steps += Segmentation.objects.filter(record_id=record).count()

            if Assets_Metadata_Dynamic.objects.filter(asset_id=asset).exists():
                total_steps += 1 


        total_steps = max(total_steps, 1)
        current_step = 0

        def update_progress():
            download.progress = int((current_step / total_steps) * 100)
            download.save(update_fields=["progress"])

        dataset_copy = {}
        metadata_static_serializer_model_dict = {'device_type_id_id': Device_Type, 'scaling_value_id_id': Scaling_Value, 'arbitrary_data': None, 'asset_structure': None}
        metadata_dynamic_serializer_model_dict = {'localization_id_id': Localization, 'diagnosis_id_id': Diagnosis}
        object_metadata_data_dict = {'species_id_id': Species, 'sex_id_id': Sex, 'age': None, 'weight': None}
        metadata_static_copy = {}

        dataset_original = Datasets.objects.get(dataset_id=dataset_id)
        
        if "_".join(dataset_original.dataset_name.split("_")[1:]) == dataset_name:
            
            dataset_name = "_".join(dataset_original.dataset_name.split("_")[1:]) + '_copy'

        dataset_copy['dataset_name'] = dataset_name
        dataset_copy['access_type'] = {'access_type_name': dataset_original.access_policy_id.access_type_id.access_type_name}

       
        label_properties = dataset_original.label_properties
        if label_properties:
            current_step += 1
            update_progress()
            label_properties.open()
            file_content = label_properties.read()
            label_properties.close()
            dataset_copy['label_properties'] = [ContentFile(file_content, name=label_properties.name.split('/')[-1])]

        metadata_static_data = dataset_original.metadata_static_id
        if metadata_static_data:
            current_step += 1
            update_progress()
            for key in metadata_static_serializer_model_dict.keys():
                if metadata_static_data.__dict__[key]:
                    if key == 'arbitrary_data':
                        f = metadata_static_data.arbitrary_data
                        f.open()
                        metadata_static_copy[key] = json.loads(f.read())
                        f.close()
                    elif key in ('device_type_id_id', 'scaling_value_id_id'):
                        model = metadata_static_serializer_model_dict[key]
                        key_obj = model.objects.get(**{key.replace('_id_id', '_id'): metadata_static_data.__dict__[key]})
                        metadata_static_copy[key.replace('_id', '')] = {key.replace('_id', '') + '_name': getattr(key_obj, key.replace('_id', '') + '_name')}
                    else:
                        metadata_static_copy[key] = metadata_static_data.__dict__[key]

        if metadata_static_copy:
            meta_serializer = MetadataStaticSerializer(data=metadata_static_copy)
            
            if meta_serializer.is_valid():
                dataset_copy['metadata_static'] = meta_serializer.validated_data

        serializer_dataset = DatasetsSerializer(data=dataset_copy)
        if serializer_dataset.is_valid():
            dataset_copy_create = create_dataset(serializer_dataset, user_id, False)
            if records_validation:
                metrics = dataset_original.metrics
                if metrics:
                    metrics.open()
                    metrics_copy = metrics.read()
                    metrics.close()
                    json_metric = json.loads(metrics_copy)
                    dataset_copy_create.metrics = ContentFile(json.dumps(json_metric), name='dataset' + str(dataset_copy_create.dataset_id) + '_metrics.json')
                    dataset_copy_create.save()
 
            for asset in assets:
                asset_copy = {}
                metadata_dynamic_copy = {}
                object_metadata_copy = {}

                metadata_dynamic = Assets_Metadata_Dynamic.objects.filter(asset_id=asset.asset_id).first()
                if metadata_dynamic:
                    current_step += 1
                    update_progress()
                    object_metadata = metadata_dynamic.object_metadata_id
                    if object_metadata:
                        for key in object_metadata_data_dict:
                            val = object_metadata.__dict__.get(key)
                            if val:
                                if key.endswith('_id_id'):
                                    model = object_metadata_data_dict[key]
                                    obj = model.objects.get(**{key.replace('_id_id', '_id'): val})
                                    object_metadata_copy[key.replace('_id', '')] = {key.replace('_id', '') + '_name': getattr(obj, key.replace('_id', '') + '_name')}
                                else:
                                    object_metadata_copy[key] = val

                    for key in metadata_dynamic_serializer_model_dict:
                        val = metadata_dynamic.__dict__.get(key)
                        if val:
                            model = metadata_dynamic_serializer_model_dict[key]
                            obj = model.objects.get(**{key.replace('_id_id', '_id'): val})
                            metadata_dynamic_copy[key.replace('_id', '')] = {key.replace('_id', '') + '_name': getattr(obj, key.replace('_id', '') + '_name')}

                    if object_metadata_copy:
                        object_serializer = ObjectMetadataSerializer(data=object_metadata_copy)
                        if object_serializer.is_valid():
                            metadata_dynamic_copy['object_metadata'] = object_serializer.validated_data

                    if metadata_dynamic_copy:
                        meta_serializer = MetadataDynamicSerializer(data=metadata_dynamic_copy)
                        if meta_serializer.is_valid():
                            asset_copy['metadata_dynamic'] = meta_serializer.validated_data

                asset_copy['asset_name'] = {'asset_name': asset.asset_name, 'dataset_id': dataset_copy_create.dataset_id}
             
                asset_records = Records.objects.filter(asset_id=asset.asset_id)
                for record in asset_records:
                    current_step += 1
                    update_progress()
                    record_links = []
                    f = record.record_link
                    f.open()
                    content = f.read()
                    f.close()
                    name = re.sub(r"^\d+_", "", f.name.split('/')[-1])
                    record_links.append(SimpleUploadedFile(name, content, content_type='image/webp'))
                    asset_copy['record_links'] = record_links
                    
                    masks = list(Segmentation.objects.filter(record_id=record.record_id))
                    bboxes = list(Detection.objects.filter(record_id=record.record_id))

                    asset_serializer = RecordsCopySerializer(data=asset_copy)
                    if asset_serializer.is_valid():
                        records_new = create_asset_copy(asset_serializer.validated_data)[0]
                        
                        if records_validation:
                            metrics = asset.metrics
                            if metrics:
                                metrics.open()
                                metrics_copy = metrics.read()
                                metrics.close()
                                json_metric = json.loads(metrics_copy)
                              
                                asset_copy_metrics = records_new.asset_id
                                asset_copy_metrics.metrics = ContentFile(json.dumps(json_metric), name='asset' + str(asset_copy_metrics.asset_id) + '_metrics.json')
                                asset_copy_metrics.save()
                            for rm in masks + bboxes:
                                current_step += 1
                                update_progress()
                                if rm.record_id_id == record.record_id:
                                    link = rm.record_metadata_dynamic_link
                                    metric_link = rm.metrics
                                    link.open()
                                    
                                    content = link.read()
                                    
                                    link.close()

                                    new_name = records_new.record_link.name.split('/')[-1]
                                    metric_file = None
                                    if metric_link != '' and metric_link is not None:
                                        metric_link.open()
                                        metric_link_content = metric_link.read()
                                        metric_link.close()

                                        json_metric = json.loads(metric_link_content)
                                        metric_file = ContentFile(json.dumps(json_metric), name=new_name.replace('.webp', '.json'))

                                    
                                    if hasattr(rm, 'processing_type_id') and rm.processing_type_id.processing_type == 'Segmentation':
                                        fname = new_name.replace('.webp', '_mask.webp')
                                        file = SimpleUploadedFile(fname, content, content_type='image/webp')
                                        Segmentation.objects.create(record_id=records_new, processing_type_id=rm.processing_type_id, record_metadata_dynamic_link=file, metrics=metric_file)
                                    else:
                                        json_data = json.loads(content)
                                        orig_key = f.name.split('/')[-1].replace('.webp', '')
                                        bbox_list = json_data[orig_key]
                                        for b in bbox_list:
                                            b['image_name'] = new_name
                                        new_json = {new_name.replace('.webp', ''): bbox_list}
                                        f = ContentFile(json.dumps(new_json), name=new_name.replace('.webp', '_bbox.json'))
                                        Detection.objects.create(record_id=records_new, processing_type_id=rm.processing_type_id, record_metadata_dynamic_link=f, metrics=metric_file)

        download.status = 'completed'
        download.progress = 100
        download.finished_at = timezone.now()
        download.save()

    except Exception as e:
        download.status = 'failed'
        download.progress = 0
        download.save()
        raise e


def update_progress(download_obj, percent):
    download_obj.progress = percent
    download_obj.save()


@shared_task(bind=True)
def generate_dataset_archive(self, download_id):
    download = None
    try:
        download = DownloadDataset.objects.get(transfer_id=download_id)
        dataset = download.dataset_id
        download.status = 'in_progress'
        download.phase = 'preparing'
        download.progress = 0
        download.started_at = timezone.now()
        download.save()

        def update_progress(percent, phase=None):
            download.progress = percent
            if phase:
                download.phase = phase
            download.save()

        folder = download_dataset_files(dataset, update_progress=lambda p: update_progress(p, 'preparing'))
        
        update_progress(0, 'zipping')

        temp_dir = tempfile.gettempdir()
        filename = f"{dataset.dataset_name.replace('/', '_')}.zip"
        zip_path = os.path.join(temp_dir, filename)
        
        with zipfile.ZipFile(zip_path, 'w') as archive:
            total_files = sum(len(f) for _, _, f in os.walk(folder))
            download.total_files_expected = total_files
            download.save()
            
            processed = 0
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder)
                    archive.write(file_path, arcname)
                    
                    processed += 1
                    download.files_uploaded = processed
                    progress_percent = int((processed / total_files) * 100) if total_files > 0 else 0
                    update_progress(progress_percent, 'zipping')

        with open(zip_path, 'rb') as f:
            download.archive_file.save(filename, File(f))

        download.status = 'completed'
        download.phase = 'ready'
        download.progress = 100
        download.finished_at = timezone.now()
        download.save()

        shutil.rmtree(folder)
        if os.path.exists(zip_path):
            os.remove(zip_path)

    except Exception as e:
        if download:
            download.status = 'failed'
            download.error_message = str(e)
            download.finished_at = timezone.now()
            download.save()
  
       
        raise e
    


from celery import shared_task
from collections import Counter, defaultdict
import json
from .models import Records, Detection, Segmentation, Assets, Datasets

@shared_task
def update_asset_metrics(asset_id, inference):
    try:
        asset = Assets.objects.get(asset_id=asset_id)
        records = Records.objects.filter(asset_id=asset_id)
        
        asset_metrics = {
            'detection': defaultdict(int),
            'detection_percentage': defaultdict(int),
            'detection_all': int(0),
            'segmentation': {
                'total_square': defaultdict(int),
                'image_counts': defaultdict(int),  
                
            },
            'total_records': records.count(),
      
        }
        
        for record in records:
            record_name = os.path.basename(record.record_link.name.split('.')[0]) 
          
            detections = Detection.objects.filter(record_id=record.record_id)
            for detection in detections:
                metrics_data = None
                needs_save = False
                
                if detection.metrics and not inference:
                    detection.metrics.seek(0)
                    metrics_data = json.load(detection.metrics)
                elif detection.record_metadata_dynamic_link:
                    detection.record_metadata_dynamic_link.seek(0)
                    json_data = json.load(detection.record_metadata_dynamic_link)
                    boxes = next(iter(json_data.values()))
                    metrics_data = Counter(box["label_name"] for box in boxes)
                    
                    metrics_bytes = io.BytesIO()
                    metrics_bytes.write(json.dumps(metrics_data, indent=2).encode('utf-8'))
                    metrics_bytes.seek(0)
                    metrics_filename = f"{record_name}_bbox_metrics.json"
                    detection.metrics.save(metrics_filename, ContentFile(metrics_bytes.read()))
                    needs_save = True
                
                if metrics_data:
                    for label, count in metrics_data.items():
                        asset_metrics['detection'][label] += count
                        asset_metrics['detection_percentage'][label] += 1
                        asset_metrics['detection_all'] += count
                    
                    
                    if needs_save:
                        detection.save()

            segmentations = Segmentation.objects.filter(record_id=record.record_id)
            for segmentation in segmentations:
                metrics_data = None
                needs_save = False
                
                if segmentation.metrics and not inference:
                    segmentation.metrics.seek(0)
                    metrics_data = json.load(segmentation.metrics)
                elif segmentation.record_metadata_dynamic_link:
                    segmentation.record_metadata_dynamic_link.seek(0)
                    original_image = Image.open(segmentation.record_metadata_dynamic_link).convert('RGBA')
                    label_properties_path = record.asset_id.dataset_id.label_properties
                    metrics_data = calculate_segmentation_metrics(original_image, label_properties_path)
                    
                    metrics_bytes = io.BytesIO()
                    metrics_bytes.write(json.dumps(metrics_data, indent=2).encode('utf-8'))
                    metrics_bytes.seek(0)
                    metrics_filename = f"{record_name}_mask_metrics.json"
                    segmentation.metrics.save(metrics_filename, ContentFile(metrics_bytes.read()))
                    needs_save = True
                
                if metrics_data:
                    for label, pixel_count in metrics_data.items():
                        asset_metrics['segmentation']['total_square'][label] += pixel_count
                        asset_metrics['segmentation']['image_counts'][label] += 1
                    
                    
                    
                    if needs_save:
                        segmentation.save()

        for label in asset_metrics['segmentation']['total_square']:
            asset_metrics['segmentation']['total_square'][label] = asset_metrics['segmentation']['total_square'][label] / asset_metrics['total_records']

        for label in asset_metrics['detection_percentage']:
            asset_metrics['detection_percentage'][label] = asset_metrics['detection_percentage'][label] * asset_metrics['detection'][label] / (asset_metrics['total_records']*asset_metrics['detection_all'])
            
        metrics_filename = f"asset_{asset_id}_metrics.json"
        metrics_bytes = io.BytesIO()
        metrics_bytes.write(json.dumps(asset_metrics, indent=2, default=lambda x: dict(x) if isinstance(x, defaultdict) else x).encode('utf-8'))
        metrics_bytes.seek(0)
        
        asset.metrics.save(metrics_filename, ContentFile(metrics_bytes.read()))
        asset.save()
        
        
        
    except Exception as e:
        raise e

@shared_task
def update_dataset_metrics(dataset_id):
    try:
        dataset = Datasets.objects.get(dataset_id=dataset_id)
        assets = Assets.objects.filter(dataset_id=dataset_id)
        
        dataset_metrics = {
            'detection': defaultdict(int),
            
            'detection_percentage': defaultdict(int),
            'detection_all': int(0),
            'segmentation': {
                'total_square': defaultdict(int),
                'image_counts': defaultdict(int),
           
            },
            'total_assets': assets.count(),
            'total_records': 0,
         
        }
        
        total_records_in_dataset = Records.objects.filter(
            asset_id__in=assets.values('asset_id')
        ).count()
        dataset_metrics['total_records'] = total_records_in_dataset
        
        for asset in assets:
            if asset.metrics:
                asset.metrics.seek(0)
                asset_metrics = json.load(asset.metrics)

                for label, count in asset_metrics.get('detection', {}).items():
                    dataset_metrics['detection'][label] += count
                
                    dataset_metrics['detection_percentage'][label] = asset_metrics['detection_percentage'][label] * asset_metrics.get('total_records', 1)/ (dataset_metrics['total_records'])
                
                dataset_metrics['detection_all'] += asset_metrics.get('detection_all', 0)
                
                seg_metrics = asset_metrics.get('segmentation', {})
                for label, pixel_count in seg_metrics.get('total_square', {}).items():
                    dataset_metrics['segmentation']['total_square'][label] += pixel_count * asset_metrics.get('total_records', 1)
                    dataset_metrics['segmentation']['image_counts'][label] += seg_metrics.get('image_counts', {}).get(label, 0)
                
                
        for label in dataset_metrics['segmentation']['total_square']:
            dataset_metrics['segmentation']['total_square'][label] = dataset_metrics['segmentation']['total_square'][label] / dataset_metrics['total_records']
     
            
        metrics_filename = f"dataset_{dataset_id}_metrics.json"
        metrics_bytes = io.BytesIO()
        metrics_bytes.write(json.dumps(dataset_metrics, indent=2, default=lambda x: dict(x) if isinstance(x, defaultdict) else x).encode('utf-8'))
        metrics_bytes.seek(0)
        
        dataset.metrics.save(metrics_filename, ContentFile(metrics_bytes.read()))
        dataset.save()
        
    except Exception as e:
        raise e
    

@shared_task
def recalculate_all_metrics(dataset_id=None, inference=False):
    if dataset_id:
        dataset = Datasets.objects.get(dataset_id=dataset_id)
    
    assets = Assets.objects.filter(dataset_id=dataset.dataset_id)
    
    asset_tasks = [update_asset_metrics.s(asset.asset_id, inference) for asset in assets]
    
    if asset_tasks:
        chain(group(asset_tasks), update_dataset_metrics.si(dataset.dataset_id))()
    else:
        update_dataset_metrics.delay(dataset.dataset_id)


@shared_task
def clean_annotations_after_class_delete(dataset_id, class_name, color):

    clean_detection_after_class_delete.delay(dataset_id, class_name)
    clean_segmentation_after_class_delete.delay(dataset_id, color)

@shared_task
def clean_detection_after_class_delete(dataset_id, class_name):

    try:
        detections = Detection.objects.filter(record_id__asset_id__dataset_id=dataset_id)
        deleted_count = 0
        updated_records = 0
        
        for detection in detections:
            if not detection.record_metadata_dynamic_link:
                continue
                
            try:
                file_content = detection.record_metadata_dynamic_link.read()
                detection.record_metadata_dynamic_link.close()
                annotations = json.loads(file_content)
                
                deleted_count_file = 0
                original_count_file = 0
                filtered_annotations = {}
                
                for image_name, image_annotations in annotations.items():
                    original_count_file += len(image_annotations)
                    filtered_image_annotations = [
                        ann for ann in image_annotations 
                        if ann.get('label_name') != class_name
                    ]
                    deleted_count_file += (len(image_annotations) - len(filtered_image_annotations))
                    filtered_annotations[image_name] = filtered_image_annotations
                
                if deleted_count_file > 0:
                    detection.record_metadata_dynamic_link = ContentFile(
                        json.dumps(filtered_annotations).encode('utf-8'), 
                        name=os.path.basename(detection.record_metadata_dynamic_link.name)
                    )
                    detection.save()
                    deleted_count += deleted_count_file
                    updated_records += 1
                    
            except Exception as e:
                continue
        
        
    except Exception as e:
        raise

@shared_task
def clean_segmentation_after_class_delete(dataset_id, target_color):

    try:
        segmentations = Segmentation.objects.filter(record_id__asset_id__dataset_id=dataset_id)
        
        for segmentation in segmentations:
            if not segmentation.record_metadata_dynamic_link:
                continue
                
            file_content = segmentation.record_metadata_dynamic_link.read()
            segmentation.record_metadata_dynamic_link.close()

            if target_color.startswith('#'):
                target_rgb = np.array([
                    int(target_color[1:3], 16),  
                    int(target_color[3:5], 16),  
                    int(target_color[5:7], 16)   
                ])
            
            img = Image.open(io.BytesIO(file_content))
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
                
            img_array = np.array(img)
            
            color_mask = (
                np.abs(img_array[:, :, 0] - target_rgb[0]) <= 10) & (
                np.abs(img_array[:, :, 1] - target_rgb[1]) <= 10) & (
                np.abs(img_array[:, :, 2] - target_rgb[2]) <= 10)
            
            if not np.any(color_mask):
                
                continue
                

            img_array[color_mask, 3] = 0

            cleaned_img = Image.fromarray(img_array, 'RGBA')
            output = io.BytesIO()
            cleaned_img.save(output, format='WEBP', quality=95)
            
            segmentation.record_metadata_dynamic_link = ContentFile(
                output.getvalue(),
                name=os.path.basename(segmentation.record_metadata_dynamic_link.name)
            )
            segmentation.save()
        
        
    except Exception as e:
        print(e)
        return False
    
@shared_task
def update_annotation_colors(dataset_id, old_color, new_color):

    try:
        segmentations = Segmentation.objects.filter(record_id__asset_id__dataset_id=dataset_id)
        updated_records = 0
        updated_pixels = 0
        
        for segmentation in segmentations:
            if not segmentation.record_metadata_dynamic_link:
                continue
                

            file_content = segmentation.record_metadata_dynamic_link.read()
            segmentation.record_metadata_dynamic_link.close()
            
            if old_color.startswith('#') and new_color.startswith('#'):
                old_rgb = np.array([
                    int(old_color[1:3], 16),  
                    int(old_color[3:5], 16),  
                    int(old_color[5:7], 16)   
                ])
                new_rgb = np.array([
                    int(new_color[1:3], 16), 
                    int(new_color[3:5], 16),  
                    int(new_color[5:7], 16)  
                ])
            
            img = Image.open(io.BytesIO(file_content))
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
                
            img_array = np.array(img)
            
            color_mask = (
                np.abs(img_array[:, :, 0] - old_rgb[0]) <= 10) & (
                np.abs(img_array[:, :, 1] - old_rgb[1]) <= 10) & (
                np.abs(img_array[:, :, 2] - old_rgb[2]) <= 10)
            

            if not np.any(color_mask):
                continue
            
   
            img_array[color_mask, 0] = new_rgb[0]  
            img_array[color_mask, 1] = new_rgb[1] 
            img_array[color_mask, 2] = new_rgb[2]  

            cleaned_img = Image.fromarray(img_array, 'RGBA')
            output = io.BytesIO()
            cleaned_img.save(output, format='WEBP', quality=95)
            
            segmentation.record_metadata_dynamic_link = ContentFile(
                output.getvalue(),
                name=os.path.basename(segmentation.record_metadata_dynamic_link.name)
            )
            segmentation.save()
            
            updated_pixels += np.sum(color_mask)
            updated_records += 1
        
        
    except Exception as e:
    
        return False