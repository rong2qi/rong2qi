#!/usr/bin/env python3
"""Build the refracted-icon profile from deterministic, original SVG geometry."""
from html import escape
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'

# Your words go here. Empty tuples preserve the approved writing space.
HERO_LINES = ()
NOW_LINES = ()
ASHES_LINES = ()

NIGHT = '#11131A'
BONE = '#D3CBC2'
JADE = '#6F8983'
ROSE = '#8D5660'
GLOW = '#E7CBB4'
FONT = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def words(lines, x, y, size, line_height):
    return ''.join(
        f'<text x="{x}" y="{y + index * line_height}" font-size="{size}">{escape(line)}</text>'
        for index, line in enumerate(lines)
    )


def label(name, y, mobile=False, hollow=False):
    size = 48 if mobile else 19
    dot = (
        f'<circle cx="45" cy="{y - 6}" r="4" fill="none" stroke="{BONE}"/>'
        if hollow else
        f'<circle cx="45" cy="{y - 6}" r="4" fill="{ROSE}"/>'
    )
    return f'{dot}<text x="66" y="{y}" font-size="{size}" letter-spacing="4">{name}</text>'


def write(name, width, height, body, title):
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
<title id="title">{escape(title)}</title>
<rect width="{width}" height="{height}" fill="{NIGHT}"/>
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="{BONE}" stroke-opacity=".14"/>
<g fill="{BONE}" font-family="{FONT}">{body}</g>
</svg>\n''',
        encoding='utf-8',
    )


def hero_world(mobile=False):
    transform = 'translate(-210 -90) scale(1.27)' if mobile else ''
    return f'''<g id="world" transform="{transform}">
  <g id="orbit" fill="none" stroke-linecap="round">
    <path d="M580 328A180 235 0 0 1 760 93" stroke="{GLOW}" stroke-width="3" stroke-opacity=".72"/>
    <path d="M792 97A180 235 0 0 1 940 292" stroke="{BONE}" stroke-width="2" stroke-opacity=".42"/>
    <path d="M940 363A180 235 0 0 1 806 556" stroke="{ROSE}" stroke-width="3" stroke-opacity=".58"/>
    <path d="M710 555A180 235 0 0 1 582 390" stroke="{JADE}" stroke-width="2" stroke-opacity=".42"/>
  </g>
  <g id="stars" fill="{GLOW}">
    <circle cx="566" cy="184" r="2.6"/><circle cx="938" cy="206" r="2.1"/>
    <circle cx="970" cy="421" r="2.8"/><circle cx="548" cy="474" r="2.2"/>
    <path d="M566 184L611 224L548 474M938 206L904 247L970 421" fill="none" stroke="{BONE}" stroke-width="1" stroke-opacity=".24"/>
  </g>
  <g id="portrait-silhouette">
    <path d="M555 824C574 707 611 626 675 568C702 544 716 517 720 478H805C813 520 833 544 870 565C928 599 971 683 994 824Z" fill="{NIGHT}" stroke="{BONE}" stroke-width="2" stroke-opacity=".28"/>
    <path d="M608 824C632 690 674 613 742 574C791 546 839 563 884 602C928 640 954 717 970 824Z" fill="{ROSE}" fill-opacity=".08"/>
    <path d="M719 448C730 481 731 512 708 541C743 570 790 570 828 537C805 511 801 478 810 444Z" fill="{BONE}" fill-opacity=".36" stroke="{BONE}" stroke-opacity=".34"/>
    <g id="face-shadow">
      <path d="M682 252C684 190 721 159 766 164C817 170 847 218 837 294L824 390C815 445 786 480 751 474C714 468 691 426 686 369Z" fill="{NIGHT}" stroke="{BONE}" stroke-width="2" stroke-opacity=".34"/>
      <path d="M758 302C770 297 782 299 791 306" fill="none" stroke="{ROSE}" stroke-width="5" stroke-linecap="round" stroke-opacity=".82"/>
    </g>
    <g id="hair-static">
      <path d="M745 151C677 146 638 200 634 274C629 370 655 427 610 507C580 559 574 613 601 684C630 626 668 592 681 526C692 472 666 389 680 309C693 235 720 205 765 177Z" fill="{BONE}" fill-opacity=".13" stroke="{BONE}" stroke-width="3" stroke-opacity=".48"/>
      <path d="M760 151C831 151 871 209 874 284C878 376 850 438 893 500C932 556 955 617 935 690C905 629 860 595 849 523C839 461 869 388 850 294C837 228 806 187 760 151Z" fill="{JADE}" fill-opacity=".15" stroke="{BONE}" stroke-width="3" stroke-opacity=".44"/>
      <path d="M692 206C739 172 803 179 837 224C806 212 780 223 762 255C744 287 737 341 706 372C685 332 673 254 692 206Z" fill="{NIGHT}" fill-opacity=".96"/>
      <path d="M682 280C651 392 694 493 650 575M840 282C871 385 821 477 872 567M705 188C667 252 671 363 701 438M819 190C860 270 850 383 816 451" fill="none" stroke="{BONE}" stroke-width="2" stroke-opacity=".46"/>
      <path d="M677 574C706 615 715 684 690 754M854 566C828 620 824 685 853 758" fill="none" stroke="{JADE}" stroke-width="3" stroke-opacity=".48"/>
    </g>
    <g id="hair-drift-left" fill="none" stroke-linecap="round">
      <path d="M649 501C603 534 564 581 548 649C574 620 611 608 638 572" stroke="{BONE}" stroke-width="3" stroke-opacity=".58"/>
      <path d="M635 537C582 565 540 608 520 690" stroke="{JADE}" stroke-width="2" stroke-opacity=".48"/>
    </g>
    <g id="hair-drift-right" fill="none" stroke-linecap="round">
      <path d="M880 501C929 536 966 582 987 646C957 620 922 607 894 571" stroke="{BONE}" stroke-width="3" stroke-opacity=".54"/>
      <path d="M897 539C951 567 988 611 1004 683" stroke="{ROSE}" stroke-width="2" stroke-opacity=".44"/>
    </g>
    <path d="M690 590C742 614 803 613 857 588" fill="none" stroke="{GLOW}" stroke-width="2" stroke-opacity=".22"/>
  </g>
