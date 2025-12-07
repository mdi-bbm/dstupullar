import json
import tempfile
import os
import numpy as np
import requests
from network.models import Assets, Records, Segmentation, Detection, Assets_Metadata_Dynamic
from urllib.parse import urljoin
from django.conf import settings
import os
from django.core.files.storage import FileSystemStorage
from django.core.files.storage import default_storage

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
def build_full_url(file_field, package=False):
    if not file_field:
        return None

    url = file_field.url  

    if url.startswith('https'):
        return url

    return urljoin(settings.BASE_URL, url)


def download_dataset_files(dataset, update_progress=None):
    temp_dir = tempfile.mkdtemp(prefix=f'{dataset.dataset_name.replace("/", "_")}_')

    total_steps = 0
    assets = Assets.objects.filter(dataset_id=dataset)


    if dataset.metadata_static_id:
        static = dataset.metadata_static_id
        total_steps += int(bool(static.arbitrary_data))
        total_steps += int(bool(static.asset_structure))

    total_steps += int(bool(dataset.label_properties))


    for asset in assets:
        records = Records.objects.filter(asset_id=asset)
        total_steps += records.count()  

        for record in records:
            total_steps += Detection.objects.filter(record_id=record).count()
            total_steps += Segmentation.objects.filter(record_id=record).count()

        if Assets_Metadata_Dynamic.objects.filter(asset_id=asset).exists():
            total_steps += 1  


    total_steps = max(total_steps, 1)
    current_step = 0

    def step():
        nonlocal current_step
        current_step += 1
        if update_progress:
            progress = int((current_step / total_steps) * 100) 
            update_progress(progress)




    metadata_static_dir = os.path.join(temp_dir, 'Metadata_Static')
    label_properties_dir = os.path.join(temp_dir, 'Label_Properties')
    os.makedirs(metadata_static_dir, exist_ok=True)
    os.makedirs(label_properties_dir, exist_ok=True)


    if dataset.metadata_static_id:
        static = dataset.metadata_static_id
        if static.arbitrary_data:
            _copy_file(build_full_url(static.arbitrary_data), metadata_static_dir)
            step()
        if static.asset_structure:
            _copy_file(build_full_url(static.asset_structure), metadata_static_dir)
            step()
        metadata_json_path = os.path.join(metadata_static_dir, 'metadata_static.json')
        with open(metadata_json_path, 'w') as f:
            json.dump({
                "device_type": static.device_type_id.device_type_name if static.device_type_id else None,
                "scaling_value": static.scaling_value_id.scaling_value_name if static.scaling_value_id else None,
            }, f, indent=2)


    if dataset.label_properties:
        _copy_file(build_full_url(dataset.label_properties), label_properties_dir)
        step()

 
    for asset in assets:
        asset_dir = os.path.join(temp_dir, asset.asset_name or f'asset_{asset.asset_id}')
        os.makedirs(asset_dir, exist_ok=True)

     
        raw_dir = os.path.join(asset_dir, 'Raw')
        os.makedirs(raw_dir, exist_ok=True)
        records = Records.objects.filter(asset_id=asset)
        for record in records:
            if record.record_link:
                _copy_file(build_full_url(record.record_link), raw_dir)
                step()

       
            for cls, subdir in [(Detection, 'Detection'), (Segmentation, 'Segmentation')]:
                meta = cls.objects.filter(record_id=record)
                if meta.exists():
                    target_dir = os.path.join(asset_dir, subdir)
                    os.makedirs(target_dir, exist_ok=True)
                    for m in meta:
                        if m.record_metadata_dynamic_link:
                            _copy_file(build_full_url(m.record_metadata_dynamic_link), target_dir)
                            step()


        dynamic_meta = Assets_Metadata_Dynamic.objects.filter(asset_id=asset).first()
        if dynamic_meta:
            arb_dir = os.path.join(asset_dir, 'Arbitrary_Metadata')
            os.makedirs(arb_dir, exist_ok=True)
            if dynamic_meta.arbitrary_data_json_link:
                _copy_file(build_full_url(dynamic_meta.arbitrary_data_json_link), arb_dir)
                step()

            asset_metadata_path = os.path.join(asset_dir, 'asset_metadata.json')
            obj = dynamic_meta.object_metadata_id
            metadata_dict = {
                "species": obj.species_id.species_name if obj and obj.species_id else None,
                "age": obj.age if obj else None,
                "weight": obj.weight if obj else None,
                "sex": obj.sex_id.sex_name if obj and obj.sex_id else None,
                "localization": dynamic_meta.localization_id.localization_name if dynamic_meta.localization_id else None,
                "diagnosis": dynamic_meta.diagnosis_id.diagnosis_name if dynamic_meta.diagnosis_id else None
            }
            with open(asset_metadata_path, 'w') as f:
                json.dump(metadata_dict, f, indent=2)

    return temp_dir

def _copy_file(url, dest_dir):
    filename = os.path.basename(url.split('?')[0])
    save_path = os.path.join(dest_dir, filename)
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(f"Error {url}: {e}")

def remove_empty_dirs(file_field):
    storage = file_field.storage
    if not isinstance(storage, FileSystemStorage):
        return

    try:
        path = file_field.path  
        _remove_upwards(path)
    except Exception as e:
        print(f"[remove_empty_dirs] Error: {e}")


def _remove_upwards(path):
    dir_path = os.path.dirname(path)

    if not os.path.isdir(dir_path):
        return

    try:
        os.rmdir(dir_path)
        _remove_upwards(dir_path)
    except OSError:
        pass  

def remove_empty_dirs_for_asset(asset_name: str):
    storage = default_storage

    if not isinstance(storage, FileSystemStorage):
        return

    asset_root = os.path.join(settings.MEDIA_ROOT, asset_name)
    if os.path.isdir(asset_root):
        remove_empty_dirs(asset_root)


def notify_dataset_status_change(dataset_id, status, message=""):
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        f'dataset_{dataset_id}',
        {
            'type': 'status_update',
            'dataset_id': dataset_id,
            'status': status,
            'message': message
        }
    )

def hex_to_rgb_lable(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

def calculate_segmentation_metrics(mask_image, label_properties_path):
    label_properties = json.load(label_properties_path)
    class_rgb_map = {k: hex_to_rgb_lable(v) for k, v in label_properties.items()}

    mask_array = np.array(mask_image)

    total_pixels = mask_array.shape[0] * mask_array.shape[1]
    if total_pixels == 0:
        return {}
    
    metrics = {}

    for class_name, target_rgb in class_rgb_map.items():
            match_mask = np.all(np.abs(mask_array[:, :, :3] - target_rgb) <= 10, axis=-1)
            match_count = int(np.sum(match_mask))
            
            if match_count > 0:
                metrics[class_name] = round((match_count / total_pixels) * 100, 2)

    return metrics