#!/usr/bin/env python3
"""Build a deterministic B-to-A light reveal from the fixed selected A painting."""

from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math

import numpy as np
from PIL import Image, ImageFilter, __version__ as pillow_version


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FPS = 10
SECONDS = 12
FRAME_COUNT = FPS * SECONDS
FRAME_MS = 1000 // FPS
PALETTE_COLORS = 128
REVEAL_LEVELS = 12

SPECS = {
    "hero": {
        "static_fallback": "hero.jpg",
        "mobile": False,
        "size": (720, 480),
        "byte_budget": 5_200_000,
        "stone": (0.73, 0.43),
        "seam_end": (0.33, 0.02),
        "river": ((0.60, 0.51), (0.48, 0.68), (0.34, 0.84)),
    },
    "hero-mobile": {
        "static_fallback": "hero-mobile.jpg",
        "mobile": True,
        "size": (560, 560),
        "byte_budget": 5_200_000,
        "stone": (0.74, 0.43),
        "seam_end": (0.12, 0.02),
        "river": ((0.56, 0.51), (0.40, 0.68), (0.22, 0.84)),
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def smoothstep(value):
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def segment_distance(x, y, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    projection = np.clip(
        ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy),
        0,
        1,
    )
    return np.sqrt((x - (x0 + projection * dx)) ** 2 + (y - (y0 + projection * dy)) ** 2)


def progress_at(index):
    if index == FRAME_COUNT - 1:
        return 0.0
    time = index / FPS
    if time < 1.2:
        return 0.0
    if time < 6.0:
        phase = (time - 1.2) / 4.8
        return 0.5 - 0.5 * math.cos(math.pi * phase)
    if time < 8.4:
        return 1.0
    phase = (time - 8.4) / 3.6
    return 0.5 + 0.5 * math.cos(math.pi * phase)


def frame_factory(image, spec, label_overlay):
    full = np.asarray(image.convert("RGB"), dtype=np.float32)
    height, width = full.shape[:2]
    y, x = np.mgrid[:height, :width].astype(np.float32)
    xn, yn = x / width, y / height
    luminance = full @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    grey = luminance[..., None]
    chromatic = full * 0.56 + grey * 0.44

    stone_x, stone_y = spec["stone"]
    right_presence = smoothstep((xn - 0.34) / 0.52)
    stone_presence = np.exp(
        -(((xn - stone_x) / 0.13) ** 2 + ((yn - stone_y) / 0.18) ** 2)
    )
    dark_factor = 0.23 + 0.12 * right_presence + 0.13 * stone_presence
    quiet = chromatic * dark_factor[..., None]
    quiet += np.array([6.0, 6.5, 5.0], dtype=np.float32)

    radial = np.sqrt(
        ((xn - stone_x) / 0.90) ** 2 + ((yn - stone_y) / 0.93) ** 2
    )
    seam_x, seam_y = spec["seam_end"]
    seam = segment_distance(xn, yn, stone_x, stone_y, seam_x, seam_y) / 0.48
    river_a, river_b, river_c = spec["river"]
    river_one = segment_distance(xn, yn, *river_a, *river_b) / 0.34
    river_two = segment_distance(xn, yn, *river_b, *river_c) / 0.38
    pathway = np.minimum.reduce([radial, seam, river_one, river_two])

    texture = image.convert("L").filter(ImageFilter.GaussianBlur(radius=max(9, width // 64)))
    texture = np.asarray(texture, dtype=np.float32) / 255.0
    delay = np.clip(0.05 + 0.76 * pathway + 0.12 * (1.0 - texture), 0.0, 0.92)

    red_thread = (
        (full[..., 0] > full[..., 1] * 1.17)
        & (full[..., 0] > full[..., 2] * 1.22)
        & (full[..., 0] > 58)
    ).astype(np.float32)
    red_thread = np.asarray(
        Image.fromarray((red_thread * 255).astype("uint8")).filter(
            ImageFilter.GaussianBlur(radius=1.1)
        ),
        dtype=np.float32,
    ) / 255.0
    stone_glow = np.exp(
        -(((xn - stone_x) / 0.075) ** 2 + ((yn - stone_y) / 0.105) ** 2)
    )
    overlay = np.asarray(label_overlay, dtype=np.float32)
    overlay_rgb = overlay[..., :3]
    overlay_alpha = overlay[..., 3:4] / 255.0
    label_mask = overlay[..., 3] > 0
    label_reference = full * (1.0 - overlay_alpha) + overlay_rgb * overlay_alpha

    def make_frame(index):
        progress = progress_at(index)
        reveal = smoothstep((progress - delay) / 0.18)
        reveal = np.rint(reveal * REVEAL_LEVELS) / REVEAL_LEVELS
        if progress >= 0.999:
            reveal[:] = 1.0
        result = quiet + (full - quiet) * reveal[..., None]

        if 0.005 < progress < 0.995:
            front = np.exp(-((progress - delay) / 0.052) ** 2)
            result += front[..., None] * np.array([22.0, 12.0, 3.0], dtype=np.float32)

        pulse_phase = 2.0 * math.pi * index / (FRAME_COUNT - 1)
        pulse = math.sin(pulse_phase)
        result += red_thread[..., None] * np.array([17.0, 3.0, 0.0]) * (0.5 + 0.5 * pulse) * 0.7
        result += stone_glow[..., None] * np.array([11.0, 6.0, 2.0]) * (0.5 + 0.5 * pulse)
        if index in (0, FRAME_COUNT - 1):
            result = quiet
        result[label_mask] = label_reference[label_mask]
        return Image.fromarray(np.clip(np.rint(result), 0, 255).astype("uint8"))

    return make_frame


def encode(image, spec, target, label_overlay):
    make_frame = frame_factory(image, spec, label_overlay)
    samples = []
    for index in range(0, FRAME_COUNT, 8):
        sample = make_frame(index)
        sample.thumbnail((256, 256), Image.Resampling.LANCZOS)
        samples.append(np.asarray(sample))
    palette = Image.fromarray(np.concatenate(samples, axis=0)).quantize(
        colors=PALETTE_COLORS,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    frames = [
        make_frame(index).quantize(palette=palette, dither=Image.Dither.NONE)
        for index in range(FRAME_COUNT)
    ]
    # Pillow coalesces a few visually identical hold frames after quantization.
    # Cycle one sub-display-pixel of existing dark paper grain so the exported
    # file retains the explicit 120-frame, 10fps timing contract.
    marker = (1, frames[0].height - 2)
    base_index = frames[0].getpixel(marker)
    colors = np.asarray(frames[0].getpalette()[: PALETTE_COLORS * 3], dtype=np.float32).reshape(-1, 3)
    distances = np.sum((colors - colors[base_index]) ** 2, axis=1)
    cadence = [int(index) for index in np.argsort(distances)[:3]]
    for index, frame in enumerate(frames):
        frame.putpixel(marker, cadence[0] if index == FRAME_COUNT - 1 else cadence[index % 3])
    frames[0].save(
        target,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        loop=0,
        disposal=1,
        optimize=True,
    )


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    builder_spec = importlib.util.spec_from_file_location(
        "nuwa_static_builder", ROOT / "scripts/build_assets.py"
    )
    static_builder = importlib.util.module_from_spec(builder_spec)
    builder_spec.loader.exec_module(static_builder)
    master = static_builder.load_master()
    entries = []
    for name, spec in SPECS.items():
        source = ASSETS / "source/nuwa-a-sky-rift.png"
        static_fallback = ASSETS / spec["static_fallback"]
        assert static_fallback.is_file(), f"Missing static fallback: {static_fallback}"
        static_spec = static_builder.HERO_SPECS[spec["static_fallback"]]
        frame_source = static_builder.build_hero(master, static_spec, labels=False).resize(
            spec["size"], Image.Resampling.LANCZOS
        )
        label_overlay = static_builder.hero_label_overlay(spec["size"], spec["mobile"])
        target = output / f"{name}-motion.gif"
        encode(frame_source, spec, target, label_overlay)
        assert target.stat().st_size <= spec["byte_budget"], (
            f"{target.name} exceeds {spec['byte_budget']:,}-byte budget"
        )
        with Image.open(target) as gif:
            frame_count = gif.n_frames
            durations = []
            for index in range(frame_count):
                gif.seek(index)
                durations.append(gif.info["duration"])
            width, height = gif.size
        entries.append(
            {
                "file": target.name,
                "source": source.relative_to(ROOT).as_posix(),
                "source_sha256": sha(source),
                "static_fallback": static_fallback.relative_to(ROOT).as_posix(),
                "static_fallback_sha256": sha(static_fallback),
                "sha256": sha(target),
                "bytes": target.stat().st_size,
                "width": width,
                "height": height,
                "frames": frame_count,
                "duration_ms": sum(durations),
                "frame_duration_ms": FRAME_MS,
                "loop": 0,
                "byte_budget": spec["byte_budget"],
                "frame_cadence_pixel": [1, height - 2],
                "frame_cadence_source_pixels": 1,
                "motion_region": [0, 0, width, height],
                "spatial_motion_pixels": 0,
                "character_geometry": "fixed Candidate A pixels; light and color only",
                "labels_fixed": True,
                "light_path": {
                    "stone": list(spec["stone"]),
                    "sky_seam_end": list(spec["seam_end"]),
                    "river": [list(point) for point in spec["river"]],
                },
            }
        )
        print(
            f"{target.name}: {target.stat().st_size:,} bytes, "
            f"{frame_count} frames, {sum(durations)}ms",
            flush=True,
        )

    static_manifest = json.loads((ASSETS / "asset-manifest.json").read_text())
    static_bytes = sum(item["bytes"] for item in static_manifest["assets"] if item["file"] not in {
        "hero.jpg", "hero-mobile.jpg"
    })
    for entry in entries:
        assert entry["bytes"] + static_bytes <= 6_500_000, "README loaded-byte budget exceeded"
        entry["loaded_bytes_with_static_sections"] = entry["bytes"] + static_bytes

    manifest = {
        "schema": 2,
        "candidate_label": "PROFILE-NUWA-A-20260911-01",
        "duration_ms": SECONDS * 1000,
        "fps": FPS,
        "frames": FRAME_COUNT,
        "palette_colors": PALETTE_COLORS,
        "reveal_levels": REVEAL_LEVELS,
        "policy": (
            "One fixed Candidate A composition; per-pixel light reveal travels from the five-colored "
            "stone through the repaired sky and river; no crossfade, character morph or spatial warp. "
            "Reduced-motion sources show the full selected A painting."
        ),
        "timeline": {
            "quiet_hold_ms": 1200,
            "reveal_complete_ms": 6000,
            "full_hold_until_ms": 8400,
            "return_complete_ms": 12000,
        },
        "runtime": {"pillow": pillow_version, "numpy": np.__version__},
        "static_manifest_sha256": sha(ASSETS / "asset-manifest.json"),
        "generator": {
            "file": "scripts/build_motion.py",
            "sha256": sha(Path(__file__)),
        },
        "assets": entries,
    }
    (output / "motion-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ASSETS)
    args = parser.parse_args()
    build(args.output_dir.resolve())
