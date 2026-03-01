"""Tests for cache.py: file and image hashing helpers."""

from PIL import Image
from cache import get_file_hash, get_image_hash, HASH_LENGTH


# ── get_file_hash ────────────────────────────────────────────────

class TestGetFileHash:

    def test_same_bytes_same_hash(self):
        data = b"hello world"
        assert get_file_hash(data) == get_file_hash(data)

    def test_different_bytes_different_hash(self):
        assert get_file_hash(b"aaa") != get_file_hash(b"bbb")

    def test_hash_length(self):
        h = get_file_hash(b"test data")
        assert len(h) == HASH_LENGTH


# ── get_image_hash ───────────────────────────────────────────────

class TestGetImageHash:

    def test_same_image_same_hash(self):
        img = Image.new("RGB", (10, 10), color="red")
        assert get_image_hash(img) == get_image_hash(img)

    def test_different_images_different_hashes(self):
        red = Image.new("RGB", (10, 10), color="red")
        blue = Image.new("RGB", (10, 10), color="blue")
        assert get_image_hash(red) != get_image_hash(blue)
