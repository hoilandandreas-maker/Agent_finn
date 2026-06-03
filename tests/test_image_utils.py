"""Tester for bildeforbehandling (Pillow). Bruker syntetiske bilder i minnet."""

import base64
import io

from PIL import Image

from agent import config, image_utils


def _lagre(tmp_path, img, fmt, navn):
    suffix = {"JPEG": "jpg", "PNG": "png"}[fmt]
    sti = tmp_path / f"{navn}.{suffix}"
    img.save(sti, format=fmt)
    return sti


def test_detect_media_type():
    assert image_utils._detect_media_type("JPEG") == "image/jpeg"
    assert image_utils._detect_media_type("PNG") == "image/png"
    assert image_utils._detect_media_type("WEBP") == "image/webp"
    assert image_utils._detect_media_type(None) == "image/jpeg"
    assert image_utils._detect_media_type("GIF") == "image/jpeg"


def test_downscale_large_jpeg(tmp_path):
    img = Image.new("RGB", (4000, 3000), (123, 50, 200))
    sti = _lagre(tmp_path, img, "JPEG", "stor")

    b64, media = image_utils.prepare_image(sti)

    assert media == "image/jpeg"
    raw = base64.standard_b64decode(b64)
    assert len(raw) < config.IMAGE_HARD_LIMIT_BYTES
    with Image.open(io.BytesIO(raw)) as ut:
        assert max(ut.size) <= config.IMAGE_MAX_EDGE


def test_png_beholdes(tmp_path):
    img = Image.new("RGB", (200, 200), (10, 20, 30))
    sti = _lagre(tmp_path, img, "PNG", "graf")

    _, media = image_utils.prepare_image(sti)

    assert media == "image/png"


def test_rgba_png_uten_krasj(tmp_path):
    img = Image.new("RGBA", (300, 300), (10, 20, 30, 128))
    sti = _lagre(tmp_path, img, "PNG", "gjennomsiktig")

    b64, media = image_utils.prepare_image(sti)

    assert media == "image/png"
    assert len(base64.standard_b64decode(b64)) > 0


def test_liten_jpeg_uendret_format(tmp_path):
    img = Image.new("RGB", (100, 80), (200, 200, 200))
    sti = _lagre(tmp_path, img, "JPEG", "liten")

    b64, media = image_utils.prepare_image(sti)

    assert media == "image/jpeg"
    with Image.open(io.BytesIO(base64.standard_b64decode(b64))) as ut:
        assert ut.size == (100, 80)  # ikke nedskalert
