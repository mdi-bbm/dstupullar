
import json
import io
import os
from django.core.files.base import ContentFile
from django.db.models import Count, Q, Case, When, Value, BooleanField
from collections import Counter
from django.db import transaction
from django.utils import timezone
from celery import group
import requests
from .utils import build_full_url, notify_dataset_status_change, calculate_segmentation_metrics
from PIL import Image
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import permissions, generics, viewsets, status
from rest_framework.views import APIView
from .serializers import UserSerializer, RegisterSerializer, DatasetsCreateSerializer, DatasetsReadSerializer, PackageStatusSerializer, DatasetStatusSerializer, PackageSerializer, DatasetManagementSerializer, ValidationSerializer,RecordsInfoSerializer, AssetsManagementSerializer, AssetSerializer, AssetRecordsSerializer, AnnotationRecordSerializer 
from .serializers import AccessTypesSerializer, MetadataStaticTablesSerializer, DatasetTablesSerializer, LabelPropertiesSerializer, CopyDatasetSerializer, ProcessedFilesViewSerializer,DownloadDatasetSerializer, SpeciesTablesSerializer,LocalizationTablesSerializer, DiagnosisTablesSerializer,SexTablesSerializer, ObjectMetadataTablesSerializer, SpeciesSerializer, DiagnosisSerializer, ObjectMetadataSerializer, GroupUserLinkageSerializer,GroupUserLinkageViewSerializer, MetadataStaticChangeSerializer, DeviceTypeTablesSerializer, ScalingValueTablesSerializer, DeviceTypeSerializer, ScalingValueSerializer
from .models import Users, Records, Access_Group_Linkage, Group_User_Linkage, Assets,UserPreferences, Assets_Metadata_Dynamic,DownloadDataset, Datasets, Access_Policies, Groups , UploadTransfer, Roles, Processing_Types, Detection, Segmentation, Package, Access_Types, Metadata_Static, Device_Type, Scaling_Value, Object_Metadata, Sex, Species, Localization, Diagnosis
from .services import create_dataset,process_label_properties, delete_record, delete_asset, delete_dataset
from .tasks import recalculate_all_metrics, generate_dataset_archive, copy_dataset, clean_annotations_after_class_delete, update_annotation_colors
class ProfileView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response({"user": serializer.data})


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
  
class IsDatasetAdminOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            
            return True

        user = request.user
       
        policy = obj.access_policy_id
        group_ids = Access_Group_Linkage.objects.filter(
            access_policy_id=policy
        ).values_list('group_id', flat=True)

        return Group_User_Linkage.objects.filter(
            group_id__in=group_ids,
            user_id=user,
            role_id__role_name="Admin"
        ).exists()
       

class IsRecordAdminOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
   
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True

        user = request.user
        
        record_id = getattr(obj, 'record_id', None)
        asset_id = getattr(obj, 'asset_id', None)
        dataset_id = getattr(obj, 'dataset_id', None)
        if record_id:
            try:
                
                record = Records.objects.get(record_id=record_id)
                policy = record.asset_id.dataset_id.access_policy_id
            except Records.DoesNotExist:
                return False
        
        elif asset_id:
            try:
          
                asset = Assets.objects.get(asset_id=asset_id)
                policy = asset.dataset_id.access_policy_id
            except Assets.DoesNotExist:
                return False

        elif dataset_id:
            try:
                dataset = Datasets.objects.get(dataset_id=dataset_id)
                policy = dataset.access_policy_id
            except Datasets.DoesNotExist:
                return False

        group_ids = Access_Group_Linkage.objects.filter(
            access_policy_id=policy
        ).values_list('group_id', flat=True)

        is_admin = Group_User_Linkage.objects.filter(
            group_id__in=group_ids,
            user_id=user,
            role_id__role_name__in=["Admin", "Editor"]
        ).exists()

        return is_admin

    def has_permission(self, request, view):
 
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        
        if request.method in ('POST', 'PATCH', 'PUT'):
     
            obj = request.data
            record_id =  obj.get('record_id', None)
            asset_id = obj.get('asset_id', None)
            dataset_id = obj.get('dataset_id', None)
            if not record_id: 
                record_id =  view.kwargs.get('record_id') 
            if not asset_id:
                asset_id =  view.kwargs.get('asset_id') 
            if not dataset_id:
                dataset_id =  view.kwargs.get('dataset_id')

            if not record_id and not dataset_id and not asset_id:
                return False
            if record_id:
                try:
                    
                    record = Records.objects.get(record_id=record_id)
                    policy = record.asset_id.dataset_id.access_policy_id
                except Records.DoesNotExist:
                    return False

            elif dataset_id:
                try:
                    dataset = Datasets.objects.get(dataset_id=dataset_id)
                    policy = dataset.access_policy_id
                except Datasets.DoesNotExist:
                    return False

            elif asset_id:
                try:
                    asset = Assets.objects.get(asset_id=asset_id)
                    policy = asset.dataset_id.access_policy_id
                except Assets.DoesNotExist:
                    return False
            group_ids = Access_Group_Linkage.objects.filter(
                access_policy_id=policy
            ).values_list('group_id', flat=True)

            return Group_User_Linkage.objects.filter(
                group_id__in=group_ids,
                user_id=request.user,
                role_id__role_name__in=["Admin", "Editor"]
            ).exists()

        return True  


