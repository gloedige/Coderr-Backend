from unittest.mock import MagicMock

from django.http import QueryDict
from django.test import SimpleTestCase
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.api.utils import (
    decode_json_field,
    file_basename,
    handle_internal_errors,
    null_text_to_none,
)


class SharedApiUtilsTests(SimpleTestCase):
    """Test the helpers shared by the accounts and marketplace APIs."""

    def test_file_basename_returns_name_without_directory_or_none(self):
        """Return only the base name for stored files and None without a file."""
        stored = MagicMock()
        stored.name = 'uploads/photo.png'
        self.assertEqual(file_basename(stored), 'photo.png')
        self.assertIsNone(file_basename(None))

    def test_null_text_to_none_only_replaces_the_null_text(self):
        """Replace the multipart text 'null' by None and keep other values."""
        self.assertIsNone(null_text_to_none({'image': 'null'}, 'image')['image'])
        self.assertEqual(null_text_to_none({'image': 'x'}, 'image'), {'image': 'x'})

    def test_null_text_to_none_flattens_query_dicts(self):
        """Convert QueryDict input to single values before normalizing."""
        data = null_text_to_none(QueryDict('image=null&title=A'), 'image')
        self.assertEqual(data, {'image': None, 'title': 'A'})

    def test_decode_json_field_decodes_or_raises_field_error(self):
        """Decode JSON text fields and report malformed JSON as a field error."""
        self.assertEqual(decode_json_field({'d': '[1]'}, 'd', 'bad'), {'d': [1]})
        with self.assertRaises(serializers.ValidationError):
            decode_json_field({'d': '{'}, 'd', 'bad')

    def test_handle_internal_errors_sanitizes_unexpected_errors(self):
        """Return a generic 500 response for unexpected errors."""
        @handle_internal_errors('failed')
        def unexpected():
            """Raise an unexpected error."""
            raise RuntimeError('secret')

        with self.assertLogs('core.api.utils', level='ERROR'):
            response = unexpected()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {'detail': 'Internal server error.'})

    def test_handle_internal_errors_reraises_api_errors(self):
        """Let API exceptions pass through to DRF unchanged."""
        @handle_internal_errors('failed')
        def invalid():
            """Raise an API validation error."""
            raise ValidationError('bad')

        with self.assertRaises(ValidationError):
            invalid()
