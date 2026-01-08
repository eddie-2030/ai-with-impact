# INSECURE: Hard-coded Secrets
# This code contains hard-coded API keys and passwords

# VULNERABLE: Hard-coded API key
API_KEY = "example_api_key_1234567890abcdefghijklmnop"

# VULNERABLE: Hard-coded password
DATABASE_PASSWORD = "MySecretPassword123!"

# VULNERABLE: Hard-coded credentials
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

def connect_to_api():
    """INSECURE: Uses hard-coded API key"""
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    # API call here
    return headers

