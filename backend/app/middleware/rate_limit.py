"""Rate limiting middleware for API endpoints."""
import time
from collections import defaultdict
from typing import Callable
from fastapi import Request, HTTPException, status

# Simple in-memory rate limiter
# For production, use Redis or similar
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

def rate_limit(max_requests: int = 100, window_seconds: int = 60) -> Callable:
    """
    Rate limiting decorator.
    
    Args:
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(request: Request, *args, **kwargs):
            # Get client identifier (IP address)
            client_ip = request.client.host if request.client else "unknown"
            key = f"{client_ip}:{func.__name__}"
            
            current_time = time.time()
            
            # Clean old entries
            _rate_limit_store[key] = [
                timestamp for timestamp in _rate_limit_store[key]
                if current_time - timestamp < window_seconds
            ]
            
            # Check rate limit
            if len(_rate_limit_store[key]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds"
                )
            
            # Record this request
            _rate_limit_store[key].append(current_time)
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator
