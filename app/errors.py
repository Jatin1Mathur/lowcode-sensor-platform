"""Consistent JSON error format for every endpoint.

{"error": {"code": "...", "message": "...", "details": [...]}}
"""

from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: list | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []


def error_response(status: int, code: str, message: str, details: list | None = None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return error_response(err.status, err.code, err.message, err.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        code = (err.name or "error").lower().replace(" ", "_")
        return error_response(err.code or 500, code, err.description or err.name)

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        app.logger.exception("Unhandled error")
        return error_response(500, "internal_error", "Unexpected server error")
