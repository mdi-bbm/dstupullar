from ..models import Detection, Sex, DownloadDataset, Segmentation, Users, Access_Types, Status, Users, Roles, Groups, Group_User_Linkage, Access_Policies, Access_Group_Linkage, Device_Type, Scaling_Value, Metadata_Static, Datasets, Assets, Records, Species, Diagnosis, Assets_Metadata_Dynamic, Localization, Object_Metadata, Package
from rest_framework import serializers
import json
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from ..utils import build_full_url
from django.http import QueryDict
from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    class Meta:
        model = Users
        fields = ['user_id', 'username']

class DatasetStatusSerializer(serializers.ModelSerializer):
    dataset_id = serializers.IntegerField(write_only=True)
    class Meta:
        model = Status
        fields = ['status', 'dataset_id']

class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = Users
        fields = ['username', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords must match."})
        
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = Users.objects.create_user(**validated_data)
        return user
    

class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ['role_id', 'role_name']

class GroupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Groups
        fields = ['group_id']

class GroupUserLinkageSerializer(serializers.ModelSerializer):

    role_name = serializers.SlugRelatedField(
        slug_field="role_name",
        queryset=Roles.objects.all(),
        write_only=True
    )
    username = serializers.SlugRelatedField(
        slug_field="username",
        queryset=Users.objects.all(),
        write_only=True
    )
    class Meta:
        model = Group_User_Linkage
        fields = ['group_id', 'username', 'role_name']


class GroupUserLinkageViewSerializer(serializers.ModelSerializer): 
    user_id = serializers.IntegerField(source='user_id.user_id')  
    username = serializers.CharField(source='user_id.username')   
    role = serializers.CharField(source='role_id.role_name')    
    
    class Meta:
        model = Group_User_Linkage
        fields = ['user_id', 'username', 'role']  


class AccessPoliciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Access_Policies
        fields = ['access_policy_id', 'access_type_id']

class AccessGroupLinkageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Access_Group_Linkage
        fields = ['group_id', 'access_policy_id']

class DeviceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device_Type
        fields = ['device_type_id','device_type_name']

class ScalingValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scaling_Value
        fields = ['scaling_value_id', 'scaling_value_name']

class MetadataStaticSerializer(serializers.ModelSerializer):
    device_type = DeviceTypeSerializer(write_only=True, required=False)
    scaling_value = ScalingValueSerializer(write_only=True, required=False)
    arbitrary_data = serializers.DictField(write_only=True, required=False)
    asset_structure = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = Metadata_Static
        fields = ['metadata_static_id','arbitrary_data', 'asset_structure', 'device_type', 'scaling_value', 'scales']

    
class MetadataStaticChangeSerializer(serializers.ModelSerializer):
    device_type = serializers.DictField(write_only=True, required=False)
    scaling_value = serializers.DictField(write_only=True, required=False)
    arbitrary_data = serializers.DictField(write_only=True, required=False)
    asset_structure = serializers.CharField(write_only=True, required=False)
    label_properties = serializers.FileField(write_only=True, required=False)
    scales = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    class Meta:
        model = Metadata_Static
        fields = ['metadata_static_id','arbitrary_data', 'asset_structure', 'device_type', 'scaling_value', 'label_properties', 'scales']

    def to_internal_value(self, data):
        data_copy = data.copy()
        for field in ["device_type", "scaling_value", "scales", "arbitrary_data"]:
            value = data_copy.get(field)
            if isinstance(value, str):
                try:
                    data_copy[field] = json.loads(value)
                except json.JSONDecodeError:
                    raise serializers.ValidationError({field: "Wrong формат"})

        return super().to_internal_value(data_copy.dict())

class AccessTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Access_Types
        fields = ['access_type_name']


class DatasetsSerializer(serializers.ModelSerializer):
    
    access_type = AccessTypesSerializer(write_only=True)
    metadata_static = MetadataStaticSerializer(write_only=True, required=False)
    label_properties = serializers.ListField(child=serializers.FileField()  , write_only=True, required=False)

    class Meta:
        model = Datasets
        fields = ['dataset_id','dataset_name', 'access_type', 'label_properties', 'metadata_static'] 

    def to_internal_value(self, data):
     
        data_copy = data.copy()
        access_type_data = data_copy.get('access_type')
        metadata_static_data = data_copy.get('metadata_static')
        if isinstance(data_copy, QueryDict):
            label_properties_file = data_copy.getlist('label_properties')
        elif isinstance(data_copy, dict):
            label_properties_file = data_copy.get('label_properties')
        
        if isinstance(access_type_data, str):
            try:
                data_copy['access_type'] = json.loads(access_type_data)
            except json.JSONDecodeError:
                raise serializers.ValidationError({'access_type_data': 'Wrong JSON.'})
        if metadata_static_data is not None:
            if isinstance(metadata_static_data, str):
                try:
                    data_copy['metadata_static'] = json.loads(metadata_static_data)
                except json.JSONDecodeError:
                    raise serializers.ValidationError({'metadata_static_data': 'Wrong JSON.'})

        if isinstance(data_copy, QueryDict):
            data_copy = data_copy.dict()
        
        if label_properties_file is not None and len(label_properties_file) > 0:
            data_copy['label_properties'] = label_properties_file
            
       
        return super().to_internal_value(data_copy)

class AssetSerializer(serializers.ModelSerializer):
    records_count = serializers.IntegerField(read_only=True)
    validation_mask_flag = serializers.BooleanField(read_only=True)
    validation_bbox_flag = serializers.BooleanField(read_only=True)
    class Meta:
        model = Assets
        fields = ['asset_id', 'asset_name', 'records_count', 'validation_mask_flag', 'validation_bbox_flag']

class DatasetsReadSerializer(serializers.ModelSerializer):
    last_image = serializers.SerializerMethodField(read_only=True)
    access_type = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField(read_only=True)

    
    class Meta:
        model = Datasets
        fields = ['dataset_id', 'dataset_name', 'metadata_static_id', 'access_policy_id', 'access_type', 'last_image', 'group_id', 'status']


    def get_group_id(self, obj):
        group = Access_Group_Linkage.objects.filter(access_policy_id=obj.access_policy_id).first()
        if group:
            return group.group_id.group_id

    def get_last_image(self, obj):
        last_asset = Assets.objects.filter(dataset_id=obj.dataset_id).order_by("-asset_id").first()
        if last_asset:
            last_image = Records.objects.filter(asset_id=last_asset.asset_id).order_by("-record_id").first()
            if last_image:
                return build_full_url(last_image.record_link)
        return None

    def get_access_type(self, obj):
       
        policy = obj.access_policy_id  
        return policy.access_type_id.access_type_name 

class RecordsInfoSerializer(serializers.ModelSerializer):
    detection_metrics = serializers.SerializerMethodField(read_only=True)
    segmentation_metrics = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Records
        fields = ['record_id' , 'asset_id', 'record_link','validation_mask_flag', 'validation_bbox_flag', 'detection_metrics', 'segmentation_metrics']

    def get_detection_metrics(self, obj):
        try:
            detection = obj.detection
            return build_full_url(detection.metrics) if detection.metrics else None
        except Detection.DoesNotExist:
            return None

    def get_segmentation_metrics(self, obj):
        try:
            segmentation = obj.segmentation
            return build_full_url(segmentation.metrics) if segmentation.metrics else None
        except Segmentation.DoesNotExist:
            return None

class AssetsManagementSerializer(serializers.ModelSerializer):
    
    segmentation_count = serializers.IntegerField(read_only=True)
    detection_count = serializers.IntegerField(read_only=True)
    validation_mask_count = serializers.IntegerField(read_only=True)
    validation_bbox_count = serializers.IntegerField(read_only=True)
    validation_mask_flag = serializers.BooleanField(read_only=True)
    validation_bbox_flag = serializers.BooleanField(read_only=True)
    records_count = serializers.IntegerField(read_only=True)
    metrics = serializers.SerializerMethodField(read_only=True)

    def get_metrics(self, obj):
        try:
            metrics = obj.metrics
            url = build_full_url(metrics) if metrics else None
            return url
        except Assets.DoesNotExist:
            return None
    class Meta:
        model = Assets
        fields = ['asset_id','asset_name', 'segmentation_count', 'detection_count', 'validation_mask_count', 'validation_bbox_count', 'validation_mask_flag', 'validation_bbox_flag', 'records_count', 'metrics']



class DatasetManagementSerializer(serializers.ModelSerializer):
    
    access_type = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField(read_only=True)
    metrics = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Datasets
        fields = ['dataset_id', 'dataset_name', 'metadata_static_id', 'access_policy_id', 'access_type', 'group_id', 'metrics']

    def get_metrics(self, obj):
        try:
            metrics = obj.metrics
            return build_full_url(metrics) if metrics else None
        except Datasets.DoesNotExist:
            return None

    def get_group_id(self, obj):
        group = Access_Group_Linkage.objects.filter(access_policy_id=obj.access_policy_id).first()
        if group:
            return group.group_id.group_id

    def get_access_type(self, obj):
       
        policy = obj.access_policy_id  
        return policy.access_type_id.access_type_name 


class DatasetsCreateSerializer(serializers.ModelSerializer):
    access_type = serializers.PrimaryKeyRelatedField(queryset=Access_Types.objects.all(), write_only=True)
    metadata_static = serializers.JSONField(write_only=True, required=False)
    label_properties = serializers.FileField(write_only=True, required=False)

    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Datasets
        fields = ['dataset_id', 'dataset_name', 'access_type', 'label_properties', 'metadata_static', 'owner']
    
        

class DatasetsViewSerializer(serializers.ModelSerializer):
    last_image = serializers.SerializerMethodField(read_only=True)
    access_type = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField(read_only=True)
    is_admin = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Datasets
        fields = ['dataset_id', 'dataset_name', 'metadata_static_id', 'access_policy_id', 'access_type', 'last_image', 'group_id', 'is_admin']

    def get_is_admin(self, obj):
        user = self.context['request'].user
        group = Access_Group_Linkage.objects.filter(access_policy_id=obj.access_policy_id).first()
        if group:
            is_admin = Group_User_Linkage.objects.filter(group_id=group.group_id, user_id=user, role_id__role_name='Admin').exists()
            return is_admin

    def get_group_id(self, obj):
        group = Access_Group_Linkage.objects.filter(access_policy_id=obj.access_policy_id).first()
        if group:
            return group.group_id.group_id

    def get_last_image(self, obj):
        last_asset = Assets.objects.filter(dataset_id=obj.dataset_id).order_by("-asset_id").first()
        if last_asset:
            last_image = Records.objects.filter(asset_id=last_asset.asset_id).order_by("-record_id").first()
            if last_image:
                return build_full_url(last_image.record_link)
        return None

    def get_access_type(self, obj):
       
        policy = obj.access_policy_id  
        return policy.access_type_id.access_type_name 
   
class AssetsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Assets
        fields = ['asset_id', 'asset_name', 'dataset_id']


class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Species
        fields = ['species_id', 'species_name']

class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ['diagnosis_id', 'diagnosis_name']

class LocalizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Localization
        fields = ['localization_id', 'localization_name']

class SexSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sex
        fields = ['sex_id', 'sex_name']

class ObjectMetadataSerializer(serializers.ModelSerializer):
    species = SpeciesSerializer(write_only=True, required=False)
    sex =  SexSerializer(write_only=True, required=False)
    class Meta:
        model = Object_Metadata
        fields = ['object_metadata_id', 'species', 'age', 'weight', 'sex']

class MetadataDynamicSerializer(serializers.ModelSerializer):
    
    diagnosis = DiagnosisSerializer(write_only=True, required=False)
    localization = LocalizationSerializer(write_only=True, required=False)
    object_metadata = ObjectMetadataSerializer(write_only=True, required=False)
    arbitrary_data_json_link = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = Assets_Metadata_Dynamic
        fields = ['asset_metadata_dynamic_id', 'diagnosis',  'localization',  'object_metadata', 'arbitrary_data_json_link']


class RecordsCopySerializer(serializers.ModelSerializer):
    
    asset_name = AssetsSerializer(write_only=True)
    record_links = serializers.ListField(child=serializers.FileField(), write_only=True)
    metadata_dynamic = MetadataDynamicSerializer(write_only=True, required=False)

    class Meta:
        model = Records
        fields = ['record_id','record_links', 'asset_name' , 'metadata_dynamic']
        
    def to_internal_value(self, data):
        
        if isinstance(data, QueryDict):
            file_type = data.getlist('record_links')[0]
            
            if isinstance(file_type, InMemoryUploadedFile):
                data_copy = data.copy()
    
            elif isinstance(file_type, TemporaryUploadedFile):
                data_copy = data
            
            asset_metadata_dynamic = data_copy.get('metadata_dynamic')
            asset_name = data_copy.get('asset_name')
            record_links = data_copy.getlist('record_links')
            if asset_metadata_dynamic is not None:  
                if isinstance(asset_metadata_dynamic, str):
                    try:
                        asset_metadata_dynamic = json.loads(asset_metadata_dynamic)
                        object_metadata = asset_metadata_dynamic.get('object_metadata')
                        if object_metadata is not None:
                            if isinstance(object_metadata, str):
                                try:
                                    object_metadata = json.loads(object_metadata)
                                    asset_metadata_dynamic['object_metadata'] = object_metadata
                                except json.JSONDecodeError:
                                    raise serializers.ValidationError({'object_metadata': 'Wrong JSON.'})
                        data_copy['metadata_dynamic'] = asset_metadata_dynamic
                    except json.JSONDecodeError:
                        raise serializers.ValidationError({'asset_metadata_dynamic': 'Wrong JSON.'})
                    
            if isinstance(asset_name, str):
                try:
                    asset_name = json.loads(asset_name)
                    data_copy['asset_name'] = asset_name
                except json.JSONDecodeError:    
                    raise serializers.ValidationError({'asset_name': 'Wrong JSON.'})
            data_copy = data_copy.dict()
            data_copy['record_links'] = record_links
        elif isinstance(data, dict):
            data_copy = data
        
        return super().to_internal_value(data_copy)

class AssetRecordsSerializer(serializers.ModelSerializer):
    detection_link = serializers.SerializerMethodField()
    segmentation_link = serializers.SerializerMethodField()
    record_link = serializers.SerializerMethodField()
    
    class Meta:
        model = Records
        fields = ['record_id', 'record_link', 'detection_link', 'segmentation_link', 'validation_mask_flag', 'validation_bbox_flag']

    def get_record_link(self, obj):
        return build_full_url(obj.record_link) if obj.record_link else None

    def get_detection_link(self, obj):
        try:
            detection_link = obj.detection
            return build_full_url(detection_link.record_metadata_dynamic_link) if detection_link.record_metadata_dynamic_link else None
        except Detection.DoesNotExist:
            return None
      

    def get_segmentation_link(self, obj): 
        try:
            segmentation_link = obj.segmentation
            return build_full_url(segmentation_link.record_metadata_dynamic_link) if segmentation_link.record_metadata_dynamic_link else None
        except Segmentation.DoesNotExist:
            return None

class RecordsSerializer(serializers.ModelSerializer):
    download_id = serializers.IntegerField(write_only=True, required=False)
    asset_name = AssetsSerializer(write_only=True)
    record_links = serializers.ListField(child=serializers.CharField(), write_only=True)
    metadata_dynamic = MetadataDynamicSerializer(write_only=True, required=False)

    class Meta:
        model = Records
        fields = ['record_id','record_links', 'asset_name' , 'metadata_dynamic', 'download_id']
        
    def to_internal_value(self, data):
        
        if isinstance(data, QueryDict):
            file_type = data.getlist('record_links')[0]
            
            if isinstance(file_type, InMemoryUploadedFile):
                data_copy = data.copy()
    
            elif isinstance(file_type, TemporaryUploadedFile):
                data_copy = data
            else:
                data_copy = data.copy() 
            
            asset_metadata_dynamic = data_copy.get('metadata_dynamic')
            asset_name = data_copy.get('asset_name')
            record_links = data_copy.getlist('record_links')
            if asset_metadata_dynamic is not None:  
                if isinstance(asset_metadata_dynamic, str):
                    try:
                        asset_metadata_dynamic = json.loads(asset_metadata_dynamic)
                        object_metadata = asset_metadata_dynamic.get('object_metadata')
                        if object_metadata is not None:
                            if isinstance(object_metadata, str):
                                try:
                                    object_metadata = json.loads(object_metadata)
                                    asset_metadata_dynamic['object_metadata'] = object_metadata
                                except json.JSONDecodeError:
                                    raise serializers.ValidationError({'object_metadata': 'Wrong JSON.'})
                        data_copy['metadata_dynamic'] = asset_metadata_dynamic
                    except json.JSONDecodeError:
                        raise serializers.ValidationError({'asset_metadata_dynamic': 'Wrong JSON.'})
                    
            if isinstance(asset_name, str):
                try:
                    asset_name = json.loads(asset_name)
                    data_copy['asset_name'] = asset_name
                except json.JSONDecodeError:    
                    raise serializers.ValidationError({'asset_name': 'Wrong JSON.'})
            data_copy = data_copy.dict()
            data_copy['record_links'] = json.loads(record_links[0])
            
        elif isinstance(data, dict):
            data_copy = data

        return super().to_internal_value(data_copy)
    
class StartResumableUploadSerializer(serializers.Serializer):
    dataset_id = serializers.PrimaryKeyRelatedField(queryset=Datasets.objects.all(), write_only=True)
    total_chunks_expected = serializers.IntegerField(write_only=True)
    class Meta:
 
        fields = ['dataset_id', 'total_chunks_expected']

class MasksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Segmentation
        fields = ['mask_id', 'mask_link']

class BoundingBoxesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detection
        fields = ['bbox_id', 'bbox_link']

class RecordsViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Records
        fields = ['__all__']

class RecordIDViewSerializer(serializers.ModelSerializer):
    asset_name = serializers.SerializerMethodField() 
    mask_link = serializers.SerializerMethodField(read_only=True)
    bbox_link = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Records
        fields = ['record_id','record_link', 'asset_id', 'asset_name', 'mask_link', 'bbox_link', 'validation_mask_flag', 'validation_bbox_flag']
      
        
    
    def get_asset_name(self, obj):
        return obj.asset_id.asset_name 
    

    def get_mask_link(self, obj):
        
        try:
            
            mask = Segmentation.objects.get(record_id = obj.record_id)
            
            return build_full_url(mask.record_metadata_dynamic_link)
        except Segmentation.DoesNotExist:
            return None
        
    def get_bbox_link(self, obj):

        try:
            
            bbox = Detection.objects.get(record_id = obj.record_id)

            return build_full_url(bbox.record_metadata_dynamic_link)
        except Detection.DoesNotExist:
            return None

class AnnotationRecordSerializer(serializers.Serializer):
    
    processing_type = serializers.CharField(write_only=True)
    record_metadata_link = serializers.FileField(write_only=True)
    class Meta:
        fields = ['record_metadata_link', 'processing_type']

class DownloadDatasetSerializer(serializers.ModelSerializer):
    dataset_name = serializers.CharField(source='dataset_id.dataset_name', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = DownloadDataset
        fields = [
            'transfer_id',
            'dataset_name',
            'status',
            'phase',
            'progress',
            'files_uploaded',
            'total_files_expected',
            'created_at',
            'started_at',
            'finished_at',
            'download_url',
            'error_message'
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        if obj.archive_file and obj.status == 'completed':
            return obj.archive_file.url
        return None

class ProcessedFilesViewSerializer(serializers.ModelSerializer):
    images = serializers.DictField(child=serializers.FileField(), write_only=True)
    mode = serializers.CharField(write_only=True)
    package_id = serializers.IntegerField(write_only=True)
    class Meta:
        model = Records
        fields = ['images', 'mode', 'package_id']
    
    def to_internal_value(self, data):

        images = {} 
        data_dict = {}
        for d in data:
            if d!='mode' and d!='package_id':
                images[d] = data[d]

        
        data_dict['images'] = images
        data_dict['mode'] = data['mode']
        data_dict['package_id'] = data['package_id']
        data = data_dict

        return super().to_internal_value(data)
      
class PackageSerializer(serializers.ModelSerializer):
    dataset_id = serializers.PrimaryKeyRelatedField(queryset=Datasets.objects.all(), required=False) 
    class Meta:
        model = Package
        fields = ['package_id', 'mode', 'package' , 'package_status', 'user_id', 'task', 'label_properties', 'dataset_id']
        read_only_fields = ['package', 'package_status', 'user_id', 'label_properties']

class PackageStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = Package
        fields = ['package_id', 'package_status']
        
class BatchUploadMetadataDynamicSerializer(serializers.ModelSerializer):
    
    diagnosis = DiagnosisSerializer(write_only=True, required=False)
    localization = LocalizationSerializer(write_only=True, required=False)
    object_metadata = ObjectMetadataSerializer(write_only=True, required=False)
    arbitrary_data_json_link = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = Assets_Metadata_Dynamic
        fields = ['asset_metadata_dynamic_id', 'diagnosis',  'localization',  'object_metadata', 'arbitrary_data_json_link']
   
class BatchUploadSerializer(serializers.Serializer):
   
    dataset = DatasetsSerializer(write_only=True)
    asset_names = serializers.ListField(child=serializers.CharField(max_length=255), write_only=True)
    record_links = serializers.DictField(child=serializers.ListField(child=serializers.FileField()), write_only=True, required=False)
    metadata_links = serializers.DictField(child=serializers.ListField(child=serializers.FileField()), write_only=True, required=False)
    metadata_dynamic = serializers.ListField(child = serializers.DictField(child=BatchUploadMetadataDynamicSerializer()), write_only=True, required=False)
    class Meta:
        fields = ['dataset', 'asset_names', 'record_links', 'metadata_links', 'metadata_dynamic', 'processing_type']

    def to_internal_value(self, data):
        record_links = {} 
        metadata_links = {}
        label_properties = []
        data_dict = {}
        for d in data.keys():
            
            if d!='dataset' and d!='asset_names' and d!='processing_type' and d!='metadata_dynamic': 
                asset = data.getlist(d)
                
                for record in asset:
                    
                    if record.name.endswith('.json') or record.name.endswith('_mask.webp'):
                        
                        metadata_links.setdefault(d , []).append(record)
                    elif d == 'label_properties':
                        label_properties.append(record)
                    else:
                       
                        record_links.setdefault(d , []).append(record)
       
        dataset = json.loads(data['dataset'])
      
        if label_properties != []:
            dataset['label_properties'] = label_properties
        data_dict['record_links'] = record_links
        if metadata_links != {}:
            data_dict['metadata_links'] = metadata_links
        data_dict['dataset'] = dataset
        data_dict['asset_names'] = data.getlist('asset_names')
        if data.get('metadata_dynamic') is not None:
            data_dict['metadata_dynamic'] = json.loads(data['metadata_dynamic'])
       
        data = data_dict
        return super().to_internal_value(data)
    
class DatasetTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datasets
        fields = ['dataset_name', 'label_properties']

class MetadataStaticTablesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Metadata_Static
        fields = ['asset_structure', 'scales']

class DeviceTypeTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device_Type
        fields = ['device_type_name']

class ScalingValueTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scaling_Value
        fields = ['scaling_value_name']


class ValidationSerializer(serializers.Serializer):
    mode = serializers.CharField(write_only=True)
    validation_flag = serializers.BooleanField(write_only=True, required=False)
    class Meta:
        fields = ['mode', 'validation_flag']


class RecordsValidationSerializer(serializers.Serializer):
    validation_all_flag = serializers.BooleanField(write_only=True)
    mode = serializers.CharField(write_only=True)
    dataset_id = serializers.PrimaryKeyRelatedField(queryset=Datasets.objects.all(), write_only=True)
    class Meta:
        fields = ['validation_all_flag', 'mode', 'dataset_id']


class AssetsMetadataDynamicTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assets_Metadata_Dynamic
        fields = ['asset_id', 'localization_id', 'diagnosis_id', 'object_metadata_id']

class SpeciesTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Species
        fields = ['species_name']

class DiagnosisTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ['diagnosis_name']

class LocalizationTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Localization
        fields = ['localization_name']

class ObjectMetadataTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Object_Metadata
        fields = ['age', 'weight']


class SexTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sex
        fields = ['sex_name']


class CopyDatasetSerializer(serializers.Serializer):
    
    dataset_name = serializers.CharField(write_only=True)
    records_validation = serializers.BooleanField(write_only=True)
    class Meta:
        fields = ['dataset_id', 'dataset_name', 'records_validation']

class LabelPropertiesSerializer(serializers.Serializer):
    label_properties = serializers.JSONField(write_only=True)
    class Meta:
        fields = ['label_properties']

   
class DescriptionRecordSerializer(serializers.Serializer):
    mode = serializers.CharField(write_only=True)
    description = serializers.JSONField(write_only=True)
    class Meta:
        fields = ['mode', 'description']


class LabelFavoritesSerializer(serializers.Serializer):
    label_name = serializers.CharField(write_only=True)
    dataset_id = serializers.PrimaryKeyRelatedField(queryset=Datasets.objects.all(), write_only=True)
    class Meta:
        fields = ['label_name', 'dataset_id']