</g>'''


def hero(mobile=False):
    identity_size = 48 if mobile else 24
    now_size = 48 if mobile else 15
    date_size = 48 if mobile else 15
    now_x, now_y = ((42, 112) if mobile else (934, 49))
    body = f'''<defs>
  <linearGradient id="night-wash" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="{JADE}" stop-opacity=".11"/><stop offset=".55" stop-color="{NIGHT}" stop-opacity="0"/><stop offset="1" stop-color="{ROSE}" stop-opacity=".12"/>
  </linearGradient>
  <linearGradient id="seam-light" x1="0" y1="0" x2="0" y2="1">
    <stop stop-color="{GLOW}" stop-opacity=".12"/><stop offset=".42" stop-color="{GLOW}" stop-opacity=".76"/><stop offset="1" stop-color="{ROSE}" stop-opacity=".2"/>
  </linearGradient>
</defs>
<rect x="2" y="2" width="1020" height="861" fill="url(#night-wash)"/>
<g id="identity"><text x="42" y="50" font-size="{identity_size}" letter-spacing="2">rong2qi</text></g>
<g id="now-label"><text x="{now_x}" y="{now_y}" font-size="{now_size}" letter-spacing="3">now</text></g>
<path d="M42 79H57M43 166V318" fill="none" stroke="{BONE}" stroke-width="1" stroke-opacity=".42"/>
<g id="hand-date" transform="rotate(-3 42 390)"><text x="42" y="390" font-size="{date_size}" font-style="italic" letter-spacing="2" fill="{BONE}" fill-opacity=".62">10 · 09 · 26</text></g>
<g id="seam"><path d="M676 1V864" stroke="url(#seam-light)" stroke-width="2"/></g>
{hero_world(mobile)}
<g id="hero-words">{words(HERO_LINES, 176, 224, 42, 62)}</g>
<g id="now-words">{words(NOW_LINES, 74, 628, 22, 33)}</g>'''
    filename = 'hero-mobile.svg' if mobile else 'hero.svg'
    write(filename, 1024, 865, body,
          'rong2qi · now — original female half silhouette, broken orbit and quiet refracted light')


def works(mobile=False):
    y = 58 if mobile else 42
    body = f'''<g id="works-label">{label('works', y, mobile)}</g>
