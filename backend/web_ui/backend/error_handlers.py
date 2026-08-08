"""
Error handling utilities for the Stock Analysis Web UI Backend.
"""

import logging
import traceback
from typing import Dict, Any
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class WebUIException(Exception):
    """Base exception for Web UI specific errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or "WEBUI_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class AgentException(WebUIException):
    """Exception for agent-related errors."""
    
    def __init__(self, message: str, agent_name: str = None, details: Dict[str, Any] = None):
        self.agent_name = agent_name
        super().__init__(message, "AGENT_ERROR", details)


class PortfolioException(WebUIException):
    """Exception for portfolio-related errors."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "PORTFOLIO_ERROR", details)


class WebSocketException(WebUIException):
    """Exception for WebSocket-related errors."""
    
    def __init__(self, message: str, client_id: str = None, details: Dict[str, Any] = None):
        self.client_id = client_id
        super().__init__(message, "WEBSOCKET_ERROR", details)


def create_error_response(
    error: Exception,
    status_code: int = 500,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error: The exception that occurred
        status_code: HTTP status code
        include_traceback: Whether to include traceback in response
        
    Returns:
        Dict containing error information
    """
    response = {
        "error": True,
        "status_code": status_code,
        "message": str(error),
        "timestamp": datetime.now().isoformat(),
        "type": type(error).__name__
    }
    
    # Add specific error details for WebUI exceptions
    if isinstance(error, WebUIException):
        response["error_code"] = error.error_code
        response["details"] = error.details
        
        if isinstance(error, AgentException) and error.agent_name:
            response["agent_name"] = error.agent_name
        elif isinstance(error, WebSocketException) and error.client_id:
            response["client_id"] = error.client_id
    
    # Add traceback if requested (for debugging)
    if include_traceback:
        response["traceback"] = traceback.format_exc()
    
    return response


def log_error(error: Exception, context: str = None, extra_data: Dict[str, Any] = None):
    """
    Log an error with context and additional data.
    
    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        extra_data: Additional data to log
    """
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or "Unknown"
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    # Add specific details for WebUI exceptions
    if isinstance(error, WebUIException):
        log_data["error_code"] = error.error_code
        log_data["error_details"] = error.details
    
    logger.error(f"Error occurred: {log_data}")
    logger.error(traceback.format_exc())


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    log_error(exc, f"HTTP {exc.status_code}", {"url": str(request.url)})
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc, exc.status_code)
    )


async def webui_exception_handler(request: Request, exc: WebUIException):
    """Handle WebUI specific exceptions."""
    status_code = 400 if isinstance(exc, (AgentException, PortfolioException)) else 500
    
    log_error(exc, "WebUI Exception", {"url": str(request.url)})
    
    return JSONResponse(
        status_code=status_code,
        content=create_error_response(exc, status_code)
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    log_error(exc, "Unhandled Exception", {"url": str(request.url)})
    
    return JSONResponse(
        status_code=500,
        content=create_error_response(exc, 500)
    )


def setup_error_handlers(app):
    """Setup error handlers for the FastAPI application."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(WebUIException, webui_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)