class DatasetsViewSet(viewsets.ModelViewSet):
    queryset = Datasets.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsDatasetAdminOrReadOnly]
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DatasetsCreateSerializer
        return DatasetsReadSerializer

    
    def perform_create(self, serializer):
        
        with transaction.atomic():
            create_dataset(serializer)
                
                
                            
                        
    
    def list(self, request, *args, **kwargs):
        user = request.user
        user_groups = Group_User_Linkage.objects.filter(user_id=user).values_list('group_id', flat=True)
        private_policies = Access_Group_Linkage.objects.filter(
            group_id__in=user_groups,
            access_policy_id__access_type_id__access_type_name='Private'
        ).values_list('access_policy_id', flat=True)

        public_policies = Access_Policies.objects.filter(access_type_id__access_type_name='Public').values_list('access_policy_id', flat=True)

        datasets_queryset = Datasets.objects.filter(
            access_policy_id__in=list(private_policies) + list(public_policies)
        ).order_by('-dataset_id').select_related('access_policy_id', 'metadata_static_id')

        serializer = self.get_serializer(datasets_queryset, many=True, context={'request': request})
        return Response({'datasets': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        dataset = self.get_object()

        serializer = self.get_serializer(dataset, context={'request': request})
        dataset_data = serializer.data
        userpreferences = UserPreferences.objects.filter(user_id=request.user, dataset_id=dataset).first()
        dataset_data['label_properties'] = dataset.label_properties_json
        dataset_data['favorites_labels'] = None
        if userpreferences and userpreferences.preferences:
            dataset_data['favorites_labels'] = userpreferences.preferences.get('favorites_labels', [])
        
        response_data = {
      
            'is_admin': dataset.has_admin_access(request.user),
            'is_editor': dataset.has_editor_access(request.user),
            'dataset': dataset_data
        }

        return Response(response_data)
    
    def destroy(self, request, *args, **kwargs):
     
        try:
            instance = self.get_object()  
            dataset_id = instance.dataset_id
            
            
            with transaction.atomic():
                delete_dataset(dataset_id)
                
                
            return Response({"detail": "Dataset deleted successfully."}, status=204)

        except Datasets.DoesNotExist:
            return Response({"error": "Dataset not found"}, status=status.HTTP_404_NOT_FOUND)
   

class DatasetManagementViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetManagementSerializer
    permission_classes = [permissions.IsAuthenticated, IsDatasetAdminOrReadOnly]
    queryset = Datasets.objects.all()
    def retrieve(self, request, *args, **kwargs):
        dataset = self.get_object()

        serializer = self.serializer_class(dataset, context={'request': request})
        dataset_data = serializer.data
        
        dataset_data['label_properties'] = dataset.label_properties_json
      
        assets = Assets.objects.filter(dataset_id=dataset).order_by('-asset_id').annotate(
            records_count=Count('records'), 
            validation_mask_flag=Case(
                    When(records_count=Count('records', filter=Q(records__validation_mask_flag=True)), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                ),
            validation_bbox_flag=Case(
                    When(records_count=Count('records', filter=Q(records__validation_bbox_flag=True)), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                ),
            segmentation_count=Count('records', filter=Q(records__segmentation__isnull=False), distinct=True),

            detection_count=Count('records', filter=Q(records__detection__isnull=False), distinct=True),

            validation_mask_count=Count('records', filter=Q(records__validation_mask_flag=True), distinct=True),

            validation_bbox_count=Count('records', filter=Q(records__validation_bbox_flag=True), distinct=True),
        )
        records = Records.objects.filter(asset_id__in=assets).order_by('-record_id')

        response_data = {
            'assets': AssetsManagementSerializer(assets, many=True).data,
            'records': RecordsInfoSerializer(records, many=True).data, 
            'is_admin': dataset.has_admin_access(request.user),
            'is_editor': dataset.has_editor_access(request.user),
            'dataset': dataset_data
        }

        return Response(response_data)

class AssetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated, IsDatasetAdminOrReadOnly]

    def get_queryset(self):
      
        dataset_id = self.kwargs['dataset_id']
        return Assets.objects.filter(dataset_id=dataset_id).order_by('-asset_id').annotate(
            records_count=Count('records'), 
            validation_mask_flag=Case(
                    When(records_count=Count('records', filter=Q(records__validation_mask_flag=True)), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                ),
            validation_bbox_flag=Case(
                    When(records_count=Count('records', filter=Q(records__validation_bbox_flag=True)), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                ),
        )
    
class AssetRecordsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDatasetAdminOrReadOnly]
    queryset = Assets.objects.all()
    def get(self, request, asset_id):
        records = Records.objects.filter(asset_id=asset_id).order_by('record_id')
        
        serializer = AssetRecordsSerializer(records, many=True)
        return Response({
            'asset_id': asset_id,
            'records': serializer.data
        })
    

class TransferCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, dataset_id):
        try:
            total_files_expected = request.data.get('total_files_expected')
            
            
            if not total_files_expected:
                return Response(
                    {'error': 'total_files_expected is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            transfer = UploadTransfer.objects.create(
                dataset_id=Datasets.objects.get(dataset_id=dataset_id),
                user_id=request.user,
                total_files_expected=total_files_expected,
                status='pending',
                started_at=timezone.now()
            )
            
            return Response({
                'transfer_id': transfer.transfer_id,
                'total_files_expected': transfer.total_files_expected,
                'status': transfer.status,
                'created_at': transfer.created_at
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TransferProgressView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = UploadTransfer.objects.all()
    lookup_field = 'transfer_id'
    
    def get(self, request, dataset_id, transfer_id):
        transfer = get_object_or_404(
            UploadTransfer,
            transfer_id=transfer_id,
            dataset_id=dataset_id,
            user_id=request.user
        )
        
        return Response({
            'transfer_id': transfer.transfer_id,
            'progress': transfer.progress,
            'files_uploaded': transfer.files_uploaded,
            'total_files_expected': transfer.total_files_expected,
            'status': transfer.status,
            'started_at': transfer.started_at,
            'finished_at': transfer.finished_at
        })

class AssetUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]
    
    def post(self, request, dataset_id):
        
            try:
                if 'files' not in request.FILES:
                    return Response({'error': 'No files provided'}, status=400)
                
                files = request.FILES.getlist('files')
                transfer_id = request.POST.get('transfer_id')
                asset_id = request.POST.get('asset_id')
                asset_name = request.POST.get('asset_name')
                metadata = request.POST.get('metadata', None)
                if metadata:
                    metadata_dict = json.loads(metadata)
                    
                    
                    cleaned_metadata = {}
                    
                    for key, value in metadata_dict.items():
                        if isinstance(value, dict) and 'name' in value:
                            cleaned_metadata[key] = value['name']
                        else:
                            cleaned_metadata[key] = value

                if not transfer_id:
                    return Response({'error': 'transfer_id is required'}, status=400)
            
                transfer = UploadTransfer.objects.get(
                    transfer_id=transfer_id,
                    user_id=request.user,
                    dataset_id=dataset_id,
                   
                )
                transfer.status = 'in_progress'
                transfer.save()
                
                if asset_id:
                    asset = get_object_or_404(
                        Assets, 
                        asset_id=asset_id, 
                        dataset_id=Datasets.objects.get(dataset_id=dataset_id)
                    )
                    created = False
                else:
                    asset, created = Assets.objects.get_or_create(
                        asset_name=asset_name,
                        dataset_id=Datasets.objects.get(dataset_id=dataset_id),
                        
                        
                    )
                    if metadata:
                        metadata_dict = json.loads(metadata)
                        cleaned_metadata = {}
                        
                        for key, value in metadata_dict.items():
                            if isinstance(value, dict) and 'name' in value:
                               
                                cleaned_metadata[key] = value['name']
                            else:
                          
                                cleaned_metadata[key] = value
                        species = cleaned_metadata.get('species')
                        sex = cleaned_metadata.get('sex')
                        age = cleaned_metadata.get('age')
                        weight = cleaned_metadata.get('weight')
                        localization = cleaned_metadata.get('localization')
                        diagnosis = cleaned_metadata.get('diagnosis')
                        object_metadata, created = Object_Metadata.objects.get_or_create(
                            species_id=Species.objects.get(species_id=species) if species else None,
                            age=age,
                            weight=weight,
                            sex_id=Sex.objects.get(sex_id=sex) if sex else None,
                            
                        )
                        
                        Assets_Metadata_Dynamic.objects.get_or_create(
                            localization_id=Localization.objects.get(localization_id=localization) if localization else None,
                            diagnosis_id=Diagnosis.objects.get(diagnosis_id=diagnosis) if diagnosis else None,
                            asset_id=asset, 
                            object_metadata_id=object_metadata
                        )

                created_records = []
                for file in files:
                    if file.size > 50 * 1024 * 1024:
                        continue
                    
                    record = Records(asset_id=asset)
                    record.save()
                    
                    processed_file = self.process_image_file(file, record.record_id)
                    record.record_link.save(
                        f"{record.record_id}_{file.name.split('.')[0]}.webp",
                        processed_file
                    )
                    record.save()
                    
                    created_records.append(record.record_id)
                
                    transfer.files_uploaded += 1
                    transfer.progress = int((transfer.files_uploaded / transfer.total_files_expected) * 100)
                    transfer.save()
                
                if transfer.files_uploaded >= transfer.total_files_expected:
                    transfer.status = 'completed'
                    transfer.finished_at = timezone.now()
                    transfer.progress = 100
                
                transfer.save()
                
                return Response({
                    'transfer_id': transfer.transfer_id,
                    'progress': transfer.progress,
                    'files_uploaded': transfer.files_uploaded,
                    'files_in_chunk': len(created_records)
                }, status=status.HTTP_200_OK)
                
            except UploadTransfer.DoesNotExist:
                return Response({'error': 'Transfer not found'}, status=404)
            except Exception as e:
                if 'transfer' in locals():
                    transfer.status = 'failed'
                    transfer.save()
                return Response({'error': str(e)}, status=500)
    
    def process_image_file(self, file, record_id):
        try:
            image = Image.open(file)
            if image.mode in ('RGBA', 'LA'):
             
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                output_format = 'WEBP'
                save_kwargs = {'lossless': True}  
            else:

                image = image.convert('RGB')
                output_format = 'WEBP'
                save_kwargs = {'quality': 85, 'method': 6}
            
            webp_buffer = io.BytesIO()
            
            image.save(webp_buffer, format=output_format, **save_kwargs)
        
            file_name = f"{record_id}_{os.path.splitext(file.name)[0]}.webp"
            return ContentFile(webp_buffer.getvalue(), name=file_name)
            
        except Exception as e:

            file_name = f"{record_id}_{file.name}"
            return ContentFile(file.read(), name=file_name)
        
class Tables_Assets_And_Metadata_Dynamic_View(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, format=None):
        data = {
            
            'Species': {
                'table_name': Datasets._meta.db_table,
                'fields': list(SpeciesTablesSerializer().get_fields().keys()),
                'species': SpeciesTablesSerializer(Species.objects.all(), many=True).data
            }, 
            'Diagnosis': {
                'table_name': Diagnosis._meta.db_table,
                'fields': list(DiagnosisTablesSerializer().get_fields().keys()), 
                'diagnosis': DiagnosisTablesSerializer(Diagnosis.objects.all(), many=True).data
            },
            'Localization': {
                'table_name': Localization._meta.db_table,
                'fields': list(LocalizationTablesSerializer().get_fields().keys()),
                'localizations': LocalizationTablesSerializer(Localization.objects.all(), many=True).data
            }, 
            'Object_Metadata': {
                'table_name': Object_Metadata._meta.db_table,
                'fields': list(ObjectMetadataTablesSerializer().get_fields().keys()),
                'object_metadata': ObjectMetadataTablesSerializer(Object_Metadata.objects.all(), many=True).data
            }, 
            'Sex': {
                'table_name': Sex._meta.db_table,
                'fields': list(SexTablesSerializer().get_fields().keys()),
                'sex': SexTablesSerializer(Sex.objects.all(), many=True).data
            },
           
            
        }
        return Response(data)

class AnnotationRecordViewSet(viewsets.ModelViewSet):
    serializer_class = AnnotationRecordSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]  
 
    def perform_create(self, serializer):
        with transaction.atomic():
            
            record_id = self.kwargs['record_id']
            processing_type = serializer.validated_data['processing_type']
            processing_type_id = Processing_Types.objects.get(processing_type=processing_type)
            processed_record_link = serializer.validated_data['record_metadata_link']
            processed_record_link_name = processed_record_link.name
            record_object = Records.objects.get(record_id=record_id)

            if processing_type == 'Detection':
                json_data = json.load(processed_record_link)
                boxes = next(iter(json_data.values()))

                metrics_dict = Counter(box["label_name"] for box in boxes)

                metrics_bytes = io.BytesIO()
                metrics_bytes.write(json.dumps(metrics_dict, indent=2).encode("utf-8"))
                metrics_bytes.seek(0)
                metrics_file = ContentFile(metrics_bytes.read(), name=f"{processed_record_link_name.split('.')[0]}_metrics.json")
                
                Detection.objects.update_or_create(
                    record_id=record_object, 
                    processing_type_id=processing_type_id, 
                    defaults={
                        'record_metadata_dynamic_link': processed_record_link, 
                        'metrics': metrics_file
                    }
                )
            else:
                processed_record_link.seek(0)
                original_image = Image.open(processed_record_link).convert('RGBA')

                label_properties_path = record_object.asset_id.dataset_id.label_properties
                
                metrics_dict = calculate_segmentation_metrics(original_image, label_properties_path)

                webp_buffer = io.BytesIO()
                original_image.save(webp_buffer, format='WEBP', quality=100, optimize=True, compress_level=0, lossless=True)
                webp_buffer.seek(0)
                metrics_bytes = io.BytesIO()
                metrics_bytes.write(json.dumps(metrics_dict, indent=2).encode('utf-8'))
                metrics_bytes.seek(0)
                metrics_file = ContentFile(metrics_bytes.read(), name=str(processed_record_link_name.split('.')[0])+'_metrics.json')

                Segmentation.objects.update_or_create(record_id=record_object, processing_type_id=processing_type_id, defaults={'record_metadata_dynamic_link': ContentFile(webp_buffer.getvalue(), name=processed_record_link_name.split('.')[0]+'.webp'), 'metrics': metrics_file})
            
            recalculate_all_metrics.delay(record_object.asset_id.dataset_id.dataset_id)


class RecordViewSet(APIView):
   
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]

    def delete(self, request, record_id, format=None):
        delete_record(record_id, Records.objects.get(record_id=record_id).record_link.name)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ValidationRecordViewSet(viewsets.ModelViewSet):
    serializer_class = ValidationSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]  

    def perform_create(self, serializer):
        with transaction.atomic():
                record_id = self.kwargs['record_id']
                mode = serializer.validated_data['mode']
                record = Records.objects.get(record_id=record_id)

                if mode == "Segmentation":
                    record.validation_mask_flag = not record.validation_mask_flag
                else:
                    record.validation_bbox_flag = not record.validation_bbox_flag
                record.save()

class ValidationAssetViewSet(viewsets.ModelViewSet):
    serializer_class = ValidationSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]  

    def perform_create(self, serializer):
        with transaction.atomic():
                asset_id = self.kwargs['asset_id']
                mode = serializer.validated_data['mode']
                validation_flag = serializer.validated_data['validation_flag']
                asset = Assets.objects.get(asset_id=asset_id)
                records = Records.objects.filter(asset_id=asset)

                if mode == "Segmentation":
                    records.update(validation_mask_flag=validation_flag)
                else:
                    records.update(validation_bbox_flag=validation_flag)


class PackageViewSet(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    
    serializer_class = PackageSerializer
   
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]
    
    def perform_create(self, serializer):
        with transaction.atomic():
            dataset_id = self.kwargs['dataset_id']
            dataset = Datasets.objects.get(dataset_id=dataset_id)
            dataset.status = 'UPLOAD'
            dataset.save()
    
            notify_dataset_status_change(dataset_id, dataset.status, 'Dataset is being processed')
            user = self.request.user
            task = serializer.validated_data['task']
            mode = serializer.validated_data['mode']
            
            if task == 'TRAIN':
                validation_field = 'validation_mask_flag' if mode == 'Segmentation' else 'validation_bbox_flag'
                records_filter = {validation_field: True}
            else:
                validation_field = 'validation_mask_flag' if mode == 'Segmentation' else 'validation_bbox_flag'
                records_filter = {validation_field: False}
            
            if task == 'TRAIN':

                related_field = 'segmentation' if mode == 'Segmentation' else 'detection'
                records = Records.objects.filter(
                    asset_id__dataset_id=dataset,
                    **records_filter
                ).select_related(related_field).exclude(
                    **{f'{related_field}__isnull': True}
                )
                
                records_task = [
                    {record.record_id: [
                        build_full_url(record.record_link, False),
                        build_full_url(getattr(record, related_field).record_metadata_dynamic_link, False)
                    ]}
                    for record in records
                ]
            else:
                records = Records.objects.filter(
                    asset_id__dataset_id=dataset,
                    **records_filter
                )
                
                records_task = [
                    {record.record_id: [build_full_url(record.record_link, False)]}
                    for record in records
                ]
            
            package, created = Package.objects.update_or_create(
                user_id=user,
                dataset_id=dataset,
                defaults={
                    'label_properties': dataset.label_properties,
                    'mode': mode,
                    'task': task,
                    'package_status': 'CREATED'
                }
            )
            
            records_json = json.dumps({'records': records_task})
            record_file = ContentFile(records_json.encode('utf-8'), name='records_package.json')
            package.package = record_file
            package.save()

                    

class PackageGetViewSet(APIView):
    queryset = Package.objects.all()
    
    serializer_class = PackageSerializer
   
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]
    
    def get(self, request, *args, **kwargs):
       
        package = Package.objects.filter(package_status='CREATED').order_by('-package_id').first()
        if not package:
            return Response({"error": "No packages found"}, status=status.HTTP_404_NOT_FOUND)
        dataset = package.dataset_id
        group = Access_Group_Linkage.objects.get(access_policy_id=dataset.access_policy_id)
        user_id = request.user.user_id
 
        if group:
            group_user_linkage = Group_User_Linkage.objects.filter(group_id=group.group_id)
            
     
            if user_id in group_user_linkage.values_list('user_id', flat=True):
                
                serializer = PackageSerializer(package)
        
                return Response(serializer.data)
            else: 
                return Response({"error": "You don't have access to this dataset"}, status=status.HTTP_403_FORBIDDEN)
    

