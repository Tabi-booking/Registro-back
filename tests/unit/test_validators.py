from __future__ import annotations

import pytest

from app.utils.validators import (
    validate_business_hours,
    validate_file_size,
    validate_mime_type,
    validate_phone_number,
    validate_storage_key,
)


class TestPhoneValidation:
    def test_valid_colombian_phone(self):
        result = validate_phone_number("+573001234567")
        assert result == "+573001234567"

    def test_valid_us_phone(self):
        result = validate_phone_number("+12125551234")
        assert result == "+12125551234"

    def test_invalid_phone_no_country_code(self):
        with pytest.raises(ValueError, match="E.164"):
            validate_phone_number("3001234567")

    def test_invalid_phone_garbage(self):
        with pytest.raises(ValueError):
            validate_phone_number("not-a-phone")

    def test_phone_normalizes_format(self):
        # Various formats of same number
        result = validate_phone_number("+57 300 123 4567")
        assert result.startswith("+57")


class TestBusinessHours:
    def test_valid_hours(self):
        assert validate_business_hours("08:00", "22:00") is True

    def test_same_time_raises(self):
        with pytest.raises(ValueError, match="after opening"):
            validate_business_hours("08:00", "08:00")

    def test_closing_before_opening_raises(self):
        with pytest.raises(ValueError, match="after opening"):
            validate_business_hours("22:00", "08:00")

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            validate_business_hours("8am", "10pm")


class TestMimeTypeValidation:
    def test_valid_image_jpeg(self):
        assert validate_mime_type("image/jpeg") is True

    def test_valid_image_png(self):
        assert validate_mime_type("image/png") is True

    def test_valid_pdf(self):
        assert validate_mime_type("application/pdf") is True

    def test_invalid_mime_type(self):
        assert validate_mime_type("application/exe") is False

    def test_invalid_text_html(self):
        assert validate_mime_type("text/html") is False

    def test_custom_allowed_set(self):
        allowed = frozenset({"image/jpeg"})
        assert validate_mime_type("image/jpeg", allowed) is True
        assert validate_mime_type("image/png", allowed) is False


class TestFileSizeValidation:
    def test_valid_size(self):
        assert validate_file_size(1024 * 1024) is True  # 1 MB

    def test_max_boundary(self):
        assert validate_file_size(10 * 1024 * 1024) is True  # exactly 10 MB

    def test_exceeds_max(self):
        assert validate_file_size(10 * 1024 * 1024 + 1) is False

    def test_zero_size(self):
        assert validate_file_size(0) is False

    def test_negative_size(self):
        assert validate_file_size(-1) is False


class TestStorageKeyValidation:
    def test_valid_key(self):
        assert validate_storage_key("restaurants/123/logo/abc_image.jpg") is True

    def test_path_traversal(self):
        assert validate_storage_key("restaurants/../etc/passwd") is False

    def test_empty_key(self):
        assert validate_storage_key("") is False

    def test_special_chars(self):
        assert validate_storage_key("restaurants/123/<script>") is False
