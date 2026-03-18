"""Standardized error handling utilities."""
import logging
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("aegisais.errors")


class AegisAISError(Exception):
    """Base exception for AegisAIS application errors."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AegisAISError):
    """Raised when input validation fails."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status_code=400, details=details)


class NotFoundError(AegisAISError):
    """Raised when a resource is not found."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status_code=404, details=details)


class DatabaseError(AegisAISError):
    """Raised when a database operation fails."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status_code=500, details=details)


def handle_database_error(e: SQLAlchemyError, context: str = "") -> HTTPException:
    """
    Convert SQLAlchemy errors to HTTP exceptions with proper logging.
    
    Args:
        e: SQLAlchemy exception
        context: Additional context for logging
    
    Returns:
        HTTPException with appropriate status code
    """
    log.error("Database error%s: %s", f" ({context})" if context else "", str(e), exc_info=True)
    return HTTPException(
        status_code=500,
        detail=f"Database error: {str(e)}"
    )


def handle_application_error(e: AegisAISError, context: str = "") -> HTTPException:
    """
    Convert application errors to HTTP exceptions with proper logging.
    
    Args:
        e: AegisAISError exception
        context: Additional context for logging
    
    Returns:
        HTTPException with appropriate status code
    """
    log_level = log.warning if e.status_code < 500 else log.error
    log_level("Application error%s: %s", f" ({context})" if context else "", str(e), exc_info=True)
    
    return HTTPException(
        status_code=e.status_code,
        detail=e.message
    )


def handle_unexpected_error(e: Exception, context: str = "") -> HTTPException:
    """
    Handle unexpected exceptions with proper logging.
    
    Args:
        e: Unexpected exception
        context: Additional context for logging
    
    Returns:
        HTTPException with 500 status code
    """
    log.error("Unexpected error%s: %s", f" ({context})" if context else "", str(e), exc_info=True)
    return HTTPException(
        status_code=500,
        detail="An unexpected error occurred. Please check server logs for details."
    )
