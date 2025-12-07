import os

def record_file_path(instance, filename):
    dataset_name = instance.asset_id.dataset_id.dataset_name
    asset_name = instance.asset_id.asset_name
    
    return os.path.join(
        dataset_name,
        asset_name,
        'Raw',
        filename
    )

