#!/usr/bin/env python3
"""Verify rendering inputs, safe SVG structure, links, and deterministic generation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from html.parser import HTMLParser
from urllib.parse import urlsplit
import hashlib
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
PALETTE = {'#11131A', '#D3CBC2', '#6F8983', '#8D5660', '#E7CBB4'}


def local_name(element):
    return element.tag.rsplit('}', 1)[-1]


def element_by_id(root, target):
    return next((element for element in root.iter() if element.attrib.get('id') == target), None)

class ReadmeParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.images=[]; self.links=[]; self.sources=[]; self.pictures=[]; self.picture=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='picture': self.picture={'sources':[], 'image':None}
        if tag=='img':
            self.images.append(a)
            if self.picture is not None: self.picture['image']=a
        if tag=='source':
            self.sources.append(a)
            if self.picture is not None: self.picture['sources'].append(a)
        if tag=='a': self.links.append(a['href'])
    def handle_endtag(self,tag):
        if tag=='picture':
            self.pictures.append(self.picture); self.picture=None

def main():
    readme=(ROOT/'README.md').read_text()
    parser=ReadmeParser();parser.feed(readme)
    assert len(parser.images)==8, 'Expected hero, works heading, five projects and footer.'
    assert len(parser.sources)==6, 'Responsive and reduced-motion sources must remain available.'
    for item in parser.images+parser.sources:
        url=item.get('src',item.get('srcset'))
        assert not urlsplit(url).scheme and not url.startswith('/'), url
        path=(ROOT/url).resolve()
        assert path.is_relative_to(ASSETS.resolve()) and path.is_file(), url
        if 'src' in item: assert item.get('alt'), f'Missing alt: {url}'
    expected_pictures=[
        ('assets/hero-motion.gif', [
            ('(prefers-reduced-motion: reduce) and (max-width: 1024px)', 'assets/hero-mobile.svg'),
            ('(prefers-reduced-motion: reduce)', 'assets/hero.svg'),
            ('(max-width: 1024px)', 'assets/hero-mobile-motion.gif')]),
        ('assets/works-divider.svg', [('(max-width: 1024px)', 'assets/works-divider-mobile.svg')]),
        ('assets/work-fish-motion.gif', [('(prefers-reduced-motion: reduce)', 'assets/work-fish.svg')]),
        ('assets/ashes-trace.svg', [('(max-width: 1024px)', 'assets/ashes-trace-mobile.svg')]),
    ]
    actual_pictures=[(p['image']['src'], [(s['media'],s['srcset']) for s in p['sources']]) for p in parser.pictures]
    assert actual_pictures==expected_pictures, 'Reduced-motion fallbacks must precede width alternatives.'
    expected={'https://github.com/rong2qi/'+name for name in (
        'desktop-pet-jinbao','prompt-agent-orchestrator','SpeakLoop','chief-of-staff-codex')}
    assert set(parser.links)==expected, parser.links
    assert 'href="https://github.com/rong2qi/fish-meditate"' not in readme
    assert '[GitHub ↗](https://github.com/rong2qi)' in readme
    assert '[repositories ↗](https://github.com/rong2qi?tab=repositories)' in readme
    card_group=readme.split('<p>')[1].split('</p>')[0]
    assert card_group.count('<img ')==5, 'All five cards must share one paragraph to flow together.'
    assert '<picture><source media="(prefers-reduced-motion: reduce)" srcset="assets/work-fish.svg"><img' in card_group, 'Keep the placeholder unlinked and preserve its static fallback.'
    assert len(parser.links) + 2 == 6, 'Four project links plus two footer links must remain accessible.'
    assert '偏女性半身剪影' in parser.images[0]['alt']
    forbidden={'script','foreignObject','image','a','animate','animateTransform','set'}
    svgs=sorted(ASSETS.rglob('*.svg'))
    assert len(svgs) == 11, 'The new profile must not ship legacy material-trace SVGs.'
    for path in svgs:
        data=path.read_text(); root=ET.fromstring(data)
        assert root.attrib.get('viewBox'), path
        assert path.stat().st_size < 2_000_000, path
        colors={color.upper() for color in re.findall(r'#[0-9a-fA-F]{6}', data)}
        assert colors <= PALETTE, (path, colors-PALETTE)
        assert 'Georgia' not in data and 'Times New Roman' not in data, path
        for el in root.iter():
            tag=local_name(el)
            assert tag not in forbidden, (path,tag)
            for key,value in el.attrib.items():
                assert not key.lower().startswith('on'), (path,key)
                if key.rsplit('}',1)[-1] in ('href','src'):
                    assert value.startswith('#'), (path,value)
                for ref in re.findall(r'url\(([^)]+)\)',value):
                    assert ref.startswith('#'), (path,ref)
        assert not re.search(r'<\?(?!xml)|<!ENTITY|<!DOCTYPE',data,re.I), path
    manifest_path=ASSETS/'asset-manifest.json'
    assert manifest_path.is_file(), 'Missing deterministic static asset manifest.'
    manifest=json.loads(manifest_path.read_text())
    assert manifest['schema'] == 1
    assert manifest['candidate_label'] == 'PROFILE-REFRACTED-20260910-02'
    assert manifest['style'] == '折光圣像 / refracted icon'
    assert set(manifest['palette'].values()) == PALETTE
    assert manifest['method'] == (
        'Original deterministic SVG geometry; no reference-image pixels, '
        'external fonts, or remote resources')
    assert manifest['generator'] == {
        'file': 'scripts/build_assets.py',
        'sha256': hashlib.sha256((ROOT/'scripts/build_assets.py').read_bytes()).hexdigest(),
    }
    assert {item['file'] for item in manifest['assets']} == {path.name for path in svgs}
    for item in manifest['assets']:
        path=ASSETS/item['file']
        root=ET.parse(path).getroot()
        assert item['width'] == int(root.attrib['width'])
        assert item['height'] == int(root.attrib['height'])
        assert item['bytes'] == path.stat().st_size
        assert item['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    hero=ET.parse(ASSETS/'hero.svg').getroot()
    mobile=ET.parse(ASSETS/'hero-mobile.svg').getroot()
    assert hero.attrib['viewBox'] == '0 0 1024 865'
    assert mobile.attrib['viewBox'] == '0 0 1024 865'
    assert 'female half silhouette' in (element_by_id(hero, 'title').text or '')
    for target in ('portrait-silhouette', 'hair-static', 'hair-drift-left',
                   'hair-drift-right', 'face-shadow', 'orbit', 'seam', 'stars', 'hand-date'):
        assert element_by_id(hero, target) is not None, f'Missing visual unit: {target}'
    face=element_by_id(hero, 'face-shadow')
    face_paths=[element for element in face.iter() if local_name(element) == 'path']
    assert len(face_paths) == 2
    assert face_paths[0].attrib.get('fill') == '#11131A', 'The face must remain hidden in shadow.'
    assert face_paths[1].attrib.get('stroke') == '#8D5660', 'Keep only the muted-rose reflection.'
    mobile_identity=element_by_id(mobile, 'identity')
    mobile_now=element_by_id(mobile, 'now-label')
    mobile_date=element_by_id(mobile, 'hand-date')
    # Live GitHub branch rendering exposes a 324px README canvas at a 390px
    # viewport; validate the displayed size against that observed surface.
    mobile_scale=324/1024
    for group in (mobile_identity, mobile_now, mobile_date):
        text=next(element for element in group.iter() if local_name(element) == 'text')
        assert float(text.attrib['font-size'])*mobile_scale >= 14, (
            'Mobile labels render below 14px at a 390px GitHub viewport.')
    for filename, target in (
        ('works-divider-mobile.svg', 'works-label'),
        ('ashes-trace-mobile.svg', 'ashes-label'),
        ('ashes-trace-mobile.svg', 'trace-label'),
    ):
        root=ET.parse(ASSETS/filename).getroot()
        group=element_by_id(root, target)
        text=next(element for element in group.iter() if local_name(element) == 'text')
        assert float(text.attrib['font-size'])*mobile_scale >= 14, (
            f'{filename}:{target} renders below 14px at 390px.')
    expected_card_titles={
        'work-fish.svg': 'fish-meditate',
        'work-jinbao.svg': 'desktop-pet-jinbao',
        'work-orchestrator.svg': 'prompt-agent-orchestrator',
        'work-speakloop.svg': 'SpeakLoop',
        'work-chief.svg': 'chief-of-staff-codex',
    }
    for filename, title in expected_card_titles.items():
        path=ASSETS/filename
        root=ET.parse(path).getroot()
        assert element_by_id(root, 'title').text == title
        visible_text=[element for element in root.iter() if local_name(element) == 'text']
        assert visible_text and all(float(element.attrib['font-size'])*.5 >= 14
                                    for element in visible_text), (
            f'{filename} labels render below 14px at their 160px README width.')
    spec=importlib.util.spec_from_file_location('profile_builder',ROOT/'scripts/build_assets.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    for lines in (builder.HERO_LINES,builder.NOW_LINES,builder.ASHES_LINES):
        assert isinstance(lines,tuple) and all(isinstance(line,str) for line in lines)
    assert '&lt;script&gt;' in builder.words(('<script>',),0,0,16,24)
    with TemporaryDirectory() as folder:
        builder.ASSETS=Path(folder);builder.main()
        outputs=sorted(Path(folder).glob('*.svg'))
        assert len(outputs)==11
        for output in outputs:
            assert output.read_bytes()==(ASSETS/output.name).read_bytes(), f'Regenerate {output.name}'
        assert (Path(folder)/'asset-manifest.json').read_bytes() == manifest_path.read_bytes()
    animated={item.get('src', item.get('srcset')) for item in parser.images+parser.sources
              if item.get('src', item.get('srcset')).endswith('.gif')}
    assert animated == {'assets/hero-motion.gif', 'assets/hero-mobile-motion.gif',
                        'assets/work-fish-motion.gif'}
    print(json.dumps({'status':'PASS','svg_files':len(svgs),'readme_images':len(parser.images),'picture_sources':len(parser.sources),'animated_images':len(animated),'project_links':len(parser.links),'generation':'byte-identical','embedded_raster_in_svg':False,'svg_bytes':sum(p.stat().st_size for p in svgs)}))

if __name__=='__main__': main()
