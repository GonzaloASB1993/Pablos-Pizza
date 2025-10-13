"""
HTTP Response Utilities
Standardized JSON responses with proper CORS headers
"""
from flask import jsonify


def json_response(data, status_code=200):
    """
    Create standardized JSON response

    Args:
        data: Response data (dict, list, or any JSON-serializable object)
        status_code: HTTP status code (default: 200)

    Returns:
        tuple: (response, status_code)
    """
    response = jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response, status_code


def error_response(error_message: str, status_code=400, details=None):
    """
    Create standardized error response

    Args:
        error_message: Error message
        status_code: HTTP status code (default: 400)
        details: Additional error details (optional)

    Returns:
        tuple: (response, status_code)
    """
    error_data = {
        "error": error_message,
        "status": "error"
    }

    if details:
        error_data["details"] = details

    return json_response(error_data, status_code)


def success_response(message: str, data=None, status_code=200):
    """
    Create standardized success response

    Args:
        message: Success message
        data: Response data (optional)
        status_code: HTTP status code (default: 200)

    Returns:
        tuple: (response, status_code)
    """
    response_data = {
        "message": message,
        "status": "success"
    }

    if data is not None:
        response_data["data"] = data

    return json_response(response_data, status_code)


def created_response(resource_type: str, resource_id: str, data=None):
    """
    Create standardized creation response (201)

    Args:
        resource_type: Type of resource created (e.g., "booking", "event")
        resource_id: ID of created resource
        data: Full resource data (optional)

    Returns:
        tuple: (response, 201)
    """
    response_data = {
        "message": f"{resource_type.capitalize()} created successfully",
        "status": "success",
        "id": resource_id
    }

    if data is not None:
        response_data["data"] = data

    return json_response(response_data, 201)


def not_found_response(resource_type: str, resource_id: str = None):
    """
    Create standardized not found response (404)

    Args:
        resource_type: Type of resource (e.g., "booking", "event")
        resource_id: ID of resource (optional)

    Returns:
        tuple: (response, 404)
    """
    message = f"{resource_type.capitalize()} not found"
    if resource_id:
        message += f": {resource_id}"

    return error_response(message, 404)