<path d="M760 18A52 52 0 0 1 831 57" fill="none" stroke="{JADE}" stroke-width="2" stroke-opacity=".5"/>
<path d="M845 51H979" stroke="{ROSE}" stroke-width="1" stroke-opacity=".45"/>'''
    write('works-divider-mobile.svg' if mobile else 'works-divider.svg',
          1024, 92 if mobile else 68, body, 'works')


def card_art(slug):
    if slug == 'fish':
        return f'''<path d="M24 166C76 116 131 109 187 145C224 169 258 170 298 139" fill="none" stroke="{JADE}" stroke-width="4" stroke-opacity=".72"/>
<path d="M25 183C87 151 136 157 183 183C225 206 264 202 298 177" fill="none" stroke="{BONE}" stroke-width="2" stroke-opacity=".4"/>
<path d="M77 76A75 75 0 0 1 214 81" fill="none" stroke="{GLOW}" stroke-width="3" stroke-opacity=".54"/>
<circle cx="80" cy="75" r="3" fill="{ROSE}"/>'''
    if slug == 'jinbao':
        return f'''<rect x="117" y="18" width="86" height="207" fill="{GLOW}" fill-opacity=".12"/>
<path d="M160 18V225" stroke="{GLOW}" stroke-width="2" stroke-opacity=".6"/>
<path d="M76 203C78 170 95 151 117 151C139 151 153 170 154 203Z" fill="{NIGHT}" stroke="{BONE}" stroke-opacity=".38"/>
<path d="M167 203C169 165 188 143 213 143C238 143 253 165 254 203Z" fill="{NIGHT}" stroke="{JADE}" stroke-opacity=".48"/>
<path d="M91 157L99 141L107 158M190 149L200 130L211 149" fill="none" stroke="{BONE}" stroke-width="2" stroke-opacity=".55"/>'''
    if slug == 'orchestrator':
        return f'''<path d="M26 204L287 43" stroke="{ROSE}" stroke-width="5" stroke-opacity=".66"/>
<path d="M41 215L301 54" stroke="{GLOW}" stroke-width="1" stroke-opacity=".58"/>
<circle cx="159" cy="126" r="42" fill="{ROSE}" fill-opacity=".1" stroke="{BONE}" stroke-opacity=".25"/>
<path d="M69 65L159 126L259 89M159 126L224 198" fill="none" stroke="{JADE}" stroke-width="2" stroke-opacity=".45"/>
<circle cx="69" cy="65" r="3"/><circle cx="259" cy="89" r="3"/><circle cx="224" cy="198" r="3"/>'''
    if slug == 'speakloop':
        return f'''<path d="M83 139A77 77 0 0 1 237 139" fill="none" stroke="{BONE}" stroke-width="5" stroke-opacity=".55"/>
<path d="M96 139V197M224 139V197" stroke="{JADE}" stroke-width="15" stroke-linecap="round" stroke-opacity=".7"/>
<path d="M132 91A55 55 0 0 1 209 109" fill="none" stroke="{ROSE}" stroke-width="3" stroke-opacity=".52"/>
<circle cx="160" cy="139" r="4" fill="{GLOW}"/>'''
    return f'''<path d="M56 35L142 58L116 113L178 94L205 154L274 137L247 219L158 206L98 224L42 169Z" fill="{BONE}" fill-opacity=".13" stroke="{BONE}" stroke-width="2" stroke-opacity=".42"/>
