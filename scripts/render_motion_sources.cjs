// Rasterize the three existing SVG compositions once. No artwork is synthesized.
const fs = require('node:fs/promises');
const path = require('node:path');
const sharp = require(process.env.PROFILE_SHARP_MODULE || 'sharp');

async function main() {
  const [assets, output] = process.argv.slice(2);
  if (!assets || !output) throw new Error('Usage: render_motion_sources.cjs ASSETS OUTPUT');
  for (const [name, width] of [['hero', 1024], ['hero-mobile', 768], ['work-fish', 320]]) {
    await sharp(path.join(assets, `${name}.svg`))
      .resize({ width }).flatten({ background: '#11131A' })
      .png().toFile(path.join(output, `${name}.png`));
  }
  await fs.writeFile(path.join(output, 'renderer.json'), JSON.stringify({
    node: process.version, sharp: sharp.versions.sharp, librsvg: sharp.versions.rsvg,
  }));
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
