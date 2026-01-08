# SECURE: Environment Variables for Secrets
# This code uses environment variables to store sensitive data

import os

# SECURE: Load from environment variables
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")

# SECURE: Environment variable with default (for non-sensitive config)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///default.db')

# SECURE: Use environment variables for credentials
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

def connect_to_api():
    """SECURE: Uses environment variable for API key"""
    if not API_KEY:
        raise ValueError("API_KEY not configured")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    # API call here
    return headers

