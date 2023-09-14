from pytube import YouTube
from celery import shared_task
from django.db.models import Max
from .models import ProcessVideoSession, VideoData, VideoSegments, RequestedVideo
from apps.user.models import UserData
import time
from uuid import uuid4
import whisper
import whisper.transcribe
from moviepy.video.io.VideoFileClip import VideoFileClip
from io import BytesIO
from proglog import ProgressBarLogger
import re
import os
import os.path
import tqdm
import sys
from typing import Optional
import subprocess


class DownloadSession:
    def __init__(self, user_id):
        self.session_data = (
            ProcessVideoSession.objects.filter(user_data__user_id=user_id)
            .order_by("-session_creation_time")
            .first()
        )

    def update_percentage(self, chunk, file_handler, remaining_bytes):
        file_size = chunk.filesize
        downloaded_size = file_size - remaining_bytes
        downloaded_percentage = int((downloaded_size / file_size) * 100)

        self.session_data.status = "Downloading Video"
        self.session_data.progress = downloaded_percentage
        self.session_data.save()


class CustomWhisperTranscriber:
    class _CustomProgressBar(tqdm.tqdm):
        def __init__(self, *args, user_id, **kwargs):
            super().__init__(*args, **kwargs)
            self.user_id = user_id
            self._current = self.n

        def update(self, n):
            super().update(n)
            self._current += n
            update_session_object(
                self.user_id,
                "Converting Audio To Text",
                int((self._current / self.total) * 100),
            )

    def __init__(self, user_id):
        self.user_id = user_id
        update_session_object(user_id, "Initalizing AI", 0)

        # Inject into tqdm.tqdm of Whisper, so we can see progress
        transcribe_module = sys.modules["whisper.transcribe"]
        transcribe_module.tqdm.tqdm = lambda *args, **kwargs: self._CustomProgressBar(
            *args, user_id=self.user_id, **kwargs
        )

        self.model = whisper.load_model("base")
        update_session_object(user_id, "Initalizing AI", 100)

    def transcribe_and_get_segements(self, audio_url, fp16=False, verbose=None):
        result = self.model.transcribe(audio_url, fp16=fp16, verbose=verbose)
        return result


class MyBarLogger(ProgressBarLogger):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def bars_callback(self, bar, attr, value, old_value=None):
        percentage = int((value / self.bars[bar]["total"]) * 100)
        update_session_object(self.user_id, "Converting Video To Audio", percentage)


def task_get_video_info(platform: str, url: str):
    if platform == "youtube":
        return task_get_youtube_video_info(url)


def task_get_youtube_video_info(url: str):
    yt = YouTube(url)
    return {
        "title": yt.title,
        "thumbnail": yt.thumbnail_url,
        "creator_name": yt.author,
    }


def task_process_and_save_requested_video_info_in_db(
    user_id: str, platform: str, video_url: str
):
    if platform == "youtube":
        try:
            user_db_data = UserData.objects.get(user_id=user_id)
        except UserData.DoesNotExist:
            return {"status": -1}
        yt = YouTube(video_url)
        video_db_data = get_video_db_data_from_video_url(yt.watch_url)

        if video_db_data is None:
            video_db_data = add_youtube_video_info_in_database(yt)
            video_db_data.save()

        max_queue_position = RequestedVideo.objects.aggregate(Max("queue_position"))[
            "queue_position__max"
        ]
        queue_position = max_queue_position + 1 if max_queue_position else 1

        requested_video_db_data = RequestedVideo(
            request_id=str(uuid4()),
            video_data=video_db_data,
            requested_by=user_db_data,
            is_video_processed=False,
            queue_position=queue_position,
            request_epoch_time=int(time.time()),
        )
        try:
            requested_video_db_data.save()
            return {"status": 1}
        except Exception as e:
            print(e)
            return {"status": 2}


def task_get_requested_video_data(user_id: str):
    requested_video_db_data = RequestedVideo.objects.filter(
        requested_by__user_id=user_id, is_video_processed=False
    )
    max_queue_position = RequestedVideo.objects.aggregate(Max("queue_position"))[
        "queue_position__max"
    ]
    max_queue_position = max_queue_position if max_queue_position else 1
    requested_video_list = []
    for req_info in requested_video_db_data:
        video_data = req_info.video_data
        requested_video_list.append(
            {
                "video_id": video_data.video_id,
                "title": video_data.video_title,
                "duration": video_data.video_duration,
                "platform": video_data.platform,
                "source_url": video_data.video_url,
                "queue": f"{req_info.queue_position}/{max_queue_position}",
                "added": req_info.request_epoch_time,
            }
        )

    return requested_video_list


