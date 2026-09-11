#!/usr/bin/env python3
"""Verify fixed-composition light reveal, timing, loop, byte budget and regeneration."""

from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
MASTER_SHA256 = "2f61ae115f1c3f6924bb7db23868d8324f73754bb632d60cb91760e609b965c1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def luminance(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def gradient(gray):
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:] = np.abs(gray[:, 1:] - gray[:, :-1])
    gy[1:, :] = np.abs(gray[1:, :] - gray[:-1, :])
    return np.hypot(gx, gy)


def correlation(left, right):
    a = left.astype(np.float64).ravel()
    b = right.astype(np.float64).ravel()
    a -= a.mean()
    b -= b.mean()
    denominator = np.sqrt(np.dot(a, a) * np.dot(b, b))
    return float(np.dot(a, b) / denominator) if denominator else 0.0


def shifted_correlation(reference, candidate, dx, dy):
    height, width = reference.shape
    x0 = max(0, dx)
    x1 = min(width, width + dx)
    y0 = max(0, dy)
    y1 = min(height, height + dy)
    return correlation(
        reference[y0:y1, x0:x1],
        candidate[y0 - dy:y1 - dy, x0 - dx:x1 - dx],
    )


def verify():
    manifest_path = ASSETS / "motion-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == 2
    assert manifest["candidate_label"] == "PROFILE-NUWA-A-20260911-01"
    assert manifest["duration_ms"] == 12_000
    assert manifest["fps"] == 10 and manifest["frames"] == 120
    assert manifest["palette_colors"] == 128
    assert manifest["reveal_levels"] == 12
    assert manifest["timeline"] == {
        "quiet_hold_ms": 1200,
        "reveal_complete_ms": 6000,
        "full_hold_until_ms": 8400,
        "return_complete_ms": 12000,
    }
    assert manifest["policy"] == (
        "One fixed Candidate A composition; per-pixel light reveal travels from the five-colored "
        "stone through the repaired sky and river; no crossfade, character morph or spatial warp. "
        "Reduced-motion sources show the full selected A painting."
    )
    assert manifest["generator"] == {
        "file": "scripts/build_motion.py",
        "sha256": sha(ROOT / "scripts/build_motion.py"),
    }
    assert manifest["static_manifest_sha256"] == sha(ASSETS / "asset-manifest.json")

    expected = {
        "hero-motion.gif": {
            "source": "assets/source/nuwa-a-sky-rift.png",
            "static_fallback": "assets/hero.jpg",
            "size": (720, 480),
            "cadence": [1, 478],
            "mobile": False,
        },
        "hero-mobile-motion.gif": {
            "source": "assets/source/nuwa-a-sky-rift.png",
            "static_fallback": "assets/hero-mobile.jpg",
            "size": (560, 560),
            "cadence": [1, 558],
            "mobile": True,
        },
    }
    assert {item["file"] for item in manifest["assets"]} == set(expected)

    static_manifest = json.loads((ASSETS / "asset-manifest.json").read_text(encoding="utf-8"))
    shared_static_bytes = sum(
        item["bytes"]
        for item in static_manifest["assets"]
        if item["file"] not in {"hero.jpg", "hero-mobile.jpg"}
    )
    reports = []
    builder_spec = importlib.util.spec_from_file_location(
        "nuwa_static_builder", ROOT / "scripts/build_assets.py"
    )
    static_builder = importlib.util.module_from_spec(builder_spec)
    builder_spec.loader.exec_module(static_builder)
    for item in manifest["assets"]:
        contract = expected[item["file"]]
        path = ASSETS / item["file"]
        source = ROOT / item["source"]
        static_fallback = ROOT / item["static_fallback"]
        assert item["source"] == contract["source"]
        assert source.is_file() and source.suffix == ".png"
        assert item["source_sha256"] == sha(source)
        assert item["source_sha256"] == MASTER_SHA256
        assert item["static_fallback"] == contract["static_fallback"]
        assert item["static_fallback_sha256"] == sha(static_fallback)
        assert item["sha256"] == sha(path)
        assert item["bytes"] == path.stat().st_size <= item["byte_budget"]
        assert item["frame_cadence_pixel"] == contract["cadence"]
        assert item["frame_cadence_source_pixels"] == 1
        assert item["motion_region"] == [0, 0, *contract["size"]]
        assert item["spatial_motion_pixels"] == 0
        assert item["character_geometry"] == "fixed Candidate A pixels; light and color only"
        assert item["labels_fixed"] is True
        assert item["loaded_bytes_with_static_sections"] == item["bytes"] + shared_static_bytes
        assert item["loaded_bytes_with_static_sections"] <= 6_500_000

        with Image.open(static_fallback) as static_image:
            static_rgb = np.asarray(
                static_image.convert("RGB").resize(contract["size"], Image.Resampling.LANCZOS),
                dtype=np.float32,
            )
        label_overlay = np.asarray(
            static_builder.hero_label_overlay(contract["size"], contract["mobile"])
        )
        label_mask = label_overlay[..., 3] > 0
        with Image.open(path) as gif:
            assert gif.format == "GIF" and gif.size == contract["size"]
            assert gif.info.get("loop") == 0 and gif.n_frames == 120
            durations = []
            means = []
            selected = {}
            adjacent_changed = []
            previous = None
            first = None
            for index in range(gif.n_frames):
                gif.seek(index)
                durations.append(gif.info["duration"])
                current = np.asarray(gif.convert("RGB"), dtype=np.float32)
                means.append(float(luminance(current).mean()))
                if index in {0, 12, 24, 36, 48, 60, 72, 84, 96, 108, 119}:
                    selected[index] = current.copy()
                if first is None:
                    first = current.copy()
                else:
                    assert np.array_equal(current[label_mask], first[label_mask]), (
                        "Identity, now and date labels must remain pixel-still."
                    )
                if previous is not None:
                    adjacent_changed.append(int(np.count_nonzero(np.any(current != previous, axis=2))))
                previous = current
            last = previous

        assert set(durations) == {100} and sum(durations) == 12_000
        assert min(adjacent_changed) >= 1, "Quantized hold frames were coalesced or duplicated."
        assert float(np.abs(first - last).mean()) <= 0.02, "Abrupt loop seam"
        assert selected[60].mean() > selected[0].mean() + 18, "B-to-A reveal is not visible"
        assert float(np.abs(selected[60] - static_rgb).mean()) < 8.0, (
            "Bright state no longer matches selected A."
        )

        rising = [means[index] for index in (12, 24, 36, 48, 60)]
        falling = [means[index] for index in (84, 96, 108, 119)]
        # The traveling warm front may overshoot the settled A exposure by up
        # to one luma value; larger reversals still fail the reveal contract.
        assert all(later >= earlier - 1.0 for earlier, later in zip(rising, rising[1:])), rising
        assert all(later <= earlier + 0.5 for earlier, later in zip(falling, falling[1:])), falling
        assert max(abs(means[index] - means[60]) for index in (60, 72, 84)) < 1.2

        static_edges = gradient(luminance(static_rgb))
        peak_edges = gradient(luminance(selected[60]))
        quiet_edges = gradient(luminance(selected[0]))
        peak_zero = correlation(static_edges, peak_edges)
        peak_shifted = max(
            shifted_correlation(static_edges, peak_edges, dx, dy)
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2))
        )
        quiet_zero = correlation(static_edges, quiet_edges)
        quiet_shifted = max(
            shifted_correlation(static_edges, quiet_edges, dx, dy)
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2))
        )
        assert peak_zero > 0.84 and peak_zero >= peak_shifted + 0.30, (
            "Bright-state structure shifted away from Candidate A."
        )
        assert quiet_zero > 0.60 and quiet_zero >= quiet_shifted + 0.20, (
            "Quiet-state structure suggests a morph or spatial warp."
        )

        reports.append(
            {
                "file": item["file"],
                "bytes": item["bytes"],
                "frames": 120,
                "duration_ms": 12_000,
                "loop_seam_mean_delta": float(np.abs(first - last).mean()),
                "quiet_to_full_luma_delta": means[60] - means[0],
                "full_to_static_mean_delta": float(np.abs(selected[60] - static_rgb).mean()),
                "peak_edge_alignment": peak_zero,
                "quiet_edge_alignment": quiet_zero,
                "fixed_label_pixel_changes": 0,
                "spatial_shift_pixels": 0,
                "min_adjacent_changed_pixels": min(adjacent_changed),
                "loaded_bytes_with_static_sections": item["bytes"] + shared_static_bytes,
            }
        )
    return {"status": "PASS", "decoded_motion": reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_assets.py")],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    report = verify()
    if args.rebuild:
        with TemporaryDirectory(prefix="nuwa-motion-verify-") as folder:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build_motion.py"),
                    "--output-dir",
                    folder,
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            for name in ("hero-motion.gif", "hero-mobile-motion.gif", "motion-manifest.json"):
                assert (Path(folder) / name).read_bytes() == (ASSETS / name).read_bytes(), (
                    f"Regenerate {name}"
                )
        report["regeneration"] = "byte-identical"
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
