# QR Gen CLI

A simple CLI tool to generate branded QR codes with custom colors and logos.

## Installation

```bash
uv tool install .
```

## Usage

```bash
qrgen "https://example.com" [OPTIONS]
```

### Options

*   -l, --logo PATH: Path to the logo image file to embed in the center.
*   -p, --primary TEXT: Primary brand color (Hex). Used for the three corner eyes. Default: `#0047BA`.
*   -s, --secondary TEXT: Secondary brand color (Hex). Used for the main QR code pattern. Default: `#00CE7C`.
*   -o, --output TEXT: Output filename. Defaults to `qr_<timestamp>.png`.
*   --scale INTEGER: Scale (box size) of each QR module. Higher values produce larger, higher-resolution images. Default: `10`.

### Example

```bash
qrgen "https://rainbowdrains.ca" \
  --primary "#062d46" \
  --secondary "#00b5e2" \
  --logo "./logo.png" \
  --scale 40 \
  --output "rainbow_qr.png"
```

## Requirements

*   Python 3.12+
*   `qrcode[pil]`
*   `click`
*   `pillow`

```