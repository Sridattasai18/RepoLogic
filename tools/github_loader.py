import requests
import logging
from pathlib import Path
from typing import Optional
from .constants import IGNORE_DIRS, IGNORE_EXTS
from config import Config

logger = logging.getLogger(__name__)

def _normalize_github_url(url: str) -> str:
    """
    Normalizes GitHub URL to root repository format.
    Strips /tree/branch/path, /blob/..., etc. to get the clone URL.
    
    Examples:
    - https://github.com/user/repo/tree/main/src -> https://github.com/user/repo
    - https://github.com/user/repo.git -> https://github.com/user/repo
    """
    url = url.rstrip("/").removesuffix(".git")
    
    # Strip path segments after repo name
    if "/tree/" in url or "/blob/" in url:
        url = url.split("/tree/")[0].split("/blob/")[0]
    
    return url

def validate_github_url(url: str) -> bool:
    """
    Validates if the URL is a reachable public GitHub repository.
    """
    if not url.startswith("https://github.com/"):
        logger.warning(f"Invalid URL format: {url}")
        return False
    
    # Normalize to root repo URL
    clean_url = _normalize_github_url(url)
    
    try:
        response = requests.head(clean_url, timeout=5)
        if response.status_code == 200:
            return True
        logger.warning(f"Repo not reachable (Status {response.status_code}): {url}")
        return False
    except Exception as e:
        logger.error(f"Error validating URL {url}: {e}")
        return False

def get_repo_id(url: str) -> str:
    """Generates a unique ID for the repo based on 'owner_repo'."""
    clean_url = _normalize_github_url(url)
    parts = clean_url.split("/")[-2:]
    return f"{parts[0]}_{parts[1]}"

