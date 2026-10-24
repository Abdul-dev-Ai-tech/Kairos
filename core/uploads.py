from io import BytesIO
from uuid import uuid4
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.base import ContentFile

Image.MAX_IMAGE_PIXELS = 20_000_000

def upload_path(instance, filename):
    return f'images/{uuid4().hex}{Path(filename).suffix.lower()}'

def validate_image(file):
    limit = settings.MAX_IMAGE_UPLOAD_BYTES
    if file.size > limit:
        raise ValidationError(f'Image must be {limit // (1024 * 1024)} MB or smaller for this deployment.')
    if Path(file.name).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
        raise ValidationError('Upload a JPG, PNG or WebP image. SVG files are not accepted.')
    try:
        file.seek(0)
        with Image.open(file) as image:
            if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise ValidationError('Unsupported image format.')
            if image.width * image.height > 20_000_000 or max(image.size) > 6000:
                raise ValidationError('Image dimensions are too large (maximum 6000 px / 20 MP).')
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError('Invalid or unsafe image.')
    finally:
        file.seek(0)

def optimized(file, size, output_format='WEBP'):
    validate_image(file)
    file.seek(0)
    with Image.open(file) as image:
        image = ImageOps.exif_transpose(image).convert('RGBA')
        image.info.clear()
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        out = BytesIO()
        if output_format == 'PNG':
            image.save(out, 'PNG', optimize=True)
        else:
            image.save(out, 'WEBP', quality=86, method=6)
    file.seek(0)
    return ContentFile(out.getvalue(), name=f'{uuid4().hex}.{output_format.lower()}')

class OptimizedImageMixin:
    image_fields = ()

    def save(self, *args, **kwargs):
        for name in self.image_fields:
            file = getattr(self, name)
            if file and not file._committed:
                # PNG retains transparency and wider email-client support for
                # branding; photographic assets use compressed WebP.
                setattr(self, name, optimized(file, 1920, 'PNG' if name in {'logo', 'favicon'} else 'WEBP'))
        super().save(*args, **kwargs)
