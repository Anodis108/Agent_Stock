import os

def get_secret(name: str) -> str | None:
    """
    Retrieve a secret value by name.
    
    Local execution: reads from os.environ (which can be populated by python-dotenv).
    GCP execution: stubbed for GCP Secret Manager integration.
    
    Returns:
        str | None: The secret value if found, else None.
    """
    # Check if we should use GCP Secret Manager
    if os.environ.get("GCP_SECRET_MANAGER") == "true":
        # MVP stub: Raise NotImplementedError or return None
        # raise NotImplementedError("GCP Secret Manager integration not yet implemented.")
        return None
        
    # Default local behavior
    return os.environ.get(name)
