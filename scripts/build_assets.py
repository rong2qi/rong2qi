#!/usr/bin/env python3
"""Compose local vector materials and editable type. Python standard library only."""
from pathlib import Path
from html import escape
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
MATERIALS = ASSETS / 'materials'

# Your words go here; empty tuples leave the reference's writing areas open.
HERO_LINES = ()
NOW_LINES = ()
ASHES_LINES = ()
GROUND = '#111212'
INK = '#d9d5d0'

def material(name, x, y, scale=1):
    tree = ET.parse(MATERIALS / f'{name}.svg').getroot()
    paths = []
    for el in tree:
        if el.tag.rsplit('}', 1)[-1] == 'path':
            paths.append(f'<path fill="{el.attrib["fill"]}" d="{el.attrib["d"]}"/>')
    return f'<g transform="translate({x} {y}) scale({scale})">' + ''.join(paths) + '</g>'

def words(lines, x, y, size, line_height):
    return ''.join(f'<text x="{x}" y="{y+i*line_height}" font-size="{size}">{escape(line)}</text>' for i,line in enumerate(lines))

def label(name, y, mobile=False, hollow=False):
    size = 42 if mobile else 19
    dot = f'<circle cx="45" cy="{y-6}" r="4" fill="none" stroke="{INK}"/>' if hollow else f'<circle cx="45" cy="{y-6}" r="4" fill="#d2bbb5"/>'
    return f'{dot}<text x="66" y="{y}" font-size="{size}" letter-spacing="4">{name}</text>'

def write(name, height, body, title, width=1024):
    (ASSETS / name).write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
<title id="title">{escape(title)}</title>
<rect width="{width}" height="{height}" fill="{GROUND}"/>
<g fill="{INK}" font-family="Georgia, 'Times New Roman', serif">{body}</g>
</svg>\n''', encoding='utf-8')

def hero(mobile=False):
    size = 44 if mobile else 24
    body = f'''<defs><linearGradient id="seam" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#807575" stop-opacity=".3"/><stop offset=".38" stop-color="#b9a49f" stop-opacity=".8"/><stop offset="1" stop-color="#c6a29c" stop-opacity=".35"/></linearGradient></defs>
<g id="identity"><text x="41" y="{63 if mobile else 49}" font-size="{size}" letter-spacing="2">rong2qi</text></g>
<path d="M42 79h12M43 183v133" fill="none" stroke="#b2aaa2" stroke-opacity=".6" stroke-width=".8"/>
{material('hero-mineral',330,0)}
<path d="M685 .5V511" stroke="url(#seam)" stroke-width=".8"/>
<path d="M0 511.5H1024" stroke="#6c6b65" stroke-opacity=".32"/>
<g id="hero-words">{words(HERO_LINES,190,220,44,66)}</g>
<g id="now-label">{label('now',564 if mobile else 560,mobile)}</g>
<g id="now-words">{words(NOW_LINES,74,629,22,33)}</g>
<path d="M628 512V589" stroke="#bca39e" stroke-opacity=".38" stroke-width=".8"/>
{material('now-filament',448,589)}
'''
    write('hero-mobile.svg' if mobile else 'hero.svg',865,body,'rong2qi · now — open writing areas, mineral seam and rose light')

def works(mobile=False):
    body=f'<g id="works-label">{label("works",62 if mobile else 42,mobile)}</g>'
    write('works-divider-mobile.svg' if mobile else 'works-divider.svg',92 if mobile else 68,body,'works')

PROJECTS = [
    ('fish','fish-water','fish-meditate'),
    ('jinbao','jinbao-curtain','desktop-pet-jinbao'),
    ('orchestrator','orchestrator-light','orchestrator'),
    ('speakloop','speakloop-headphones','SpeakLoop'),
    ('chief','chief-mineral','chief-of-staff'),
]

def cards():
    for slug,source,name in PROJECTS:
        body=material(source,8,8,304/165)
        body+=f'<rect x="8" y="8" width="304" height="219.2485" fill="none" stroke="#aaa39c" stroke-opacity=".28"/>'
        body+=f'<text x="12" y="264" font-size="26">{name}</text>'
        write(f'work-{slug}.svg',326,body,name,320)

def footer(mobile=False):
    body=f'''<path d="M41 9H981" stroke="#6c6b65" stroke-opacity=".45"/>
<g id="ashes-label">{label('ashes',57 if mobile else 46,mobile)}</g>
{material('ashes-mineral',404,34)}
<g id="ashes-words">{words(ASHES_LINES,69,89,20,30)}</g>
<path d="M41 184H981" stroke="#6c6b65" stroke-opacity=".45"/>
<g id="trace-label">{label('trace',235 if mobile else 222,mobile,True)}</g>'''
    write('ashes-trace-mobile.svg' if mobile else 'ashes-trace.svg',308,body,'ashes · trace — quiet mineral remains and open writing space')

def main():
    for mobile in (False, True):
        hero(mobile); works(mobile); footer(mobile)
    cards()

if __name__ == '__main__':
    main()
