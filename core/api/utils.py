import json
import logging
from functools import wraps

from django.db import transaction
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response


logger = logging.getLogger(__name__)
MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG'}


def internal_error_response(message):
    """Log the active exception under `message` and return the generic 500 response."""
    logger.exception(message)
    return Response(
        {'detail': 'Internal server error.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def handle_internal_errors(message):
    """Decorate a function so unexpected exceptions become the generic 500 response."""
    def decorator(func):
        """Wrap `func` with the error handling described by the outer decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Call `func`, re-raising API errors and sanitizing all other exceptions."""
            try:
                return func(*args, **kwargs)
            except APIException:
                raise
            except Exception:
                return internal_error_response(message)
        return wrapper
    return decorator


def file_basename(file_field):
    """Return the stored file's base name, or None when no file is set."""
    return file_field.name.rsplit('/', 1)[-1] if file_field else None


def schedule_replaced_file_deletion(previous_file, current_file):
    """After commit, delete `previous_file` from storage if `current_file` no longer uses its name."""
    previous_name = previous_file.name if previous_file else None
    current_name = current_file.name if current_file else None
    if previous_name and previous_name != current_name:
        transaction.on_commit(lambda: previous_file.storage.delete(previous_name), robust=True)


def validate_image_upload(value):
    """Validate an uploaded JPEG/PNG of at most 5 MB and return it rewound, or None."""
    if value is None:
        return value
    if value.size > MAX_IMAGE_SIZE:
        raise serializers.ValidationError('Image must not exceed 5 MB.')
    try:
        image = Image.open(value)
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise serializers.ValidationError('Only valid JPEG and PNG images are accepted.') from exc
    if image.format not in ALLOWED_IMAGE_FORMATS:
        raise serializers.ValidationError('Only JPEG and PNG images are accepted.')
    value.seek(0)
    return value


def as_plain_dict(data):
    """Flatten a QueryDict to a plain dict of single values; return other input unchanged."""
    return data.dict() if hasattr(data, 'getlist') else data


def null_text_to_none(data, field):
    """Return `data` where the multipart text 'null' in `field` is replaced by None."""
    data = as_plain_dict(data)
    if hasattr(data, 'get') and data.get(field) == 'null':
        data = dict(data)
        data[field] = None
    return data


def decode_json_field(data, field, message):
    """Return `data` with the JSON-encoded text `field` decoded, or raise a field error."""
    data = as_plain_dict(data)
    if not (hasattr(data, 'get') and isinstance(data.get(field), str)):
        return data
    data = dict(data)
    try:
        data[field] = json.loads(data[field])
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError({field: message}) from exc
    return data
