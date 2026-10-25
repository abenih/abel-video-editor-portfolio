"""Shrink uploaded pictures so the owner never has to think about file size.

A 2MB phone or AI-generated PNG is normal to upload and ruinous to serve: five of
them made the home page 10MB. Everything here runs at upload time so the owner
just picks a file and the site stays fast.
"""

from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps

# Big enough for a full-width hero on a 2x display, small enough to stay cheap.
MAX_EDGE = 1800
WEBP_QUALITY = 82
# Below this a re-encode usually costs more bytes than it saves.
SKIP_UNDER_BYTES = 120 * 1024


def optimize_image(uploaded, max_edge=MAX_EDGE):
    """Return a WebP version of `uploaded`, or the original if shrinking won't help.

    Never raises on a file Pillow cannot read - the form's own validation is what
    rejects bad uploads, and this must not turn a validation error into a 500.
    """
    if not uploaded or not getattr(uploaded, 'size', 0):
        return uploaded
    if uploaded.size < SKIP_UNDER_BYTES:
        return uploaded

    try:
        uploaded.seek(0)
        image = Image.open(uploaded)
        # Phone photos carry rotation in EXIF; bake it in before we drop the metadata.
        image = ImageOps.exif_transpose(image)
        image.load()
    except Exception:
        uploaded.seek(0)
        return uploaded

    # WebP keeps alpha, so logos and cut-outs survive the conversion.
    image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')

    if max(image.size) > max_edge:
        image.thumbnail((max_edge, max_edge), Image.LANCZOS)

    buffer = BytesIO()
    try:
        image.save(buffer, format='WEBP', quality=WEBP_QUALITY, method=6)
    except Exception:
        uploaded.seek(0)
        return uploaded

    if buffer.tell() >= uploaded.size:
        uploaded.seek(0)
        return uploaded

    name = uploaded.name.rsplit('/', 1)[-1].rsplit('.', 1)[0] + '.webp'
    buffer.seek(0)
    return InMemoryUploadedFile(
        buffer, getattr(uploaded, 'field_name', None), name,
        'image/webp', buffer.getbuffer().nbytes, None,
    )