<path d="M142 58L158 206M116 113L247 219M42 169L205 154" fill="none" stroke="{JADE}" stroke-width="2" stroke-opacity=".42"/>
<path d="M177 95L205 154L159 206" fill="none" stroke="{ROSE}" stroke-width="4" stroke-opacity=".62"/>
<circle cx="205" cy="154" r="4" fill="{GLOW}"/>'''


PROJECTS = (
    ('fish', 'fish-meditate', ('fish-meditate',)),
    ('jinbao', 'desktop-pet-jinbao', ('desktop-pet-jinbao',)),
    ('orchestrator', 'prompt-agent-orchestrator', ('prompt-agent-', 'orchestrator')),
    ('speakloop', 'SpeakLoop', ('SpeakLoop',)),
    ('chief', 'chief-of-staff-codex', ('chief-of-staff-codex',)),
)


def cards():
    for slug, name, lines in PROJECTS:
        labels = ''.join(
            f'<text x="12" y="{260 + index * 30}" font-size="28" letter-spacing=".2">{escape(line)}</text>'
            for index, line in enumerate(lines)
        )
        underline_y = 310 if len(lines) > 1 else 296
        body = f'''<g id="fragment-{slug}">{card_art(slug)}</g>
<rect x="8" y="8" width="304" height="219" fill="none" stroke="{BONE}" stroke-opacity=".24"/>
{labels}
<path d="M12 {underline_y}H88" stroke="{ROSE}" stroke-width="2" stroke-opacity=".52"/>'''
        write(f'work-{slug}.svg', 320, 326, body, name)


def footer(mobile=False):
    ashes_y, trace_y = ((58, 235) if mobile else (46, 222))
    body = f'''<path d="M41 10H981" stroke="{BONE}" stroke-opacity=".2"/>
<g id="ashes-label">{label('ashes', ashes_y, mobile)}</g>
<g id="ink-remains">
  <path d="M420 161C492 112 525 68 590 59C639 52 671 73 716 67C773 60 807 33 866 45C815 76 788 101 746 111C686 126 645 104 594 119C540 135 499 172 420 161Z" fill="{BONE}" fill-opacity=".12"/>
  <path d="M470 145C541 129 574 93 624 91C680 89 709 119 759 104C718 139 679 148 626 136C570 123 535 154 470 145Z" fill="{NIGHT}" stroke="{BONE}" stroke-opacity=".22"/>
  <path d="M404 177L878 48" fill="none" stroke="{JADE}" stroke-width="2" stroke-opacity=".54"/>
  <path d="M563 132C626 105 697 98 792 79" fill="none" stroke="{ROSE}" stroke-width="3" stroke-opacity=".42"/>
</g>
<g id="ashes-words">{words(ASHES_LINES, 69, 91, 20, 30)}</g>
<path d="M41 184H981" stroke="{BONE}" stroke-opacity=".2"/>
<g id="trace-label">{label('trace', trace_y, mobile, True)}</g>'''
    write('ashes-trace-mobile.svg' if mobile else 'ashes-trace.svg', 1024, 308, body,
          'ashes · trace — monochrome ink, jade diagonal and open writing space')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest():
    assets = []
    for path in sorted(ASSETS.glob('*.svg')):
        root = ET.parse(path).getroot()
        assets.append({
            'file': path.name,
            'width': int(root.attrib['width']),
            'height': int(root.attrib['height']),
            'bytes': path.stat().st_size,
            'sha256': sha(path),
        })
    manifest = {
        'schema': 1,
        'candidate_label': 'PROFILE-REFRACTED-20260910-03',
        'style': '折光圣像 / refracted icon',
        'method': (
            'Original deterministic SVG geometry; no reference-image pixels, '
            'external fonts, or remote resources'
        ),
        'palette': {
            'night': NIGHT,
            'bone': BONE,
            'jade': JADE,
            'rose': ROSE,
            'glow': GLOW,
        },
        'generator': {
            'file': 'scripts/build_assets.py',
            'sha256': sha(Path(__file__)),
        },
        'assets': assets,
    }
    (ASSETS / 'asset-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    for mobile in (False, True):
        hero(mobile)
        works(mobile)
        footer(mobile)
    cards()
    write_manifest()


if __name__ == '__main__':
    main()