def get_video_db_data_from_video_url(video_url: str) -> Optional[VideoData]:
    try:
        video_data_db = VideoData.objects.get(video_url=video_url)
        return video_data_db
    except VideoData.DoesNotExist:
        return None


def add_youtube_video_info_in_database(pytube_obj: YouTube):
    video_data = VideoData(
        video_id=str(uuid4()),
        video_title=pytube_obj.title,
        video_duration=pytube_obj.length,
        platform="youtube",
        channel_id=pytube_obj.channel_id,
        channel_name=pytube_obj.author,
        video_url=pytube_obj.watch_url,
    )
    return video_data


def start_download_session(user_id: str, video_id: str):
    current_time = int(time.time())
    expired_time = current_time + (5 * 60)
    session_data = ProcessVideoSession(
        session_id=str(uuid4()),
        user_data=UserData.objects.get(user_id=user_id),
        session_creation_time=current_time,
        session_end_time=expired_time,
        status="Initializing Download",
        progress=0,
        video_data=VideoData.objects.get(video_id=video_id),
    )
    session_data.save()


def update_session_object(user_id: str, status_message: str, progress: int):
    session_data = (
        ProcessVideoSession.objects.filter(user_data__user_id=user_id)
        .order_by("-session_creation_time")
        .first()
    )
    session_data.status = status_message
    session_data.progress = progress
    session_data.save()


def start_downaloding_youtube_video(url: str, user_id: str, video_id: str):
    dwonload_session = DownloadSession(user_id)
    yt = YouTube(url, on_progress_callback=dwonload_session.update_percentage)
    stream = yt.streams.get_by_itag(22)
    stream.download(output_path="content/video/", filename=video_id + ".mp4")
    subprocess.run(
        ["wget", "-O", "content/thumbnail/" + video_id + ".jpg", yt.thumbnail_url]
    )
    update_session_object(user_id, "Downloaded", 100)  # Update Session Status Of UserID


def convert_video_to_audio(user_id: str, file_name: str):
    logger = MyBarLogger(user_id)
    audio_output_path = "content/audio/" + file_name + ".wav"
    video_clip = VideoFileClip("content/video/" + file_name + ".mp4")
    audio_clip = video_clip.audio
    audio_clip.write_audiofile(audio_output_path, codec="pcm_s16le", logger=logger)
    return audio_output_path


