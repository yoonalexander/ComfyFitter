from io import BytesIO
import hashlib

from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .errors import AppError


async def read_image(upload, settings):
    data = bytearray()
    while chunk := await upload.read(64 * 1024):
        data.extend(chunk)
        if len(data) > settings.max_image_bytes:
            raise AppError(413, 'IMAGE_TOO_LARGE', f'Each image must be at most {settings.max_image_bytes} bytes.')
    return await run_in_threadpool(normalize, bytes(data), settings)


def normalize(data, settings):
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in ('PNG', 'JPEG', 'WEBP') or getattr(image, 'n_frames', 1) != 1:
                raise AppError(422, 'UNSUPPORTED_IMAGE', 'Use a single-frame PNG, JPEG or WebP image.')
            if image.width * image.height > settings.max_image_pixels:
                raise AppError(422, 'IMAGE_PIXELS_EXCEEDED', 'Image dimensions exceed the configured pixel limit.')
            image.load()
            original_size = list(image.size)
            orientation = image.getexif().get(274, 1)
            oriented = ImageOps.exif_transpose(image).convert('RGBA')
            canvas = Image.new('RGB', oriented.size, 'white')
            canvas.paste(oriented, mask=oriented.getchannel('A'))
            output = BytesIO()
            canvas.save(output, format='PNG')
            normalized = output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise AppError(422, 'INVALID_IMAGE', 'Upload a decodable PNG, JPEG or WebP image.') from None
    return {'bytes': normalized, 'original_sha256': hashlib.sha256(data).hexdigest(),
            'sha256': hashlib.sha256(normalized).hexdigest(), 'original_size': original_size,
            'size': list(canvas.size), 'exif_orientation': orientation,
            'preprocessing': 'EXIF transpose; alpha on white; RGB PNG; metadata stripped'}
