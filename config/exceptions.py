"""
Central exception handler so every error response has the same shape:

    {
        "success": false,
        "message": "Human readable summary.",
        "errors": { ...field -> list of messages... }      # only for validation errors
    }

Internal exceptions (database errors, bugs) are logged on the server and
replaced by a generic message; their details are never sent to the client.
"""
import logging

from django.db import DatabaseError, IntegrityError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("healthcare")


def _error_response(message, http_status, errors=None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return Response(body, status=http_status)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Not handled by DRF: database problems and unexpected bugs.
    if response is None:
        if isinstance(exc, IntegrityError):
            logger.warning("IntegrityError: %s", exc)
            return _error_response(
                "The operation conflicts with existing data.",
                status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(exc, DatabaseError):
            logger.exception("Database error")
            return _error_response(
                "A database error occurred. Please try again later.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        logger.exception("Unhandled exception")
        return _error_response(
            "An unexpected error occurred. Please try again later.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        data = response.data
        errors = data if isinstance(data, dict) else {"non_field_errors": data}
        return _error_response("Validation failed.", response.status_code, errors)

    data = response.data
    message = data.get("detail") if isinstance(data, dict) else None
    if message is None:
        message = "Request failed."
    if response.status_code == status.HTTP_404_NOT_FOUND:
        message = "Resource not found."
    return _error_response(str(message), response.status_code)
