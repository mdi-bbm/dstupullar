import requests
from .models import Bounding_Boxes, Color, Sex, Masks, Users, Access_Types, Status, Users, Roles, Groups, Group_User_Linkage, Access_Policies, Access_Group_Linkage, Device_Type, Scaling_Value, Metadata_Static, Datasets, Assets, Records, Species, Diagnosis, Assets_Metadata_Dynamic, Localization, Object_Metadata, Package
from rest_framework import serializers
import json
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from .utils import build_full_url

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
       
        token['user_id'] = user.user_id
        return token

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = self.token_backend.decode(attrs['refresh'], verify=True)
        user_id = refresh.get('user_id')
        data['user_id'] = user_id if user_id else getattr(self.user, 'user_id', None)
        return data

class UserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    class Meta:
        model = Users
        fields = ['user_id', 'username']









from rest_framework import serializers
from rest_framework.fields import HiddenField, CurrentUserDefault

class StatusSerializer(serializers.ModelSerializer):
    user = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = Status
        fields = ['status', 'user']

    def update(self, instance, validated_data):
        instance.status = validated_data['status']
        instance.save()
        return instance

class StatusPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ['status']




from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

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
        
        # Проверка на минимальную длину и другие правила
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
    # role_name = serializers.CharField(write_only=True)
    # username = serializers.CharField(write_only=True)
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

    user_name = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()

    class Meta:
        model = Group_User_Linkage
        fields = ['group_id', 'user_name', 'role_name']

    def get_user_name(self, obj):
 
        return obj.user_id.username
    
    def get_role_name(self, obj):
       
        return obj.role_id.role_name


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
        fields = ['metadata_static_id','arbitrary_data', 'asset_structure', 'device_type', 'scaling_value']

    def to_internal_value(self, data):
        
        print(data)
        
        return super().to_internal_value(data)
    
class MetadataStaticChangeSerializer(serializers.ModelSerializer):
    device_type = DeviceTypeSerializer(write_only=True, required=False)
    scaling_value = ScalingValueSerializer(write_only=True, required=False)
    arbitrary_data = serializers.DictField(write_only=True, required=False)
    asset_structure = serializers.CharField(write_only=True, required=False)
    label_properties = serializers.FileField(write_only=True, required=False)
    micrometrs_on_pixel_file = serializers.FileField(write_only=True, required=False)
    class Meta:
        model = Metadata_Static
        fields = ['metadata_static_id','arbitrary_data', 'asset_structure', 'device_type', 'scaling_value', 'label_properties', 'micrometrs_on_pixel_file']

    def to_internal_value(self, data):
        data_copy = data.copy()
        arbitrary_data = data_copy.get('arbitrary_data')
        if arbitrary_data is not None:
            if isinstance(arbitrary_data, str):
                try:
                    data_copy['arbitrary_data'] = json.loads(arbitrary_data)
                    print(data_copy['arbitrary_data'])
                except json.JSONDecodeError:
                    raise serializers.ValidationError({'arbitrary_data': 'Неверный формат JSON.'})
        print(data_copy)
        
        return super().to_internal_value(data_copy)

class AccessTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Access_Types
        fields = ['access_type_name']


from django.http import QueryDict
class DatasetsSerializer(serializers.ModelSerializer):
    
    access_type = AccessTypesSerializer(write_only=True)
    metadata_static = MetadataStaticSerializer(write_only=True, required=False)
    label_properties = serializers.ListField(child=serializers.FileField()  , write_only=True, required=False)

    class Meta:
        model = Datasets
        fields = ['dataset_id','dataset_name', 'access_type', 'label_properties', 'metadata_static']
        
# class DatasetsSerializer(serializers.ModelSerializer):
    
#     access_type = AccessTypesSerializer(write_only=True)
#     metadata_static = MetadataStaticSerializer(write_only=True, required=False)
#     label_properties = serializers.ListField(child=serializers.FileField()  , write_only=True, required=False)

