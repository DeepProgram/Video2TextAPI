from rest_framework.decorators import api_view
from rest_framework import status
from django.http import StreamingHttpResponse
from apps.user.tasks import task_verify_token
from apps.user.views import generate_response
from .tasks import (
    task_get_video_info,
    task_download_youtube_video,
    task_process_and_save_requested_video_info_in_db,
    task_get_requested_video_data,
    task_get_process_session_info,
    task_generate_initial_session_and_get_video_id,
    task_get_process_video_completed_info,
    task_get_all_processed_videos,
    task_get_all_text_segments_of_video,
    task_get_video_clip_stream,
)
import subprocess
from io import BytesIO
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import VideoFileClip


# Create your views here.


@api_view(["POST"])
def search_video(request):
    is_valid_token, extra_info_dict = task_verify_token(request)
    if not is_valid_token:
        return extra_info_dict["response"]

    # JWT Authenticated
    json_data = request.data

    platform = json_data.get("platform", None)
    video_url = json_data.get("video_url", None)

    if platform is None or video_url is None:
        return generate_response(
            {"hint": "expecting_platform_video_url_in_json", "code": -1},
            status.HTTP_200_OK,
        )
    video_info_dict = task_get_video_info(platform, video_url)
    return generate_response({"data": video_info_dict, "code": 1}, status.HTTP_200_OK)


@api_view(["POST"])
def request_for_process(request):
    is_valid_token, extra_info_dict = task_verify_token(request)
    if not is_valid_token:
        return extra_info_dict["response"]

    user_id = extra_info_dict["user_id"]
    # JWT Authenticated
    json_data = request.data

    platform = json_data.get("platform", None)
    video_url = json_data.get("video_url", None)

    if platform is None or video_url is None:
        return generate_response(
            {"hint": "expecting_platform_video_url_in_json", "code": -1},
            status.HTTP_200_OK,
        )

    operation_info = task_process_and_save_requested_video_info_in_db(
        user_id, platform, video_url
    )
    if operation_info["status"] == 1:
        return generate_response(
            {"hint": "video_request_accepted", "code": 1}, status.HTTP_200_OK
        )
    else:
        return generate_response(
            {"hint": "something_went_wrong", "code": 2}, status.HTTP_200_OK
        )


@api_view(["GET"])
def get_requested_video_info(request):
    is_valid_token, extra_info_dict = task_verify_token(request)
    if not is_valid_token:
        return extra_info_dict["response"]
    user_id = extra_info_dict["user_id"]
    # JWT Authenticated

    operation_info = task_get_requested_video_data(user_id)
    return generate_response(
        {"hint": "got_all_requested_data", "code": 1, "data": operation_info},
        status.HTTP_200_OK,
    )


@api_view(["POST"])
def download_and_process_video(request):
    is_valid_token, extra_info_dict = task_verify_token(request)
    if not is_valid_token:
        return extra_info_dict["response"]
    user_id = extra_info_dict["user_id"]
    # JWT Authenticated

    json_data = request.data
    platform = json_data.get("platform", None)
    video_url = json_data.get("video_url", None)

    if platform is None or video_url is None:
        return generate_response(
            {"hint": "expecting_platform_video_url_in_json", "code": -1},
            status.HTTP_200_OK,
        )
    video_id = task_generate_initial_session_and_get_video_id(video_url, user_id)
    task_download_youtube_video.delay(platform, video_url, user_id, video_id)

    return generate_response(
        {"hint": "background_task_started", "code": 2}, status.HTTP_201_CREATED
    )


@api_view(["GET"])
def get_process_video_processing_status(request):
    is_valid_token, extra_info_dict = task_verify_token(request)
    if not is_valid_token:
        return extra_info_dict["response"]
    user_id = extra_info_dict["user_id"]
    # JWT Authenticated

    operation_info = task_get_process_session_info(user_id)
    return generate_response(
        {
            "hint": "got_session_info",
            "code": operation_info["code"],
            "data": operation_info["data"],
        },
        status.HTTP_200_OK,
    )


@api_view(["GET"])
def get_process_video_completed_status(request):
    is_valid_token, extra_info_dict = task_verify_token(request)
    if not is_valid_token:
        return extra_info_dict["response"]
    user_id = extra_info_dict["user_id"]
    # JWT Authenticated

    operation_info = task_get_process_video_completed_info(user_id)
    if operation_info["status"] == -1:
        return generate_response(
            {"hint": "user_id_not_found_in_db", "code": -1}, status.HTTP_200_OK
        )

    if operation_info["status"] == 1:
        return generate_response(
            {
                "hint": "got_process_completed_data",
                "code": 1,
                "data": operation_info["data"],
            },
            status.HTTP_200_OK,
        )


@api_view(["GET"])
def get_all_videos(request):
    filter_video = request.query_params.get("search", None)
    if filter_video == "null":
        filter_video = None
    operation_info = task_get_all_processed_videos(filter_video)
    if operation_info["status"] == 1:
        return generate_response(
            {"hint": "got_all_videos", "code": 1, "data": operation_info["data"]},
            status.HTTP_200_OK,
        )


@api_view(["GET"])
def get_all_text_gegments(request):
    video_id = request.query_params.get("v", None)
    if video_id is None:
        return generate_response({"hint": "invalid_query_params"}, status.HTTP_200_OK)

    operation_info = task_get_all_text_segments_of_video(video_id)
    if operation_info["status"] == 1:
        return generate_response(
            {"hint": "got_all_segments", "code": 1, "data": operation_info["data"]},
            status.HTTP_200_OK,
        )


@api_view(["POST"])
def get_video_clip(request):
    json_data = request.data
    clip_id = json_data.get("clip_id", None)

    if clip_id is None:
        return generate_response(
            {"error": "something_went_wrong"}, status.HTTP_400_BAD_REQUEST
        )
    operation_info = task_get_video_clip_stream(clip_id)
    if operation_info["status"] == 1:
        return generate_response(
            {
                "hint": "got_video_clip",
                "code": 1,
                "video_url": operation_info["clip_path"],
            },
            status.HTTP_200_OK,
        )
    else:
        generate_response(
            {"hint": "something_went_wrong", "code": -1}, status.HTTP_200_OK
        )
