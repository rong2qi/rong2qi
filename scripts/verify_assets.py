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

class ReadmeParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.images=[]; self.links=[]; self.sources=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='img': self.images.append(a)
        if tag=='source': self.sources.append(a)
        if tag=='a': self.links.append(a['href'])

def main():
    readme=(ROOT/'README.md').read_text()
    parser=ReadmeParser();parser.feed(readme)
    assert len(parser.images)==8, 'Expected hero, works heading, five projects and footer.'
    assert len(parser.sources)==3, 'All wide compositions need mobile sources.'
    for item in parser.images+parser.sources:
        url=item.get('src',item.get('srcset'))
        assert not urlsplit(url).scheme and not url.startswith('/'), url
        path=(ROOT/url).resolve()
        assert path.is_relative_to(ASSETS.resolve()) and path.is_file(), url
        if 'src' in item: assert item.get('alt'), f'Missing alt: {url}'
        else: assert item['media']=='(max-width: 1024px)', item
    expected={'https://github.com/rong2qi/'+name for name in (
        'desktop-pet-jinbao','prompt-agent-orchestrator','SpeakLoop','chief-of-staff-codex')}
    assert set(parser.links)==expected, parser.links
    assert 'href="https://github.com/rong2qi/fish-meditate"' not in readme
    assert '[GitHub ↗](https://github.com/rong2qi)' in readme
    assert '[repositories ↗](https://github.com/rong2qi?tab=repositories)' in readme
    card_group=readme.split('<p>')[1].split('</p>')[0]
    assert card_group.count('<img ')==5, 'All five cards must share one paragraph to flow together.'
    assert '<picture><img src="assets/work-fish.svg"' in card_group, 'Prevent GitHub auto-linking the placeholder.'
    forbidden={'script','foreignObject','image','a','animate','animateTransform','set'}
    svgs=sorted(ASSETS.rglob('*.svg'))
    for path in svgs:
        data=path.read_text(); root=ET.fromstring(data)
        assert root.attrib.get('viewBox'), path
        assert path.stat().st_size < 2_000_000, path
        for el in root.iter():
            tag=el.tag.rsplit('}',1)[-1]
            assert tag not in forbidden, (path,tag)
            for key,value in el.attrib.items():
                assert not key.lower().startswith('on'), (path,key)
                if key.rsplit('}',1)[-1] in ('href','src'):
                    assert value.startswith('#'), (path,value)
                for ref in re.findall(r'url\(([^)]+)\)',value):
                    assert ref.startswith('#'), (path,ref)
        assert not re.search(r'<\?(?!xml)|<!ENTITY|<!DOCTYPE',data,re.I), path
    manifest=json.loads((ASSETS/'materials/manifest.json').read_text())
    for item in manifest['materials']:
        data=(ASSETS/'materials'/item['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==item['sha256'], item['file']
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
    print(json.dumps({'status':'PASS','svg_files':len(svgs),'readme_images':len(parser.images),'mobile_sources':len(parser.sources),'project_links':len(parser.links),'generation':'byte-identical','embedded_raster':False,'svg_bytes':sum(p.stat().st_size for p in svgs)}))

if __name__=='__main__': main()
