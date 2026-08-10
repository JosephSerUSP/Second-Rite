# Thestra Studio application icons

`icon-32.png` is the canonical authored pixel-art source. It is the original
32x32 artwork byte-for-byte.

The other PNG sizes are intentionally mechanical nearest-neighbor derivatives
of that source so every expected size exists as a real file and can be
hand-edited independently later. Once a size is hand-tuned, treat it as an
optical variant rather than regenerating it blindly from `icon-32.png`.

## Raster variants

- `icon-16.png`
- `icon-24.png`
- `icon-32.png` — canonical authored source
- `icon-48.png`
- `icon-64.png`
- `icon-128.png`
- `icon-256.png`
- `icon-512.png`
- `icon-1024.png`

## Platform containers

- `icon.ico` — Windows container with 16, 24, 32, 48, 64, 128, and 256px PNG entries.
- `icon.icns` — macOS container with 16, 32, 64, 128, and 256px PNG entries.

The Electron window uses `icon.ico` on Windows and `icon-256.png` on other
platforms. The larger PNGs remain available for packaging and for future
hand-tuned macOS/HiDPI variants.
