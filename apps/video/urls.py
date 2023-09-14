from django.urls import path
from . import views

urlpatterns = [
    path("search/", views.search_video, name="search_video"),
    path("request/", views.request_for_process, name="request_vidoe"),
    path("request/data/", views.get_requested_video_info, name="get_requested_video"),
    path("process/", views.download_and_process_video, name="process_video"),
    path(
        "process/status/",
        views.get_process_video_processing_status,
        name="process_video_status",
    ),
    path(
        "process/status/completed/",
        views.get_process_video_completed_status,
        name="process_video_completed_status",
    ),
    path("", views.get_all_videos, name="get_all_videos"),
    path("watch", views.get_all_text_gegments, name="get_all_text_segments"),
    path("stream/", views.get_video_clip, name="get_video_clipped_stream"),
]
