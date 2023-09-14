from django.shortcuts import render
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response

from rest_framework import status
from .tasks import (
    task_save_user_credential_in_db,
    task_verify_login,
)


# Create your views here.


@api_view(["POST"])
def signup(request):
    data = request.headers
    json_data = request.data

    email = json_data.get("email", None)
    password = json_data.get("password", None)
    full_name = json_data.get("fullname", None)
    account_type = json_data.get("account_type", None)

    if email is None or password is None or full_name is None or account_type is None:
        return generate_response(
            {
                "hint": "expecting_email_password_fullname_account-type_in_json",
                "code": 2,
            },
            status.HTTP_200_OK,
        )
    user_data_saving_response = task_save_user_credential_in_db(
        email, password, full_name, account_type
    )
    if user_data_saving_response["status"] == 1:
        response = generate_response(
            {
                "hint": "signup_successful",
                "code": 1,
                "user_level": user_data_saving_response["user_level"],
            },
            status.HTTP_201_CREATED,
        )
        response["Access-Control-Expose-Headers"] = "Authorization"
        response["Authorization"] = f"Bearer {user_data_saving_response['token']}"
        return response
    elif user_data_saving_response["status"] == 0:
        return generate_response(
            {"hint": "user_already_exist", "code": 3}, status.HTTP_200_OK
        )
    else:
        return generate_response(
            {"hint": "database_error", "code": 4}, status.HTTP_200_OK
        )


@api_view(["POST"])
def login(request):
    data = request.headers
    json_data = request.data

    email = json_data.get("email", None)
    password = json_data.get("password", None)

    if email is None or password is None:
        return generate_response(
            {"hint": "expecting_email_password_in_json", "code": -1}, status.HTTP_200_OK
        )

    verification_info = task_verify_login(email, password)
    if verification_info["status"] == -1:
        return generate_response(
            {"hint": "user_not_found", "code": -1}, status=status.HTTP_200_OK
        )
    elif verification_info["status"] == 0:
        return generate_response(
            {"hint": "user_credentials_didnt_match", "code": 0},
            status=status.HTTP_200_OK,
        )
    else:
        response = generate_response(
            {
                "hint": "login_successful",
                "code": 1,
                "user_level": verification_info["user_level"],
            },
            status=status.HTTP_200_OK,
        )
        response["Access-Control-Expose-Headers"] = "Authorization"
        response["Authorization"] = f"Bearer {verification_info['token'] }"
        return response


def generate_response(message_dict, status):
    return Response(data=message_dict, status=status)
