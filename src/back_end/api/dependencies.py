"""
src/back_end/api/dependencies.py
Dependencies for FastAPI endpoints, including authentication.
"""

import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Dependency to validate the API key passed in the headers.
    Used to protect sensitive endpoints from unauthorized access.
    """
    # For security, the API key must be provided in .env
    valid_api_key = os.getenv("API_KEY", "your-secure-api-key-here")
    
    if api_key_header == valid_api_key:
        return api_key_header
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )
