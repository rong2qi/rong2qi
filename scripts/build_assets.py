#!/usr/bin/env python3
"""Build the selected Nüwa A profile artwork into deterministic README assets."""

from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SOURCE = ROOT / "assets/source/nuwa-a-sky-rift.png"
MASTER_SHA256 = "2f61ae115f1c3f6924bb7db23868d8324f73754bb632d60cb91760e609b965c1"
LABEL_FONT = Path("/System/Library/Fonts/SFNS.ttf")
DATE_FONT = Path("/System/Library/Fonts/Noteworthy.ttc")

NIGHT = (17, 19, 26)
BONE = (211, 203, 194)

HERO_SPECS = {
    "hero.jpg": {
        "crop": (0, 0, 1536, 1024),
        "size": (1200, 800),
        "mobile": False,
        "quality": 89,
        "role": "desktop full A composition and reduced-motion fallback",
    },
    "hero-mobile.jpg": {
        "crop": (360, 0, 1384, 1024),
        "size": (768, 768),
        "mobile": True,
        "quality": 89,
        "role": "mobile A crop retaining sky seam, Nüwa, stone, river and clay figures",
    },
}

CARD_SPECS = {
    "work-fish.jpg": {
        "crop": (350, 440, 930, 1020),
        "lines": ("fish-meditate",),
        "role": "river light",
    },
    "work-jinbao.jpg": {
        "crop": (600, 540, 1084, 1024),
        "lines": ("desktop-pet-jinbao",),
        "role": "clay companions and distant water",
    },
    "work-orchestrator.jpg": {
        "crop": (380, 0, 960, 580),
        "lines": ("prompt-agent-", "orchestrator"),
        "role": "red thread, mineral fragments and repaired sky",
    },
    "work-speakloop.jpg": {
        "crop": (900, 20, 1480, 600),
        "lines": ("SpeakLoop",),
        "role": "flowing hair and returning warm light",
    },
    "work-chief.jpg": {
        "crop": (120, 0, 700, 580),
        "lines": ("chief-of-staff-codex",),
        "role": "fractured sky and mountains",
    },
}

STATIC_OUTPUTS = tuple(HERO_SPECS) + (
    "works.jpg",
    "works-mobile.jpg",
    *CARD_SPECS,
    "ashes-trace.jpg",
    "ashes-trace-mobile.jpg",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_master():
    assert SOURCE.is_file(), f"Missing selected master: {SOURCE}"
    assert sha(SOURCE) == MASTER_SHA256, "Selected Candidate A source drift"
    image = Image.open(SOURCE)
    assert image.format == "PNG" and image.size == (1536, 1024)
    return image.convert("RGB")


def crop_resize(image, box, size):
    return image.crop(box).resize(size, Image.Resampling.LANCZOS)


def font(path, size):
    assert path.is_file(), f"Missing local rasterization font: {path}"
    return ImageFont.truetype(str(path), size)


def draw_text(draw, xy, value, selected_font, fill):
    x, y = xy
    draw.text((x + 1, y + 1), value, font=selected_font, fill=(0, 0, 0, min(fill[3], 150)))
    draw.text((x, y), value, font=selected_font, fill=fill)


def hero_label_overlay(size, mobile):
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if mobile:
        scale = size[0] / 768
        identity = font(LABEL_FONT, round(42 * scale))
        small = font(LABEL_FONT, round(36 * scale))
        handwritten = font(DATE_FONT, round(36 * scale))
        draw_text(draw, (round(28 * scale), round(215 * scale)), "rong2qi", identity, (*BONE, 210))
        draw_text(draw, (round(29 * scale), round(264 * scale)), "now", small, (*BONE, 178))
        draw_text(
            draw,
            (round(29 * scale), round(701 * scale)),
            "2026 · 09 · 11",
            handwritten,
            (*BONE, 156),
        )
    else:
        scale = size[0] / 1200
        identity = font(LABEL_FONT, round(30 * scale))
        small = font(LABEL_FONT, round(22 * scale))
        handwritten = font(DATE_FONT, round(22 * scale))
        draw_text(draw, (round(38 * scale), round(30 * scale)), "rong2qi", identity, (*BONE, 205))
        draw_text(draw, (round(39 * scale), round(68 * scale)), "now", small, (*BONE, 170))
        draw_text(
            draw,
            (round(39 * scale), round(735 * scale)),
            "2026 · 09 · 11",
            handwritten,
            (*BONE, 150),
        )
    return overlay


def add_hero_labels(image, mobile):
    result = image.convert("RGBA")
    overlay = hero_label_overlay(result.size, mobile)
    return Image.alpha_composite(result, overlay).convert("RGB")


def build_hero(master, spec, labels=True):
    image = crop_resize(master, spec["crop"], spec["size"])
    if labels:
        image = add_hero_labels(image, spec["mobile"])
    return image


def fade_to_night(image, start):
    array = np.asarray(image, dtype=np.float32)
    height = array.shape[0]
    blend = np.clip((np.arange(height, dtype=np.float32) - start) / (height - start), 0, 1)
    blend = (blend * blend * (3 - 2 * blend))[:, None, None]
    night = np.empty_like(array)
    night[:] = NIGHT
    return Image.fromarray(np.clip(np.rint(array * (1 - blend) + night * blend), 0, 255).astype("uint8"))


def build_card(master, spec):
    fragment = crop_resize(master, spec["crop"], (480, 500))
    fragment = fade_to_night(fragment, 398)
    canvas = Image.new("RGB", (480, 600), NIGHT)
    canvas.paste(fragment, (0, 0))
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    label_font = font(LABEL_FONT, 45)
    lines = spec["lines"]
    first_y = 492 if len(lines) == 2 else 516
    for index, line in enumerate(lines):
        draw_text(draw, (14, first_y + index * 47), line, label_font, (*BONE, 224))
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def build_works(master, mobile=False):
    strip = crop_resize(master, (0, 360, 1536, 522), (1024, 108))
    strip = Image.blend(strip, Image.new("RGB", strip.size, NIGHT), 0.58)
    overlay = Image.new("RGBA", strip.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    size = 48 if mobile else 27
    y = 24 if mobile else 35
    draw_text(draw, (40, y), "works", font(LABEL_FONT, size), (*BONE, 220))
    return Image.alpha_composite(strip.convert("RGBA"), overlay).convert("RGB")


def build_footer(master, mobile=False):
    image = crop_resize(master, (160, 470, 1536, 850), (1024, 283))
    array = np.asarray(image, dtype=np.float32)
    array = array * 0.72 + np.asarray(NIGHT, dtype=np.float32) * 0.28
    x = np.linspace(0, 1, array.shape[1], dtype=np.float32)
    left_veil = np.clip((0.56 - x) / 0.42, 0, 1)
    left_veil = (left_veil * left_veil * (3 - 2 * left_veil))[None, :, None]
    array = array * (1 - 0.76 * left_veil) + np.asarray(NIGHT) * (0.76 * left_veil)
    image = Image.fromarray(np.clip(np.rint(array), 0, 255).astype("uint8"))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    label_font = font(LABEL_FONT, 48 if mobile else 30)
    draw_text(draw, (40, 28 if mobile else 38), "ashes", label_font, (*BONE, 215))
    draw_text(draw, (40, 220 if mobile else 230), "trace", label_font, (*BONE, 195))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def save_jpeg(image, path, quality):
    image.save(
        path,
        format="JPEG",
        quality=quality,
        subsampling=0,
        optimize=True,
        progressive=False,
        exif=b"",
    )


def write_manifest():
    assets = []
    roles = {
        **{name: spec["role"] for name, spec in HERO_SPECS.items()},
        "works.jpg": "painterly section marker",
        "works-mobile.jpg": "painterly section marker with mobile-readable label",
        **{name: spec["role"] for name, spec in CARD_SPECS.items()},
        "ashes-trace.jpg": "dark river and mountain trace with open writing space",
        "ashes-trace-mobile.jpg": "dark river and mountain trace with mobile-readable labels",
    }
    for name in STATIC_OUTPUTS:
        path = ASSETS / name
        with Image.open(path) as image:
            width, height = image.size
            file_format = image.format
        assets.append(
            {
                "file": name,
                "role": roles[name],
                "format": file_format,
                "width": width,
                "height": height,
                "bytes": path.stat().st_size,
                "sha256": sha(path),
            }
        )
    manifest = {
        "schema": 2,
        "candidate_label": "PROFILE-NUWA-A-20260911-01",
        "style": "女娲 · A 天裂 / Nüwa sky rift",
        "method": (
            "User-selected built-in ImageGen master A; deterministic local crops, "
            "tone-preserving raster derivatives and minimal rasterized labels; no remote resources"
        ),
        "source": {
            "file": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": MASTER_SHA256,
            "width": 1536,
            "height": 1024,
            "origin": "Codex built-in ImageGen, selected by the user with: A最好看。",
            "prompt_summary": (
                "Original Nüwa repairing the sky: feminine upper body and serpentine lower form "
                "on the right, muted five-colored stone, dark-red repair thread, dark negative "
                "space on the left, mineral sky, river and clay figures; painterly paper grain; "
                "no copied figure, clothing, composition, signature or watermark."
            ),
        },
        "labels": {
            "desktop_source_width": 1200,
            "mobile_source_width": 768,
            "public_mobile_canvas_width": 308,
            "mobile_min_font_px": 36,
            "section_source_width": 1024,
            "desktop_section_font_px": 27,
            "mobile_section_font_px": 48,
            "card_source_width": 480,
            "card_render_width": 150,
            "card_font_px": 45,
        },
        "fonts": [
            {"file": str(LABEL_FONT), "sha256": sha(LABEL_FONT)},
            {"file": str(DATE_FONT), "sha256": sha(DATE_FONT)},
        ],
        "runtime": {"pillow": pillow_version, "numpy": np.__version__},
        "generator": {
            "file": "scripts/build_assets.py",
            "sha256": sha(Path(__file__)),
        },
        "assets": assets,
    }
    (ASSETS / "asset-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    master = load_master()
    for name, spec in HERO_SPECS.items():
        save_jpeg(build_hero(master, spec), ASSETS / name, spec["quality"])
    save_jpeg(build_works(master), ASSETS / "works.jpg", 88)
    save_jpeg(build_works(master, mobile=True), ASSETS / "works-mobile.jpg", 88)
    for name, spec in CARD_SPECS.items():
        save_jpeg(build_card(master, spec), ASSETS / name, 88)
    save_jpeg(build_footer(master), ASSETS / "ashes-trace.jpg", 88)
    save_jpeg(build_footer(master, mobile=True), ASSETS / "ashes-trace-mobile.jpg", 88)
    write_manifest()


if __name__ == "__main__":
    main()
