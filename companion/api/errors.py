"""
统一错误响应工具
"""
from flask import jsonify, g, make_response


def api_success(data, status=200):
    resp = make_response(jsonify({
        "data": data,
        "error": None,
        "request_id": getattr(g, "request_id", ""),
    }))
    resp.status_code = status
    return resp


def api_error(code: str, message: str, status: int = 400, details: dict | None = None):
    resp = make_response(jsonify({
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "request_id": getattr(g, "request_id", ""),
    }))
    resp.status_code = status
    return resp
