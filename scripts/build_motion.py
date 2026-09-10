#!/usr/bin/env python3
"""Render bounded local motion from the approved SVGs, preserving static sources."""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess

import numpy as np
from PIL import Image, __version__ as pillow_version

ROOT = Path(__file__).resolve().parents[1]
FPS = 10
SECONDS = 12
FRAME_COUNT = FPS * SECONDS
FRAME_MS = 1000 // FPS
HERO_INNER_GUARD = 4
HERO_INNER_FADE = 4
LEFT_HAIR_SHIFT_SOURCE_PX = 2.4
RIGHT_HAIR_SHIFT_SOURCE_PX = 2.1
FISH_REFLECTION_SHIFT_SOURCE_PX = 1.9
HERO_REGIONS = {
    'hero': [[540, 65, 990, 570], [500, 480, 670, 720],
             [860, 480, 1020, 720], [668, 0, 684, 865]],
    'hero-mobile': [[510, 10, 1000, 635], [425, 515, 650, 825],
                    [880, 515, 1024, 825], [668, 0, 684, 865]],
}
PORTRAIT_GUARDS = {
    'hero': [675, 145, 855, 485],
    'hero-mobile': [645, 90, 880, 535],
}
SPECS = (
    ('hero', 1024, HERO_REGIONS['hero'], 4_500_000),
    ('hero-mobile', 768, HERO_REGIONS['hero-mobile'], 4_500_000),
    ('work-fish', 320, [[10, 10, 310, 226]], 500_000),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_frame_function(name, image):
    """Return RGB frames; only the named visual fragments may move."""
    base = np.asarray(image.convert('RGB'), dtype=np.float32)
    height, width = base.shape[:2]
    yy, xx = np.mgrid[:height, :width].astype(np.float32)
    if name.startswith('hero'):
        x = xx * 1024 / width
        y = yy * 865 / height
        luma = base @ np.array([.2126, .7152, .0722], dtype=np.float32)

        def region_weight(bounds):
            x0, y0, x1, y1 = bounds
            distance = np.minimum.reduce([x - x0, x1 - x, y - y0, y1 - y])
            return np.clip((distance - HERO_INNER_GUARD) / HERO_INNER_FADE, 0, 1)

        orbit_area, left_area, right_area, seam_area = [
            region_weight(bounds) for bounds in HERO_REGIONS[name]
        ]
        gx0, gy0, gx1, gy1 = PORTRAIT_GUARDS[name]
        portrait_fixed = (x >= gx0) & (x < gx1) & (y >= gy0) & (y < gy1)
        movable = (~portrait_fixed).astype(np.float32)

        if name == 'hero-mobile':
            transform = lambda px, py: (px * 1.27 - 210, py * 1.27 - 90)
            cx, cy = transform(760, 328)
            rx, ry = 180 * 1.27, 235 * 1.27
            stars = [transform(px, py) for px, py in ((566, 184), (938, 206), (970, 421), (548, 474))]
        else:
            cx, cy, rx, ry = 760, 328, 180, 235
            stars = [(566, 184), (938, 206), (970, 421), (548, 474)]

        radius = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
        ring = np.exp(-.5 * ((radius - 1) / .014) ** 2)
        visible_line = np.clip((luma - 28) / 68, 0, 1)
        orbit = ring * visible_line * orbit_area * movable
        seam = np.clip(1 - np.abs(x - 676) / 4, 0, 1)
        seam *= np.clip((luma - 22) / 42, 0, 1) * seam_area * movable

        star_weights = []
        for sx, sy in stars:
            star_weights.append(
                np.exp(-.5 * (((x - sx) / 5) ** 2 + ((y - sy) / 5) ** 2))
                * orbit_area * movable
            )

        row = np.arange(height)[:, None]

        def shifted(dx):
            sample = np.clip(xx - dx, 0, width - 1)
            left = np.floor(sample).astype('int32')
            right = np.minimum(left + 1, width - 1)
            fraction = (sample - left)[..., None]
            return base[row, left] * (1 - fraction) + base[row, right] * fraction

        def frame(index):
            angle = 2 * math.pi * index / FRAME_COUNT
            source_scale = width / 1024
            left_shift = LEFT_HAIR_SHIFT_SOURCE_PX * source_scale * math.sin(angle)
            right_shift = -RIGHT_HAIR_SHIFT_SOURCE_PX * source_scale * math.sin(angle)
            moved_left = shifted(left_shift)
            moved_right = shifted(right_shift)
            left_presence = np.clip((np.maximum(luma, moved_left @ np.array([.2126, .7152, .0722])) - 34) / 58, 0, 1)
            right_presence = np.clip((np.maximum(luma, moved_right @ np.array([.2126, .7152, .0722])) - 34) / 58, 0, 1)
            left_weight = left_area * left_presence * movable
            right_weight = right_area * right_presence * movable
            result = base + (moved_left - base) * left_weight[..., None]
            result += (moved_right - base) * right_weight[..., None]

            delta = .055 * math.sin(angle) * orbit
            delta += .035 * (1 - math.cos(angle)) * seam
            phases = (0, .7, 1.4, 2.1)
            for weight, phase in zip(star_weights, phases):
                delta += .075 * (math.sin(angle + phase) - math.sin(phase)) * weight
            result *= 1 + delta[..., None]
            return Image.fromarray(np.clip(np.rint(result), 0, 255).astype('uint8'))
    else:
        # A horizontal ripple moves reflected light by at most two source pixels.
        x0, y0, x1, y1 = 10, 10, 310, 226
        patch = base[y0:y1, x0:x1]
        ph, pw = patch.shape[:2]
        py, px = np.mgrid[:ph, :pw].astype(np.float32)
        luma = patch @ np.array([.2126, .7152, .0722], dtype=np.float32)
        weight = np.clip((luma - 32) / 55, 0, 1)
        edge = np.minimum.reduce([px / 8, (pw - 1 - px) / 8, py / 8, (ph - 1 - py) / 8])
        weight *= np.clip(edge, 0, 1)
        row = np.arange(ph)[:, None]

        def frame(index):
            angle = 2 * math.pi * index / FRAME_COUNT
            shift = FISH_REFLECTION_SHIFT_SOURCE_PX * math.sin(angle) * (.65 + .35 * np.sin(py / 18 + angle))
            sample = np.clip(px + shift, 0, pw - 1)
            left = np.floor(sample).astype('int32')
            right = np.minimum(left + 1, pw - 1)
            fraction = (sample - left)[..., None]
            moved = patch[row, left] * (1 - fraction) + patch[row, right] * fraction
            result = base.copy()
            result[y0:y1, x0:x1] = patch + (moved - patch) * weight[..., None]
            return Image.fromarray(np.clip(np.rint(result), 0, 255).astype('uint8'))
    return frame


def encode(name, image, output):
    frame = make_frame_function(name, image)
    # One palette for the entire loop prevents static pixels from flickering.
    samples = []
    for index in range(0, FRAME_COUNT, 8):
        sample = frame(index)
        sample.thumbnail((256, 256), Image.Resampling.LANCZOS)
        samples.append(np.asarray(sample))
    palette = Image.fromarray(np.concatenate(samples, axis=0)).quantize(
        colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    frames = [frame(index).quantize(palette=palette, dither=Image.Dither.NONE)
              for index in range(FRAME_COUNT)]
    target = output / f'{name}-motion.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, disposal=1, optimize=True)
    return target


def build(output, node):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='profile-motion-') as tmp:
        raster = Path(tmp)
        subprocess.run([node, str(ROOT/'scripts/render_motion_sources.cjs'),
                        str(ROOT/'assets'), str(raster)], check=True)
        entries = []
        for name, width, regions, limit in SPECS:
            source = ROOT/'assets'/f'{name}.svg'
            with Image.open(raster/f'{name}.png') as im:
                image = im.convert('RGB')
            target = encode(name, image, output)
            assert target.stat().st_size <= limit, f'{target.name} exceeds byte budget'
            with Image.open(target) as gif:
                count = gif.n_frames
                duration = sum((gif.seek(i), gif.info['duration'])[1] for i in range(count))
            motion_limits = ({
                'hair_tip_translation_source_px': {
                    'left': LEFT_HAIR_SHIFT_SOURCE_PX,
                    'right': RIGHT_HAIR_SHIFT_SOURCE_PX,
                },
                'orbit_translation_source_px': 0,
                'star_translation_source_px': 0,
                'seam_translation_source_px': 0,
            } if name.startswith('hero') else {
                'reflection_translation_source_px': FISH_REFLECTION_SHIFT_SOURCE_PX,
            })
            entries.append({'file': target.name, 'source': source.relative_to(ROOT).as_posix(),
                            'source_sha256': sha(source), 'sha256': sha(target),
                            'bytes': target.stat().st_size, 'width': width, 'height': image.height,
                            'frames': count, 'duration_ms': duration, 'loop': 0,
                            'source_viewbox': [1024, 865] if name.startswith('hero') else [320, 326],
                            'motion_regions': regions, 'motion_limits': motion_limits,
                            'byte_budget': limit,
                            'stationary_inner_band_source_px': HERO_INNER_GUARD if name.startswith('hero') else 0,
                            'inward_fade_source_px': HERO_INNER_FADE if name.startswith('hero') else 0})
            print(f'{target.name}: {target.stat().st_size:,} bytes, {count} frames, {duration}ms', flush=True)
        fish_bytes = entries[-1]['bytes']
        assert all(item['bytes'] + fish_bytes <= 5_000_000 for item in entries[:2])
        manifest = {'schema': 1, 'duration_ms': SECONDS*1000, 'fps': FPS,
                    'policy': 'Fixed five-color source; no dithering; only broken orbit and stars, hair tips, vertical seam, and fish reflection move; portrait and type remain fixed',
                    'runtime': {**json.loads((raster/'renderer.json').read_text()),
                                'pillow': pillow_version, 'numpy': np.__version__}, 'assets': entries}
        (output/'motion-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'assets')
    parser.add_argument('--node', default=os.environ.get('PROFILE_NODE') or shutil.which('node'))
    args = parser.parse_args()
    if not args.node:
        parser.error('Node is required. Supply --node or PROFILE_NODE; Sharp must be available.')
    build(args.output_dir.resolve(), args.node)
