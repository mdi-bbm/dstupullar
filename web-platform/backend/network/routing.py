from django.urls import re_path
from network.consumers import TaskStatusConsumer, DatasetStatusConsumer

websocket_urlpatterns = [
    re_path(r"ws/tasks/(?P<record_id>\d+)/$", TaskStatusConsumer.as_asgi()),
    re_path(r'ws/datasets/(?P<dataset_id>[^/]+)/$', DatasetStatusConsumer.as_asgi()),
]