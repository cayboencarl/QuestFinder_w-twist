"""Safe image uploads.

Every image is opened with Pillow (so non-images are rejected even if they are
renamed), resized, stripped of metadata such as GPS EXIF tags, and re-saved as
JPEG under a random name. Files go to instance/uploads/<kind>/, which is not
publicly served; see blueprints/files for access-checked serving.
"""
import io
import os
import secrets

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

KINDS = {"avatars", "quests", "chat", "verification"}
MAX_SIDE = {"avatars": 512, "quests": 1600, "chat": 1600, "verification": 1600}


class UploadError(Exception):
    pass


def _folder(kind: str) -> str:
    if kind not in KINDS:
        raise ValueError(f"unknown upload kind {kind}")
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], kind)
    os.makedirs(path, exist_ok=True)
    return path


def save_image(file_storage_or_bytes, kind: str) -> str:
    """Validate, clean and store an image. Returns the stored file name."""
    if file_storage_or_bytes is None:
        raise UploadError("No image was provided.")
    if isinstance(file_storage_or_bytes, (bytes, bytearray)):
        raw = bytes(file_storage_or_bytes)
        filename = "upload.jpg"
    else:
        filename = file_storage_or_bytes.filename or ""
        raw = file_storage_or_bytes.read()
    if not raw:
        raise UploadError("The image is empty.")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext and ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"] | {"blob"}:
        raise UploadError("Only JPG, PNG or WEBP images are allowed.")

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()  # detects truncated / fake files
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)  # respect phone rotation, then drop EXIF
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise UploadError("That file is not a valid image.")

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    side = MAX_SIDE[kind]
    img.thumbnail((side, side))

    name = f"{secrets.token_hex(16)}.jpg"
    img.save(os.path.join(_folder(kind), name), "JPEG", quality=85, optimize=True)
    return name


def path_for(kind: str, name: str) -> str:
    """Absolute path of a stored file (name is validated to prevent path traversal)."""
    if not name or os.path.basename(name) != name or not name.endswith(".jpg"):
        raise UploadError("Invalid file name.")
    return os.path.join(_folder(kind), name)


def delete(kind: str, name: str | None) -> None:
    if not name:
        return
    try:
        os.remove(path_for(kind, name))
    except (OSError, UploadError):
        pass
