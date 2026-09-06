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
SPECS = (
    ('hero', 1024, [[330, 0, 850, 505], [448, 589, 870, 824]], 4_500_000),
    ('hero-mobile', 768, [[330, 0, 850, 505], [448, 589, 870, 824]], 4_500_000),
    ('work-fish', 320, [[10, 10, 310, 226]], 500_000),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_frame_function(name, image):
    """Return RGB frames; masks deliberately exclude all labels and borders."""
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
            # Keep a fixed inner border so scaled light cannot sample across it.
            return np.clip((distance - HERO_INNER_GUARD) / HERO_INNER_FADE, 0, 1)

        mineral = region_weight((330, 0, 850, 505))
        # Only existing pigment receives the moving light; the dark field stays fixed.
        pigment = np.clip((luma - 30) / 60, 0, 1) * mineral
        light_area = region_weight((448, 589, 870, 824))
        first = np.exp(-.5 * (((x - 629) / 48) ** 2 + ((y - 765) / 30) ** 2)) * light_area
        second = np.exp(-.5 * (((x - 850) / 35) ** 2 + ((y - 657) / 27) ** 2)) * light_area

        def frame(index):
            angle = 2 * math.pi * index / FRAME_COUNT
            cy = 325 + 115 * math.cos(angle)
            cx = float(np.interp(cy, [140, 220, 330, 400, 460], [685, 660, 655, 630, 565]))
            travel = np.exp(-.5 * (((x - cx) / 72) ** 2 + ((y - cy) / 78) ** 2))
            delta = .10 * math.sin(angle) * travel * pigment
            delta += .10 * math.sin(angle) * first - .10 * math.sin(2 * angle) * second
            return Image.fromarray(np.clip(np.rint(base * (1 + delta[..., None])), 0, 255).astype('uint8'))
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
            shift = 1.9 * math.sin(angle) * (.65 + .35 * np.sin(py / 18 + angle))
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
            entries.append({'file': target.name, 'source': source.relative_to(ROOT).as_posix(),
                            'source_sha256': sha(source), 'sha256': sha(target),
                            'bytes': target.stat().st_size, 'width': width, 'height': image.height,
                            'frames': count, 'duration_ms': duration, 'loop': 0,
                            'source_viewbox': [1024, 865] if name.startswith('hero') else [320, 326],
                            'motion_regions': regions, 'byte_budget': limit,
                            'stationary_inner_band_source_px': HERO_INNER_GUARD if name.startswith('hero') else 0,
                            'inward_fade_source_px': HERO_INNER_FADE if name.startswith('hero') else 0})
            print(f'{target.name}: {target.stat().st_size:,} bytes, {count} frames, {duration}ms', flush=True)
        fish_bytes = entries[-1]['bytes']
        assert all(item['bytes'] + fish_bytes <= 5_000_000 for item in entries[:2])
        manifest = {'schema': 1, 'duration_ms': SECONDS*1000, 'fps': FPS,
                    'policy': 'Fixed palette; no dithering; local pigment/reflection motion; hero has 4px stationary inner band and 4px inward fade; static SVGs unchanged',
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
