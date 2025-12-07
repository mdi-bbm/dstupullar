from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfileView, AssetUploadView
router = DefaultRouter()


from .views import DatasetsViewSet, AssetViewSet, AssetRecordsView, TransferCreateView,DatasetDownloadView,CopyDataset, FavoritesLabelsView, LabelsPropertiesView, DownloadStatusView, AssetDeleteViewSet,TransferProgressView,GroupUserView, RecordViewSet, ProcessedPackageView, Tables_Assets_And_Metadata_Dynamic_View, MetadataStaticView, AnnotationRecordViewSet, ValidationRecordViewSet, PackageStatusView,Tables_Dataset_And_Metadata_Static_View, DatasetStatusView, PackageGetViewSet, ValidationAssetViewSet, PackageViewSet, DatasetManagementViewSet
router.register(r'datasets', DatasetsViewSet)

router.register(r'datasets/(?P<dataset_id>[^/.]+)/assets', AssetViewSet, basename='dataset-assets')
router.register(r'dataset/assets/records/(?P<record_id>[^/.]+)', AnnotationRecordViewSet, basename='asset-records')
router.register(r'record/validation/(?P<record_id>[^/.]+)', ValidationRecordViewSet, basename='record-validation')
router.register(r'asset/validation/(?P<asset_id>[^/.]+)', ValidationAssetViewSet, basename='asset-validation')
router.register(r'dataset/management', DatasetManagementViewSet, basename='dataset-management')
router.register(r'dataset/(?P<dataset_id>[^/.]+)/packages', PackageViewSet, basename='dataset-packages')


urlpatterns = [
    path("", include(router.urls)), 
    path('profile_18fn1038wn198r1nb/', ProfileView.as_view()),
    path('dataset/<int:dataset_id>/transfers/', TransferCreateView.as_view(), name='create-transfer'),
    path('dataset/<int:dataset_id>/transfers/<int:transfer_id>/', TransferProgressView.as_view(), name='transfer-progress'),
    path('dataset/<int:dataset_id>/assets/upload/', AssetUploadView.as_view(),name='asset-upload'),
    path('assets/<int:asset_id>/records/', AssetRecordsView.as_view(), name='asset-records'),
    path('processed_package/', ProcessedPackageView.as_view(), name='processed_package'),
    path('package_status/<int:package_id>/', PackageStatusView.as_view(), name='package_status'),    
    path('status_mfdqofn19101f/', DatasetStatusView.as_view(), name='status'),
    path('package/', PackageGetViewSet.as_view(), name='package'),
    path("tables/", Tables_Dataset_And_Metadata_Static_View.as_view(), name='tables'),
    path("assets/metadata/", Tables_Assets_And_Metadata_Dynamic_View.as_view(), name='tables'),
    path('dataset/metadata_static/<int:dataset_id>/', MetadataStaticView.as_view(), name='metadata_static'),
    path('dataset/group/<int:group_id>/', GroupUserView.as_view(), name='group'),
    path('record/<int:record_id>/',RecordViewSet.as_view(), name='record'),
    path('assets/<int:asset_id>/', AssetDeleteViewSet.as_view(), name='asset'),
    path('datasets/<int:dataset_id>/download/', DatasetDownloadView.as_view(), name='dataset-download'),
    path('downloads/<int:download_id>/status/', DownloadStatusView.as_view(), name='download-status'),
    path("copy_dataset/<int:dataset_id>/", CopyDataset.as_view(), name='copy_dataset'),
    path("label_properties/<int:dataset_id>/", LabelsPropertiesView.as_view(), name='label_properties'),
    path("label_properties/favorites/<int:dataset_id>/", FavoritesLabelsView.as_view(), name='label_properties'),
]   

