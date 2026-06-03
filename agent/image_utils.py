"""Bildeforbehandling med Pillow før opplasting til Claude vision.

Retter EXIF-orientering, konverterer farger, nedskalerer lengste kant og
komprimerer slik at det kodede bildet holder seg innenfor API-grensene.
Returnerer alltid riktig ``media_type`` (ikke hardkodet til JPEG).
"""

import base64
import io
from pathlib import Path

from PIL import Image, ImageOps

from agent import config

_PIL_TO_MEDIA = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def _detect_media_type(img_format: str | None) -> str:
    return _PIL_TO_MEDIA.get((img_format or "").upper(), "image/jpeg")


def prepare_image(
    path,
    max_edge: int = config.IMAGE_MAX_EDGE,
    target_bytes: int = config.IMAGE_TARGET_BYTES,
) -> tuple[str, str]:
    """Laster, roterer riktig, nedskalerer og komprimerer et bilde.

    Returnerer ``(base64_data, media_type)``.
    """
    path = Path(path)
    with Image.open(path) as img:
        src_format = (img.format or "").upper()
        img = ImageOps.exif_transpose(img)  # rett opp orientering fra EXIF

        # Behold PNG for grafikk/skjermbilder; ellers normaliser til JPEG.
        keep_png = src_format == "PNG"
        if keep_png:
            if img.mode == "P":
                img = img.convert("RGBA")
        elif img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        # Nedskaler lengste kant.
        longest = max(img.size)
        if longest > max_edge:
            scale = max_edge / longest
            new_size = (
                max(1, int(img.width * scale)),
                max(1, int(img.height * scale)),
            )
            img = img.resize(new_size, Image.LANCZOS)

        if keep_png:
            data = _encode_png(img, target_bytes)
            media_type = "image/png"
        else:
            data = _encode_jpeg(img, target_bytes)
            media_type = "image/jpeg"

    return base64.standard_b64encode(data).decode("ascii"), media_type


def _encode_jpeg(img: Image.Image, target_bytes: int) -> bytes:
    """Koder som JPEG; senker kvalitet og deretter størrelse til under målet."""
    quality = config.JPEG_QUALITY
    data = b""
    for _ in range(20):  # garantert terminering
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= target_bytes:
            return data
        if quality > 45:
            quality -= 10
        elif max(img.size) > 256:
            img = img.resize(
                (max(1, int(img.width * 0.8)), max(1, int(img.height * 0.8))),
                Image.LANCZOS,
            )
        else:
            break
    return data


def _encode_png(img: Image.Image, target_bytes: int) -> bytes:
    """Koder som PNG; nedskalerer ved behov for å holde størrelsen i sjakk."""
    data = b""
    for _ in range(10):
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()
        if len(data) <= target_bytes or max(img.size) <= 256:
            return data
        img = img.resize(
            (max(1, int(img.width * 0.8)), max(1, int(img.height * 0.8))),
            Image.LANCZOS,
        )
    return data
