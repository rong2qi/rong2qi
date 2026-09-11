#!/usr/bin/env python3
"""Verify the selected master, README paths, raster assets, links and regeneration."""

from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
import hashlib
import importlib.util
import json
import sys

from PIL import Image


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
MASTER_SHA256 = "2f61ae115f1c3f6924bb7db23868d8324f73754bb632d60cb91760e609b965c1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReadmeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.links = []
        self.sources = []
        self.pictures = []
        self.picture = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "picture":
            self.picture = {"sources": [], "image": None}
        if tag == "img":
            self.images.append(attributes)
            if self.picture is not None:
                self.picture["image"] = attributes
        if tag == "source":
            self.sources.append(attributes)
            if self.picture is not None:
                self.picture["sources"].append(attributes)
        if tag == "a":
            self.links.append(attributes["href"])

    def handle_endtag(self, tag):
        if tag == "picture":
            self.pictures.append(self.picture)
            self.picture = None


def main():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    parser = ReadmeParser()
    parser.feed(readme)

    assert len(parser.images) == 8, "Expected hero, works, five project fragments and footer."
    assert len(parser.sources) == 5, "Hero and section labels need responsive sources."
    assert len(parser.pictures) == 3
    hero_picture = parser.pictures[0]
    assert hero_picture["image"]["src"] == "assets/hero-motion.gif"
    assert [
        (source["media"], source["srcset"]) for source in hero_picture["sources"]
    ] == [
        (
            "(prefers-reduced-motion: reduce) and (max-width: 768px)",
            "assets/hero-mobile.jpg",
        ),
        ("(prefers-reduced-motion: reduce)", "assets/hero.jpg"),
        ("(max-width: 768px)", "assets/hero-mobile-motion.gif"),
    ], "Reduced-motion sources must precede the responsive motion source."
    assert parser.pictures[1] == {
        "sources": [{"media": "(max-width: 768px)", "srcset": "assets/works-mobile.jpg"}],
        "image": {"src": "assets/works.jpg", "alt": "works", "width": "100%"},
    }
    assert parser.pictures[2] == {
        "sources": [
            {"media": "(max-width: 768px)", "srcset": "assets/ashes-trace-mobile.jpg"}
        ],
        "image": {
            "src": "assets/ashes-trace.jpg",
            "alt": "ashes · trace — 山、水、墨色与留白",
            "width": "100%",
        },
    }

    referenced = []
    for item in parser.images + parser.sources:
        url = item.get("src", item.get("srcset"))
        parts = urlsplit(url)
        assert not parts.scheme and not url.startswith("/"), url
        path = (ROOT / url).resolve()
        assert path.is_relative_to(ASSETS.resolve()) and path.is_file(), url
        if "src" in item:
            assert item.get("alt"), f"Missing alt text: {url}"
        referenced.append(path)
    assert not any(path.suffix.lower() == ".svg" for path in referenced)
    assert ASSETS / "source/nuwa-a-sky-rift.png" not in referenced

    expected_projects = {
        "https://github.com/rong2qi/desktop-pet-jinbao",
        "https://github.com/rong2qi/prompt-agent-orchestrator",
        "https://github.com/rong2qi/SpeakLoop",
        "https://github.com/rong2qi/chief-of-staff-codex",
    }
    assert set(parser.links) == expected_projects, parser.links
    assert "href=\"https://github.com/rong2qi/fish-meditate\"" not in readme
    assert "[GitHub ↗](https://github.com/rong2qi)" in readme
    assert "[repositories ↗](https://github.com/rong2qi?tab=repositories)" in readme
    assert len(parser.links) + 2 == 6
    card_group = readme.split("<p>", 1)[1].split("</p>", 1)[0]
    assert card_group.count("<img ") == 5
    assert card_group.lstrip().startswith('<img src="assets/work-fish.jpg"')
    assert "女娲" in parser.images[0]["alt"] and "五色石" in parser.images[0]["alt"]

    master = ASSETS / "source/nuwa-a-sky-rift.png"
    assert sha(master) == MASTER_SHA256
    with Image.open(master) as image:
        assert image.format == "PNG" and image.size == (1536, 1024) and image.mode == "RGB"

    manifest_path = ASSETS / "asset-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == 2
    assert manifest["candidate_label"] == "PROFILE-NUWA-A-20260911-01"
    assert manifest["style"] == "女娲 · A 天裂 / Nüwa sky rift"
    assert manifest["source"] == {
        "file": "assets/source/nuwa-a-sky-rift.png",
        "sha256": MASTER_SHA256,
        "width": 1536,
        "height": 1024,
        "origin": "Codex built-in ImageGen, selected by the user with: A最好看。",
        "prompt_summary": manifest["source"]["prompt_summary"],
    }
    assert "no copied figure" in manifest["source"]["prompt_summary"]
    assert manifest["generator"] == {
        "file": "scripts/build_assets.py",
        "sha256": sha(ROOT / "scripts/build_assets.py"),
    }
    for font in manifest["fonts"]:
        font_path = Path(font["file"])
        assert font_path.is_file() and sha(font_path) == font["sha256"]

    expected_dimensions = {
        "hero.jpg": (1200, 800),
        "hero-mobile.jpg": (768, 768),
        "works.jpg": (1024, 108),
        "works-mobile.jpg": (1024, 108),
        "work-fish.jpg": (480, 600),
        "work-jinbao.jpg": (480, 600),
        "work-orchestrator.jpg": (480, 600),
        "work-speakloop.jpg": (480, 600),
        "work-chief.jpg": (480, 600),
        "ashes-trace.jpg": (1024, 283),
        "ashes-trace-mobile.jpg": (1024, 283),
    }
    assert {item["file"] for item in manifest["assets"]} == set(expected_dimensions)
    for item in manifest["assets"]:
        path = ASSETS / item["file"]
        with Image.open(path) as image:
            assert image.format == "JPEG"
            assert image.size == expected_dimensions[item["file"]]
            image.verify()
        assert item["format"] == "JPEG"
        assert (item["width"], item["height"]) == expected_dimensions[item["file"]]
        assert item["bytes"] == path.stat().st_size
        assert item["sha256"] == sha(path)
        assert item["bytes"] < 900_000, f"Static asset too large: {path}"

    labels = manifest["labels"]
    assert labels["mobile_min_font_px"] * labels["public_mobile_canvas_width"] / labels["mobile_source_width"] >= 14
    assert labels["mobile_section_font_px"] * labels["public_mobile_canvas_width"] / labels["section_source_width"] >= 14
    assert labels["desktop_section_font_px"] < labels["mobile_section_font_px"]
    assert labels["card_font_px"] * labels["card_render_width"] / labels["card_source_width"] >= 14

    actual_rasters = {
        path.name for path in ASSETS.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif"}
    }
    assert actual_rasters == set(expected_dimensions) | {
        "hero-motion.gif",
        "hero-mobile-motion.gif",
    }, actual_rasters
    assert not list(ASSETS.glob("*.svg")), "Legacy geometric SVGs must not ship in Candidate A."

    spec = importlib.util.spec_from_file_location("profile_builder", ROOT / "scripts/build_assets.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with TemporaryDirectory(prefix="nuwa-static-verify-") as folder:
        builder.ASSETS = Path(folder)
        builder.main()
        for name in expected_dimensions:
            assert (Path(folder) / name).read_bytes() == (ASSETS / name).read_bytes(), (
                f"Regenerate {name}"
            )
        assert (Path(folder) / "asset-manifest.json").read_bytes() == manifest_path.read_bytes()

    print(
        json.dumps(
            {
                "status": "PASS",
                "selected_master_sha256": MASTER_SHA256,
                "readme_images": len(parser.images),
                "picture_sources": len(parser.sources),
                "project_links": len(parser.links),
                "accessible_links_total": len(parser.links) + 2,
                "static_assets": len(expected_dimensions),
                "legacy_svg_assets": 0,
                "generation": "byte-identical",
                "mobile_min_rendered_label_px": min(
                    labels["mobile_min_font_px"]
                    * labels["public_mobile_canvas_width"]
                    / labels["mobile_source_width"],
                    labels["mobile_section_font_px"]
                    * labels["public_mobile_canvas_width"]
                    / labels["section_source_width"],
                    labels["card_font_px"]
                    * labels["card_render_width"]
                    / labels["card_source_width"],
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
