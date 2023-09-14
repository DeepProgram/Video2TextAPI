from django.conf import settings
from django.http import FileResponse, Http404
import os


def serve_thumbnail(request, file_name):
    image_path = os.path.join(
        os.path.dirname(__file__), "..", "content", "thumbnail", file_name
    )
    if os.path.exists(image_path):
        return FileResponse(open(image_path, "rb"))
    else:
        raise Http404()


def serve_video_segment(request, file_name):
    image_path = os.path.join(
        os.path.dirname(__file__), "..", "content", "segment", file_name
    )
    if os.path.exists(image_path):
        response = FileResponse(open(image_path, "rb"))
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response
    else:
        raise Http404()
