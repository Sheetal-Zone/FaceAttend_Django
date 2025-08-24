from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/detection/$', consumers.DetectionConsumer.as_asgi()),
    re_path(r'ws/camera/(?P<camera_id>\w+)/$', consumers.CameraConsumer.as_asgi()),
    re_path(r'ws/stats/$', consumers.StatsConsumer.as_asgi()),
]