#     class Meta:
#         model = Datasets
#         fields = ['dataset_id','dataset_name', 'access_type', 'label_properties', 'metadata_static'] 

#     def to_internal_value(self, data):
     
#         data_copy = data.copy()
#         access_type_data = data_copy.get('access_type')
#         metadata_static_data = data_copy.get('metadata_static')
#         if isinstance(data_copy, QueryDict):
#             label_properties_file = data_copy.getlist('label_properties')
#         elif isinstance(data_copy, dict):
#             label_properties_file = data_copy.get('label_properties')
        
#         if isinstance(access_type_data, str):
#             try:
#                 data_copy['access_type'] = json.loads(access_type_data)
#             except json.JSONDecodeError:
#                 raise serializers.ValidationError({'access_type_data': 'Неверный формат JSON.'})
#         if metadata_static_data is not None:
#             if isinstance(metadata_static_data, str):
#                 try:
#                     data_copy['metadata_static'] = json.loads(metadata_static_data)
#                 except json.JSONDecodeError:
#                     raise serializers.ValidationError({'metadata_static_data': 'Неверный формат JSON.'})

#         if isinstance(data_copy, QueryDict):
#             data_copy = data_copy.dict()
        
#         if label_properties_file is not None and len(label_properties_file) > 0:
#             data_copy['label_properties'] = label_properties_file
            
       
#         return super().to_internal_value(data_copy)

    
# class DatasetsReadSerializer(serializers.ModelSerializer):
#     access_type = serializers.StringRelatedField()  # красиво отображаем access_type
#     metadata_static = MetadataStaticSerializer(read_only=True)
#     owner = serializers.StringRelatedField()  # username текущего пользователя

#     class Meta:
#         model = Datasets
#         fields = ['dataset_id', 'dataset_name', 'access_type', 'label_properties', 'metadata_static', 'owner']

# Сериализатор для создания/изменения
class DatasetsCreateSerializer(serializers.ModelSerializer):
    access_type = serializers.PrimaryKeyRelatedField(queryset=Access_Types.objects.all(), write_only=True)
    metadata_static = MetadataStaticSerializer(write_only=True, required=False)
    label_properties = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Datasets
        fields = ['dataset_id', 'dataset_name', 'access_type', 'label_properties', 'metadata_static', 'owner']
    
        

class DatasetsReadSerializer(serializers.ModelSerializer):
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
                                    raise serializers.ValidationError({'object_metadata': 'РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ JSON.'})
                        data_copy['metadata_dynamic'] = asset_metadata_dynamic
                    except json.JSONDecodeError:
                        raise serializers.ValidationError({'asset_metadata_dynamic': 'РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ JSON.'})
            if isinstance(asset_name, str):
                try:
                    asset_name = json.loads(asset_name)
                    data_copy['asset_name'] = asset_name
                except json.JSONDecodeError:    
                    raise serializers.ValidationError({'asset_name': 'РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ JSON.'})
            data_copy = data_copy.dict()
            data_copy['record_links'] = record_links
        elif isinstance(data, dict):
            data_copy = data
        
        return super().to_internal_value(data_copy)


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
            # upload_id = data_copy.get('upload_id')
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
                                    raise serializers.ValidationError({'object_metadata': 'Неверный формат JSON.'})
                        data_copy['metadata_dynamic'] = asset_metadata_dynamic
                    except json.JSONDecodeError:
                        raise serializers.ValidationError({'asset_metadata_dynamic': 'Неверный формат JSON.'})
            if isinstance(asset_name, str):
                try:
                    asset_name = json.loads(asset_name)
                    data_copy['asset_name'] = asset_name
                except json.JSONDecodeError:    
                    raise serializers.ValidationError({'asset_name': 'Неверный формат JSON.'})
            data_copy = data_copy.dict()
            data_copy['record_links'] = json.loads(record_links[0])
            # data_copy['upload_id'] = upload_id
        elif isinstance(data, dict):
            data_copy = data
        print(data_copy)
        return super().to_internal_value(data_copy)
    
