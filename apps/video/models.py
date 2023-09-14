from django.db import models
from apps.user.models import UserData

# Create your models here.


class VideoData(models.Model):
    video_id = models.UUIDField()
    video_title = models.TextField()
    video_duration = models.IntegerField()
    platform = models.TextField()
    channel_id = models.TextField()
    channel_name = models.TextField()
    video_url = models.TextField()
    local_video_path = models.TextField(default="")
    local_thumbnail_path = models.TextField(default="")
    is_video_processed = models.BooleanField(default=False)
    video_processed_by = models.TextField(default="Reuv Play")
    video_processed_on = models.IntegerField(default=0)  # Epoch Time In Seconds


class ProcessVideoSession(models.Model):
    session_id = models.UUIDField()
    user_data = models.ForeignKey(UserData, on_delete=models.CASCADE)
    session_creation_time = models.IntegerField()
    session_end_time = models.IntegerField()
    status = models.TextField()
    progress = models.IntegerField()
    video_data = models.ForeignKey(VideoData, on_delete=models.CASCADE)


class VideoSegments(models.Model):
    clip_id = models.UUIDField()
    video_data = models.ForeignKey(VideoData, on_delete=models.CASCADE)
    start_time = models.FloatField()
    end_time = models.FloatField()
    text = models.TextField()


class RequestedVideo(models.Model):
    request_id = models.UUIDField()
    video_data = models.ForeignKey(VideoData, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(UserData, on_delete=models.CASCADE)
    is_video_processed = models.BooleanField()
    queue_position = models.IntegerField()
    request_epoch_time = models.IntegerField()
    request_completed_epoch_time = models.IntegerField(default=0)
