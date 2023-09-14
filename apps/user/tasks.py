from .models import UserData
from uuid import uuid4
import time
from typing import Tuple, Dict, Optional
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import jwt
from django.conf import settings


def is_user_already_exist(email: str) -> bool:
    try:
        user_data = UserData.objects.get(email=email)
    except UserData.DoesNotExist:
        return False
    return True


def task_save_user_credential_in_db(
    email: str, password: str, full_name: str, account_type: int
) -> Dict:
    if is_user_already_exist(email):
        return {"status": 0}  # Email Already Exist In Database
    else:
        user_id = str(uuid4())
        new_user_data = UserData(
            user_id=user_id,
            email=email,
            password=password,
            full_name=full_name,
            user_level=account_type,
            join_epoch_time=int(time.time()),  # Epoch Time In Seconds
        )
        try:
            new_user_data.save()
            new_jwt_token = task_generate_jwt_token(user_id)
            return {
                "status": 1,
                "token": new_jwt_token,
                "user_level": new_user_data.user_level,
            }
        except Exception:
            return {"status": -1}  # Database Saving Error


def task_verify_login(email: str, password: str):
    try:
        user_data = UserData.objects.get(email=email)
    except UserData.DoesNotExist:
        return {"status": -1}
    if user_data.password != password:
        return {"status": 0}
    token = task_generate_jwt_token(str(user_data.user_id))
    return {"status": 1, "token": token, "user_level": user_data.user_level}


def task_generate_jwt_token(user_id):
    expiration_time = datetime.utcnow() + timedelta(minutes=20)
    payload = {
        "user_id": user_id,
        "exp": expiration_time,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


def task_verify_token(request) -> Tuple[bool, Dict]:
    try:
        token = request.META.get("HTTP_AUTHORIZATION", "").split(" ")[1]
    except Exception:
        return False, {
            "response": Response(
                data={"error": "token_not_found"}, status=status.HTTP_401_UNAUTHORIZED
            )
        }
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        return True, {"user_id": user_id}
    except Exception:
        return False, {
            "response": Response(
                data={"error": "jwt_token_invalid"}, status=status.HTTP_401_UNAUTHORIZED
            )
        }