class StartResumableUploadSerializer(serializers.Serializer):
    dataset_id = serializers.PrimaryKeyRelatedField(queryset=Datasets.objects.all(), write_only=True)
    total_chunks_expected = serializers.IntegerField(write_only=True)
    class Meta:
 
        fields = ['dataset_id', 'total_chunks_expected']


class MasksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Masks
        fields = ['mask_id', 'mask_link']

class BoundingBoxesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bounding_Boxes
        fields = ['bbox_id', 'bbox_link']

from urllib.parse import urlparse, urlunparse
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
            
            mask = Masks.objects.get(record_id = obj.record_id)
            
            return build_full_url(mask.record_metadata_dynamic_link)
        except Masks.DoesNotExist:
            return None
        
    def get_bbox_link(self, obj):

        try:
            
            bbox = Bounding_Boxes.objects.get(record_id = obj.record_id)

            return build_full_url(bbox.record_metadata_dynamic_link)
        except Bounding_Boxes.DoesNotExist:
            return None

class ProcessedRecordSerializer(serializers.Serializer):
    
    record_id = serializers.PrimaryKeyRelatedField(queryset=Records.objects.all(),
        write_only=True)
    processing_type = serializers.CharField(write_only=True)
    record_link = serializers.FileField(write_only=True)
    class Meta:
        fields = ['record_link', 'record_id', 'processing_type']

    def to_internal_value(self, data):
        print(data)
        
        return super().to_internal_value(data)

class ProcessedFilesViewSerializer(serializers.ModelSerializer):
    images = serializers.DictField(child=serializers.FileField(), write_only=True)
    mode = serializers.CharField(write_only=True)
    user_id = serializers.CharField(write_only=True)
    class Meta:
        model = Records
        fields = ['images', 'mode', 'user_id']
    
    def to_internal_value(self, data):

        images = {} 
        data_dict = {}
        for d in data:
            if d!='mode' and d!='user_id':
                images[d] = data[d]

        
        data_dict['images'] = images
        data_dict['mode'] = data['mode']
        data_dict['user_id'] = data['user_id']
        data = data_dict
        print(data)

        return super().to_internal_value(data)
      
class PackageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Package
        fields = ['package_id', 'mode', 'package' , 'package_status', 'user_id', 'task', 'dataset_id', 'label_properties']
        read_only_fields = ['package', 'package_status', 'user_id']

    def to_internal_value(self, data):
        print(data)
        return super().to_internal_value(data)

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
        print(data)
     
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
        print(data)
        return super().to_internal_value(data)
    
class DatasetTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datasets
        fields = ['dataset_name', 'label_properties']

class MetadataStaticTablesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Metadata_Static
        fields = ['asset_structure']

class DeviceTypeTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device_Type
        fields = ['device_type_name']

class ScalingValueTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scaling_Value
        fields = ['scaling_value_name']


class ValidationFlagSerializer(serializers.Serializer):
    mode = serializers.CharField(write_only=True)
    
    class Meta:
        fields = ['mode']


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

    def to_internal_value(self, data):
        print(data)
        
        return super().to_internal_value(data)


class LabelPropertiesSerializer(serializers.Serializer):
    dataset_id = serializers.PrimaryKeyRelatedField(queryset=Datasets.objects.all(), write_only=True)
    label_properties = serializers.FileField(write_only=True)
    label_name = serializers.CharField(write_only=True, required=False)
    label_color = serializers.CharField(write_only=True, required=False)
    old_color = serializers.CharField(write_only=True, required=False)
    record_id = serializers.PrimaryKeyRelatedField(queryset=Records.objects.all(), write_only=True, required=False)
    class Meta:
        fields = ['label_properties', 'dataset_id', 'label_name', 'label_color', 'old_color', 'record_id']

    def to_internal_value(self, data):
        print(data)
        
        return super().to_internal_value(data)

   
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
