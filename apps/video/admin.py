from django.contrib import admin
from .models import VideoData, ProcessVideoSession, VideoSegments, RequestedVideo

# Register your models here.

admin.site.register(VideoData)
admin.site.register(ProcessVideoSession)
admin.site.register(VideoSegments)
admin.site.register(RequestedVideo)
