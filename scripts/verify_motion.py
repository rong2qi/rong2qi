#!/usr/bin/env python3
"""Verify GIF integrity, bounded motion, seam continuity and optional regeneration."""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = json.loads((ROOT/'assets/motion-manifest.json').read_text())
    assert manifest['duration_ms'] == 12_000 and manifest['fps'] == 10
    assert manifest['policy'] == (
        'Fixed five-color source; no dithering; only broken orbit and stars, '
        'hair tips, vertical seam, and fish reflection move; portrait and type remain fixed')
    expected = {
        'hero-motion.gif': {
            'size': (1024, 865),
            'regions': [[540, 65, 990, 570], [500, 480, 670, 720],
                        [860, 480, 1020, 720], [668, 0, 684, 865]],
            'portrait_guard': [675, 145, 855, 485],
            'motion_limits': {
                'hair_tip_translation_source_px': {'left': 2.4, 'right': 2.1},
                'orbit_translation_source_px': 0,
                'star_translation_source_px': 0,
                'seam_translation_source_px': 0,
            },
        },
        'hero-mobile-motion.gif': {
            'size': (768, 649),
            'regions': [[510, 10, 1000, 635], [425, 515, 650, 825],
                        [880, 515, 1024, 825], [668, 0, 684, 865]],
            'portrait_guard': [645, 90, 880, 535],
            'motion_limits': {
                'hair_tip_translation_source_px': {'left': 2.4, 'right': 2.1},
                'orbit_translation_source_px': 0,
                'star_translation_source_px': 0,
                'seam_translation_source_px': 0,
            },
        },
        'work-fish-motion.gif': {
            'size': (320, 326),
            'regions': [[10, 10, 310, 226]],
            'portrait_guard': None,
            'motion_limits': {'reflection_translation_source_px': 1.9},
        },
    }
    spec = importlib.util.spec_from_file_location('motion_builder', ROOT/'scripts/build_motion.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    assert builder.LEFT_HAIR_SHIFT_SOURCE_PX == 2.4
    assert builder.RIGHT_HAIR_SHIFT_SOURCE_PX == 2.1
    assert builder.FISH_REFLECTION_SHIFT_SOURCE_PX == 1.9
    assert {a['file'] for a in manifest['assets']} == set(expected)
    results = []
    for item in manifest['assets']:
        is_hero = item['file'].startswith('hero')
        contract = expected[item['file']]
        assert item['motion_regions'] == contract['regions'], 'Approved region drift'
        assert item['motion_limits'] == contract['motion_limits'], 'Approved motion limit drift'
        if is_hero:
            assert max(item['motion_limits']['hair_tip_translation_source_px'].values()) <= 3
        assert item['stationary_inner_band_source_px'] == (4 if is_hero else 0)
        assert item['inward_fade_source_px'] == (4 if is_hero else 0)
        path = ROOT/'assets'/item['file']
        source = (ROOT/item['source']).resolve()
        assert source.is_relative_to((ROOT/'assets').resolve()) and source.suffix == '.svg'
        assert sha(source) == item['source_sha256'], 'Static source drift'
        assert sha(path) == item['sha256'], 'GIF drift'
        assert path.stat().st_size == item['bytes'] <= item['byte_budget']
        with Image.open(path) as gif:
            assert gif.format == 'GIF' and gif.size == contract['size']
            assert gif.info.get('loop') == 0 and gif.n_frames == 120
            width, height = gif.size
            yy, xx = np.mgrid[:height, :width]
            vw, vh = item['source_viewbox']
            x, y = xx*vw/width, yy*vh/height
            masks = [(x>=x0)&(x<x1)&(y>=y0)&(y<y1)
                     for x0,y0,x1,y1 in item['motion_regions']]
            allowed = np.logical_or.reduce(masks)
            portrait_guard = np.zeros((height, width), dtype=bool)
            if contract['portrait_guard']:
                x0, y0, x1, y1 = contract['portrait_guard']
                portrait_guard = (x>=x0)&(x<x1)&(y>=y0)&(y<y1)
            guard = np.zeros((height, width), dtype=bool)
            if is_hero:
                interior = np.zeros((height, width), dtype=bool)
                for mask, (x0, y0, x1, y1) in zip(masks, item['motion_regions']):
                    distance = np.minimum.reduce([x-x0, x1-x, y-y0, y1-y])
                    interior |= mask & (distance > 4)
                # Guard the outer edge of the approved union. A rectangle edge
                # that falls inside another approved region is not an external
                # boundary and must not mask valid overlapping motion.
                guard = allowed & ~interior
            counts = np.zeros(len(masks), dtype='int64')
            first = np.asarray(gif.convert('RGB')).copy()
            previous = first
            durations, differences, observed = [], [], []
            for index in range(gif.n_frames):
                gif.seek(index)
                durations.append(gif.info['duration'])
                current = np.asarray(gif.convert('RGB')).copy()
                changed = np.any(current != first, axis=2)
                assert not np.any(changed & ~allowed), f'{path.name}: motion outside approved regions'
                assert not np.any(changed & guard), f'{path.name}: motion inside stationary edge band'
                assert not np.any(changed & portrait_guard), f'{path.name}: portrait must remain fixed'
                for n, mask in enumerate(masks):
                    counts[n] = max(counts[n], np.count_nonzero(changed & mask))
                if index:
                    differences.append(float(np.abs(current.astype('int16') - previous)[allowed].mean()))
                if index in (0, 30, 60, 90):
                    observed.append({'time_ms': index*100,
                                     'changed_pixels': int(np.count_nonzero(changed)),
                                     'mean_change_in_regions': float(np.abs(current.astype('int16')-first)[allowed].mean())})
                previous = current
            closing = float(np.abs(previous.astype('int16') - first)[allowed].mean())
            assert sum(durations) == 12_000 and set(durations) == {100}
            assert np.all(counts > (20 if is_hero else 100)), f'{path.name}: an approved region does not visibly change'
            assert observed[1]['changed_pixels'] > 100, f'{path.name}: no motion within three seconds'
            assert closing <= max(differences)*1.5 + .01, f'{path.name}: abrupt loop seam'
            results.append({'file': path.name, 'bytes': item['bytes'], 'frames': gif.n_frames,
                            'duration_ms': sum(durations), 'static_region_changes': 0,
                            'stationary_inner_band_changes': 0,
                            'protected_portrait_changes': 0 if is_hero else None,
                            'max_changed_pixels_per_region': [int(c) for c in counts],
                            'max_adjacent_frame_mean_delta': max(differences),
                            'loop_seam_mean_delta': closing, 'samples': observed})
    fish = next(r['bytes'] for r in results if r['file']=='work-fish-motion.gif')
    totals = {r['file']: r['bytes']+fish for r in results if r['file'].startswith('hero')}
    assert max(totals.values()) <= 5_000_000
    return {'status': 'PASS', 'decoded_motion': results, 'animated_bytes_by_hero': totals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true')
    parser.add_argument('--node', default=os.environ.get('PROFILE_NODE'))
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT/'scripts/verify_assets.py')], check=True,
                   stdout=subprocess.PIPE, text=True)
    report = verify()
    if args.rebuild:
        with TemporaryDirectory(prefix='profile-motion-verify-') as tmp:
            command = [sys.executable, str(ROOT/'scripts/build_motion.py'), '--output-dir', tmp]
            if args.node:
                command.extend(['--node', args.node])
            subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True)
            for path in Path(tmp).iterdir():
                assert path.read_bytes() == (ROOT/'assets'/path.name).read_bytes(), path.name
        report['regeneration'] = 'byte-identical'
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
