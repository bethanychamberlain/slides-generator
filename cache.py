"""File and slide caching logic for analysis results."""

import json
import hashlib
import shutil
from pathlib import Path

# Cache directory for storing analysis results
CACHE_DIR = Path(__file__).parent / "analysis_cache"

HASH_LENGTH = 16


def get_file_hash(file_bytes):
    """Generate a hash of file contents for cache lookup."""
    return hashlib.sha256(file_bytes).hexdigest()[:HASH_LENGTH]


def get_image_hash(image):
    """Generate a hash of an image for per-slide cache lookup.

    Uses raw pixel data for speed — avoids PNG encoding overhead.
    """
    return hashlib.sha256(image.tobytes()).hexdigest()[:HASH_LENGTH]


def get_cache_path(file_hash):
    """Get the path to a cached analysis file."""
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / f"{file_hash}.json"


def get_slide_cache_path():
    """Get the path to the per-slide image hash cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / "_slide_image_cache.json"


def load_slide_cache():
    """Load the per-slide image hash cache."""
    cache_path = get_slide_cache_path()
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_slide_cache(cache):
    """Save the per-slide image hash cache."""
    cache_path = get_slide_cache_path()
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)


def get_cached_questions_for_image(image):
    """Check if we have cached questions for this exact image."""
    image_hash = get_image_hash(image)
    slide_cache = load_slide_cache()
    return slide_cache.get(image_hash), image_hash


def save_questions_for_image(image_hash, questions):
    """Save questions for a specific image hash."""
    slide_cache = load_slide_cache()
    slide_cache[image_hash] = questions
    save_slide_cache(slide_cache)


def load_from_cache(file_hash):
    """Load cached analysis results if available."""
    cache_path = get_cache_path(file_hash)
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_to_cache(file_hash, data):
    """Save analysis results to cache."""
    cache_path = get_cache_path(file_hash)
    CACHE_DIR.mkdir(exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(data, f, indent=2)


def clear_cache():
    """Clear all cached analysis results."""
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(exist_ok=True)
