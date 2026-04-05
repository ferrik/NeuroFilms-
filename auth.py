import os

ROLE_PRIORITY = {
    "anonymous": 0,
    "creator": 1,
    "moderator": 2,
    "admin": 3,
}

def resolve_role_from_api_key(api_key: str) -> str:
    if api_key and api_key == os.getenv("CREATOR_API_KEY"):
        return "creator"
    if api_key and api_key == os.getenv("MODERATOR_API_KEY"):
        return "moderator"
    if api_key and api_key == os.getenv("ADMIN_API_KEY"):
        return "admin"
    return "anonymous"

def has_required_role(current_role: str, required_role: str) -> bool:
    return ROLE_PRIORITY.get(current_role, 0) >= ROLE_PRIORITY.get(required_role, 0)