class ProcessedPackageView(APIView):
  
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProcessedFilesViewSerializer
   
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
 
        with transaction.atomic():
            if serializer.is_valid():
                
                data_response = serializer.validated_data.copy()
                mode = serializer.validated_data['mode']
                data_response_flag = True
                package_data = serializer.validated_data.get('images', {})
                processing_type_id = Processing_Types.objects.get(processing_type=mode)
             
                for metadata in package_data:
                  
                    
                    if mode == 'Segmentation':
                        mask = Image.open(io.BytesIO(package_data[metadata].read())).convert("RGBA")
                        mask_byte_arr = io.BytesIO()
                        mask.save(mask_byte_arr, format="WEBP", quality=100)
                        mask_byte_arr.seek(0)
                        mask_link_bytes = mask_byte_arr.read()
                        record_file = ContentFile(mask_link_bytes, name=str(package_data[metadata].name))
                        record_id = Records.objects.get(record_id=int(metadata))
                        record, _ = Segmentation.objects.update_or_create(
                            record_id=record_id,
                            processing_type_id=processing_type_id,
                            defaults={
                                'record_metadata_dynamic_link': record_file,
                              
                            }
                        )
                        record.save()
                        if data_response_flag:
                            data_response['images'] = [file.name for file in data_response.get('images', {}).values()]
                            data_response_flag = False
                    else:
                    
                        record_file = package_data[metadata]
                        record_id = Records.objects.get(record_id = int(metadata))
                        record, _ = Detection.objects.update_or_create( record_id = record_id , processing_type_id = processing_type_id, defaults={'record_metadata_dynamic_link': record_file})
                        record.save()

                recalculate_all_metrics.delay(Package.objects.get(package_id=serializer.validated_data['package_id']).dataset_id.dataset_id, True)                        
                return Response(data_response, status=status.HTTP_200_OK)
            else:
                
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DatasetStatusView(generics.RetrieveUpdateAPIView):
    serializer_class = DatasetStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Datasets.objects.all()

    def put(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            dataset_id = serializer.validated_data['dataset_id']
            dataset = Datasets.objects.get(dataset_id=dataset_id)
            
            old_status = dataset.status
            dataset.status = serializer.validated_data['status']
            dataset.save()
            
            if old_status != dataset.status:
                notify_dataset_status_change(dataset_id, dataset.status, 'Dataset is being processed')
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Datasets.DoesNotExist:
            return Response(
                {"error": "Dataset not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
     
class PackageStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    serializer_class = PackageStatusSerializer
    def put(self, request, package_id):
        serializer = self.serializer_class(data=request.data, context={'request': request})
      
        if serializer.is_valid():
            queryset = Package.objects.get(package_id=package_id)
            queryset.package_status = serializer.validated_data['package_status']
            queryset.save()
            serializer = self.serializer_class(queryset)
            return Response(serializer.data, status=status.HTTP_200_OK)  
        


class Tables_Dataset_And_Metadata_Static_View(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, format=None):
        data = {
            'Access_Type': {
                'table_name': Access_Types._meta.db_table,
                'fields': list(AccessTypesSerializer().get_fields().keys()),
                'access_types': [
                    {'id': at.access_type_id, 'name': at.access_type_name}
                    for at in Access_Types.objects.all()
                ]
            },
            'Metadata_Static': {
                'table_name': Metadata_Static._meta.db_table,
                'fields': list(MetadataStaticTablesSerializer().get_fields().keys())
            },
            'Datasets': {
                'table_name': Datasets._meta.db_table,
                'fields': list(DatasetTablesSerializer().get_fields().keys())
            }, 
            'Device_Type': {
                'table_name': Device_Type._meta.db_table,
                'fields': list(DeviceTypeTablesSerializer().get_fields().keys()), 
                'device_types': [
                    {'id': dt.device_type_id, 'name': dt.device_type_name} 
                    for dt in Device_Type.objects.all()
                ]
            },
            'Scaling_Value': {
                'table_name': Scaling_Value._meta.db_table,
                'fields': list(ScalingValueTablesSerializer().get_fields().keys()),
                'scaling_values': [
                    {'id': sv.scaling_value_id, 'name': sv.scaling_value_name} 
                    for sv in Scaling_Value.objects.all()
                ]
            }
        }
        return Response(data)
    

class MetadataStaticView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        dataset_id = kwargs.get('dataset_id')
        
        try:
            dataset = Datasets.objects.select_related(
                'metadata_static_id__device_type_id',
                'metadata_static_id__scaling_value_id'
            ).get(dataset_id=dataset_id)
            
            metadata_static = dataset.metadata_static_id
            
        except Datasets.DoesNotExist:
            return self._get_default_response()
        
        device_types = Device_Type.objects.all()
        scaling_values = Scaling_Value.objects.all()
        
        data = {
            'arbitrary_data': None,
            'asset_structure': None,
            'device_type': None,
            'scaling_value': None,
            'scales': [],
            'device_types': DeviceTypeSerializer(device_types, many=True).data,
            'scaling_values': ScalingValueSerializer(scaling_values, many=True).data,
        }
        
        if metadata_static:
            data.update({
                'device_type': metadata_static.device_type_id.device_type_name if metadata_static.device_type_id else None,
                'scaling_value': metadata_static.scaling_value_id.scaling_value_name if metadata_static.scaling_value_id else None,
                'scales': metadata_static.scales or [],
            })
            
            if metadata_static.arbitrary_data:
                data['arbitrary_data'] = self._load_arbitrary_data(metadata_static.arbitrary_data)
        
        return Response(data)
    
    def _load_arbitrary_data(self, arbitrary_data_file):
        
        try:
            resp = requests.get(build_full_url(arbitrary_data_file), timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
        
            return None
        except json.JSONDecodeError as e:
            
            return None
    
    def _get_default_response(self):
        device_types = Device_Type.objects.all()
        scaling_values = Scaling_Value.objects.all()
        
        return Response({
            'arbitrary_data': None,
            'asset_structure': None,
            'device_type': None,
            'scaling_value': None,
            'device_types': DeviceTypeSerializer(device_types, many=True).data,
            'scaling_values': ScalingValueSerializer(scaling_values, many=True).data,
            'scales': [],
            'error': 'Dataset not found'
        })
    
    def post(self, request, *args, **kwargs):
        dataset_id = kwargs.get('dataset_id')
        metadata_static_serializer = MetadataStaticChangeSerializer(data=request.data)
        metadata_static_serializer_model_dict = {
            'device_type': [DeviceTypeSerializer, Device_Type],
            'scaling_value': [ScalingValueSerializer, Scaling_Value],
        }
        with transaction.atomic():
            if metadata_static_serializer.is_valid():
          
                dataset = Datasets.objects.get(dataset_id=dataset_id)

                metadata_validated_data = metadata_static_serializer.validated_data
                arbitrary_data = {}
                metadata_arbitrary_data = metadata_validated_data.get('arbitrary_data', None)

                not_none_data = [key for key, value in metadata_validated_data.items() if value is not None]
                
                metadata_static_object = dataset.metadata_static_id
                if not metadata_static_object:
                    metadata_static_object = Metadata_Static.objects.create()
                    dataset.metadata_static_id = metadata_static_object
                    dataset.save()
                for data in not_none_data:
                    if data in metadata_static_serializer_model_dict:
                        data_serializer = metadata_static_serializer_model_dict[data][0](data=metadata_validated_data[data])
                        if data_serializer.is_valid():
                            data_id, _= metadata_static_serializer_model_dict[data][1].objects.get_or_create(**{data+'_name' : data_serializer.validated_data[data+'_name']})
                            setattr(metadata_static_object, data+'_id', data_id)
                
                    elif data == 'asset_structure':
                        metadata_static_object.asset_structure = ContentFile(json.dumps(metadata_validated_data['asset_structure']), name='asset_structure.json')
                    elif data == 'scales': 
                        metadata_static_object.scales = metadata_validated_data['scales']

                
                if metadata_arbitrary_data:
                    arbitrary_data = metadata_arbitrary_data
                    
                    metadata_static_object.arbitrary_data = ContentFile(json.dumps(arbitrary_data), name='arbitrary_data.json')
                
                
                metadata_static_object.save()

                if metadata_validated_data.get('label_properties', None) is not None:
                    file_content = metadata_validated_data['label_properties'].read()
                    is_yaml = metadata_validated_data['label_properties'].name.endswith((".yaml", ".yml")) 
                    processed_data = process_label_properties(file_content, is_yaml=is_yaml)
                    processed_json = json.dumps(processed_data, ensure_ascii=False, indent=4)
                    dataset.label_properties.save("label_properties.json", ContentFile(processed_json))
        
                
                
                return Response(metadata_static_serializer.data, status=status.HTTP_200_OK)
            
            return Response(metadata_static_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

class GroupUserView(APIView):
    queryset = Group_User_Linkage.objects.all()
    serializer_class = GroupUserLinkageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        group_id = self.kwargs.get('group_id')
        queryset = self.queryset.filter(group_id=group_id)
        serializer = GroupUserLinkageViewSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            group_id = self.kwargs.get('group_id')
            username = request.data.get('username')
            role_name = request.data.get('role_name')
            
            try:
                user = Users.objects.get(username=username)
                role = Roles.objects.get(role_name=role_name)
                
                if Group_User_Linkage.objects.filter(group_id=Groups.objects.get(group_id=group_id), user_id=user).exists():
                    return Response({"error": "User already exists in the group"}, status=status.HTTP_400_BAD_REQUEST)
                
                linkage = Group_User_Linkage.objects.create(
                    group_id=Groups.objects.get(group_id=group_id), 
                    user_id=user, 
                    role_id=role
                )
                
                serializer = GroupUserLinkageViewSerializer(linkage)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except Users.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            except Roles.DoesNotExist:
                return Response({"error": "Role not found"}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, *args, **kwargs):
        group_id = self.kwargs.get('group_id')
        user_id = request.data.get('user_id')
  
        try:
            linkage = Group_User_Linkage.objects.get(
                group_id=Groups.objects.get(group_id=group_id),
                user_id=user_id,
                role_id__role_name__in=['Viewer', 'Editor']
            )
            linkage.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Group_User_Linkage.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        

class AssetDeleteViewSet(APIView):
    queryset = Assets.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]
    
    def delete(self, request, *args, **kwargs):
        asset_id = self.kwargs.get('asset_id')
        try:
            asset = Assets.objects.get(asset_id=asset_id)
            delete_asset(asset.asset_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Assets.DoesNotExist:
            return Response({"error": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)
        

class DatasetDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dataset_id):
        dataset = get_object_or_404(Datasets, dataset_id=dataset_id)
  
        download = DownloadDataset.objects.create(
            dataset_id=dataset,
            user_id=request.user,
            status='pending',
            phase='preparing',
            progress=0
        )
       
        generate_dataset_archive.delay(download.transfer_id)

        return Response({
            'download_id': download.transfer_id,
            'phase': download.phase,
            'status': download.status
        }, status=202)


class DownloadStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, download_id):
        download = get_object_or_404(DownloadDataset, transfer_id=download_id, user_id=request.user)
        serializer = DownloadDatasetSerializer(download)
        return Response(serializer.data)
    

class CopyDataset(APIView):
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, dataset_id, *args, **kwargs):
        serializer = CopyDatasetSerializer(data=request.data)
        if serializer.is_valid():
            dataset_name = serializer.validated_data['dataset_name']
            records_validation = serializer.validated_data['records_validation']
            user = request.user

            
            download = DownloadDataset.objects.create(
                dataset_id_id=dataset_id,
                user_id=user,
                status='pending',
                phase='copying',
                progress=0,
                created_at=timezone.now()
            )

            
            copy_dataset.delay(dataset_id, dataset_name, records_validation, user.user_id, download.transfer_id)

            
            return Response({'download_id': download.transfer_id}, status=status.HTTP_201_CREATED)
        
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LabelsPropertiesView(APIView):
    queryset = Datasets.objects.all()
    serializer_class = LabelPropertiesSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]
    
    def post(self, request,dataset_id, format=None):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            label_properties = serializer.validated_data['label_properties']
            dataset = Datasets.objects.get(dataset_id=dataset_id)

            old_properties = json.loads(dataset.label_properties.read()) if dataset.label_properties else {}
            new_properties = label_properties
            dataset.label_properties = ContentFile(json.dumps(label_properties), name='label_properties.json')
            dataset.save()
            deleted_classes = set(old_properties.keys()) - set(new_properties.keys())
            modified_classes = [
                cls for cls in old_properties.keys() 
                if cls in new_properties and old_properties[cls] != new_properties[cls]
            ]
            
            cleanup_tasks = []
            for cls in deleted_classes:
                userpreferences = UserPreferences.objects.filter(user_id=request.user, dataset_id=dataset).first()
                if userpreferences:
                    userpreferences = userpreferences.preferences.get('favorites_labels', [])
                    if cls in userpreferences.preferences:
                        userpreferences.preferences = {'favorites_labels': userpreferences.pop(cls)}
                        userpreferences.save()
                cleanup_tasks.append(clean_annotations_after_class_delete.si(dataset_id, cls, old_properties[cls]))
            for cls in modified_classes:
                cleanup_tasks.append(update_annotation_colors.si(dataset_id, old_properties[cls], new_properties[cls]))

            if cleanup_tasks:

                workflow = group(cleanup_tasks) | recalculate_all_metrics.si(dataset_id, True)
                workflow.delay()
            else:
    
                recalculate_all_metrics.delay(dataset_id, True)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class FavoritesLabelsView(APIView):
    queryset = Datasets.objects.all()
    serializer_class = LabelPropertiesSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecordAdminOrReadOnly]
    
    def post(self, request, dataset_id, format=None):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            favorites_labels = serializer.validated_data['label_properties']
            dataset = Datasets.objects.get(dataset_id=dataset_id)
            userpreferences = UserPreferences.objects.filter(user_id=request.user, dataset_id=dataset).first()
            if not userpreferences:
              
                userpreferences = UserPreferences.objects.create(
                    user_id=request.user, 
                    dataset_id=dataset,
                    preferences={'favorites_labels': favorites_labels} 
                )
            else:
          
                userpreferences.preferences = {'favorites_labels': favorites_labels}
                userpreferences.save()
                

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)