def convert_video_to_text(user_id: str, video_id: str, file_name: str):
    audio_file_path = convert_video_to_audio(user_id, file_name)
    transcriber = CustomWhisperTranscriber(user_id)
    whisper_generated_dict = transcriber.transcribe_and_get_segements(audio_file_path)
    segments = whisper_generated_dict["segments"]
    video_database_data = VideoData.objects.get(video_id=video_id)
    update_session_object(user_id, "Adding Segements In Database", 0)
    count = 0
    total = len(segments)
    for segment in segments:
        video_segment_data = VideoSegments(
            clip_id=str(uuid4()),
            video_data=video_database_data,
            start_time=round(segment["start"], 2),
            end_time=round(segment["end"], 2),
            text=segment["text"],
        )
        video_segment_data.save()
        count += 1
        update_session_object(
            user_id, "Adding Segements In Database", int((count // total)) * 100
        )
    update_session_object(user_id, "Completed", 100)


@shared_task(ignore_result=False)
def task_download_youtube_video(platform: str, url: str, user_id: str, video_id: str):
    user_data_db = UserData.objects.get(user_id=user_id)
    user_full_name = user_data_db.full_name
    if platform == "youtube":
        start_downaloding_youtube_video(url, user_id, video_id)
        convert_video_to_text(user_id, video_id, video_id)
        video_db_data = VideoData.objects.get(video_id=video_id)
        video_db_data.local_video_path = "content/video/" + video_id + ".mp4"
        video_db_data.local_thumbnail_path = "content/thumbnail/" + video_id + ".jpg"
        video_db_data.is_video_processed = True
        video_db_data.video_processed_by = user_full_name
        video_db_data.video_processed_on = int(time.time())
        video_db_data.save()


def task_generate_initial_session_and_get_video_id(video_url: str, user_id: str):
    yt = YouTube(video_url)
    video_data_db = get_video_db_data_from_video_url(yt.watch_url)
    if video_data_db is None:
        video_data_db = add_youtube_video_info_in_database(yt)
        video_data_db.save()
    start_download_session(user_id, video_data_db.video_id)
    return str(video_data_db.video_id)


def task_get_process_session_info(user_id: str):
    session_data = (
        ProcessVideoSession.objects.filter(user_data__user_id=user_id)
        .order_by("-session_creation_time")
        .first()
    )
    if session_data is None:
        return {"code": 1, "data": []}
    if session_data.status == "Completed":
        return {"code": 1, "data": []}
    # video_db_data = VideoData.objects.get(video_id=session_data.video_id)
    return {
        "code": 1 if session_data.status == "Completed" else 0,
        "data": [
            {
                "title": session_data.video_data.video_title,
                "status": session_data.status,
                "progress": session_data.progress,
                "video_id": session_data.video_data.video_id,
                "platform": session_data.video_data.platform,
                "source_url": session_data.video_data.video_url,
            }
        ],
    }


def task_get_process_video_completed_info(user_id: str):
    try:
        user_db_data = UserData.objects.get(user_id=user_id)
    except UserData.DoesNotExist:
        return {"status": -1}
    video_db_data = VideoData.objects.filter(
        video_processed_by=user_db_data.full_name, is_video_processed=True
    )
    completed_list = []
    for video_info in video_db_data:
        completed_list.append(
            {
                "video_id": video_info.video_id,
                "title": video_info.video_title,
                "duration": video_info.video_duration,
                "platform": video_info.platform,
                "source_url": video_info.video_url,
                "added": video_info.video_processed_on,
            }
        )
    return {"status": 1, "data": completed_list}


def task_get_all_processed_videos(filter_video):
    if filter_video is None or filter_video.strip() == "":
        video_db_data = VideoData.objects.filter(is_video_processed=True)
    else:
        video_db_data = VideoData.objects.filter(
            is_video_processed=True, title__icontains=filter_video
        )
    video_list = []
    for video in video_db_data:
        video_list.append(
            {
                "video_id": video.video_id,
                "title": video.video_title,
                "thumbnail": video.local_thumbnail_path,
            }
        )
    return {"status": 1, "data": video_list}


def task_get_all_text_segments_of_video(video_id: str):
    try:
        video_db_data = VideoData.objects.get(video_id=video_id)
    except VideoData.DoesNotExist:
        return {"status": -1}
    text_segments_db_data = VideoSegments.objects.filter(video_data=video_db_data)
    text_segments_list = []
    for segment in text_segments_db_data:
        text_segments_list.append(
            {
                "clip_id": segment.clip_id,
                "text": segment.text,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
            }
        )
    data = {
        "segments": text_segments_list,
        "thumbnail": video_db_data.local_thumbnail_path,
        "title": video_db_data.video_title,
        "channel": video_db_data.channel_name,
        "duration": video_db_data.video_duration,
        "source_url": video_db_data.video_url,
        "channel_id": video_db_data.channel_id,
    }
    return {"status": 1, "data": data}


def task_get_video_clip_stream(clip_id: str):
    clip_path = f"content/segment/{clip_id}.mp4"
    if os.path.exists(clip_path):
        return {"status": 1, "clip_path": clip_path}

    try:
        segment_db_data = VideoSegments.objects.get(clip_id=clip_id)
    except VideoSegments.DoesNotExist:
        return {"status": -1}
    video_local_path = segment_db_data.video_data.local_video_path
    start_time = str(segment_db_data.start_time)
    end_time = str(segment_db_data.end_time)
    cmd = [
        "ffmpeg",
        "-i",
        video_local_path,
        "-ss",
        start_time,
        "-to",
        end_time,
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-vf",
        "copy",
        "-f",
        "mp4",
        clip_path,
    ]
    subprocess.run(cmd, check=True)
    return {"status": 1, "clip_path": clip_path}
