"""CLI tool for generating branded QR codes with custom colors and logos."""

from datetime import datetime
from pathlib import Path

import click
import qrcode
from PIL import Image, ImageDraw
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer

DEFAULT_PRIMARY = "#0047BA"
DEFAULT_SECONDARY = "#00CE7C"


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple.

    Raises:
        click.BadParameter: If the hex color string is not a valid #RRGGBB format.
    """
    cleaned = hex_color.lstrip("#")
    if len(cleaned) != 6:
        raise click.BadParameter(
            f"Invalid hex color '{hex_color}'. Expected #RRGGBB format (e.g. #FF00AA)."
        )
    try:
        r, g, b = (int(cleaned[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        raise click.BadParameter(
            f"Invalid hex color '{hex_color}'. Contains non-hex characters."
        )
    return (r, g, b)


def _build_eye_mask(
    img_size: int, scale: int, border: int, corners: list[tuple[int, int]]
) -> Image.Image:
    """Create a mask highlighting rectangular regions at the given corner positions.

    Args:
        img_size: Width/height of the square QR image in pixels.
        scale: Module size in pixels (box_size).
        border: Border size in modules.
        corners: List of (corner_x, corner_y) pixel positions for each finder pattern.
    """
    finder_px = 7 * scale
    mask = Image.new("L", (img_size, img_size), 0)
    draw = ImageDraw.Draw(mask)

    for cx, cy in corners:
        draw.rectangle((cx, cy, cx + finder_px, cy + finder_px), fill=255)

    return mask


def style_inner_eyes(img: Image.Image, scale: int, border: int) -> Image.Image:
    """Create mask for the inner eyes of the QR code."""
    img_size = img.size[0]
    finder_px = 7 * scale
    border_px = border * scale
    inner_offset = 4 * scale

    corners = [
        (inner_offset + border_px, inner_offset + border_px),
        (img_size - border_px - finder_px + inner_offset, border_px + inner_offset),
        (border_px + inner_offset, img_size - border_px - finder_px + inner_offset),
    ]
    return _build_eye_mask(img_size, scale, border, corners)


def style_outer_eyes(img: Image.Image, scale: int, border: int) -> Image.Image:
    """Create mask for the outer eyes of the QR code."""
    img_size = img.size[0]
    finder_px = 7 * scale
    border_px = border * scale

    corners = [
        (border_px, border_px),
        (img_size - border_px - finder_px, border_px),
        (border_px, img_size - border_px - finder_px),
    ]
    return _build_eye_mask(img_size, scale, border, corners)


def _generate_filename() -> str:
    """Generate a timestamped output filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"qr_{timestamp}.png"


def _build_qr(url: str, scale: int, border: int) -> qrcode.QRCode:
    """Create and populate a QRCode object."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=border,
        box_size=scale,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr


def _composite_qr(
    qr: qrcode.QRCode,
    primary_color: tuple[int, int, int],
    secondary_color: tuple[int, int, int],
    logo: str | None,
    scale: int,
    border: int,
) -> Image.Image:
    """Render QR layers and composite inner eyes, outer eyes, and body."""
    qr_inner_eyes_img = qr.make_image(
        image_factory=StyledPilImage,
        color_mask=SolidFillColorMask(front_color=primary_color),
    )

    qr_outer_eyes_img = qr.make_image(
        image_factory=StyledPilImage,
        eye_drawer=RoundedModuleDrawer(radius_ratio=1),
        color_mask=SolidFillColorMask(front_color=primary_color),
    )

    body_kwargs: dict = {
        "image_factory": StyledPilImage,
        "module_drawer": RoundedModuleDrawer(),
        "color_mask": SolidFillColorMask(front_color=secondary_color),
    }
    if logo:
        body_kwargs["embeded_image_path"] = logo

    qr_body_img = qr.make_image(**body_kwargs)

    qr_inner_rgb = qr_inner_eyes_img.convert("RGB")
    qr_outer_rgb = qr_outer_eyes_img.convert("RGB")
    qr_body_rgb = qr_body_img.convert("RGB")

    inner_mask = style_inner_eyes(qr_body_rgb, scale, border)
    outer_mask = style_outer_eyes(qr_body_rgb, scale, border)

    intermediate = Image.composite(qr_inner_rgb, qr_body_rgb, inner_mask)
    return Image.composite(qr_outer_rgb, intermediate, outer_mask)


@click.command()
@click.argument("url")
@click.option("--logo", "-l", type=click.Path(exists=True), help="Path to logo image file.")
@click.option(
    "--primary", "-p", default=DEFAULT_PRIMARY,
    help=f"Primary brand color (hex). Default: {DEFAULT_PRIMARY}",
)
@click.option(
    "--secondary", "-s", default=DEFAULT_SECONDARY,
    help=f"Secondary brand color (hex). Default: {DEFAULT_SECONDARY}",
)
@click.option("--output", "-o", type=click.Path(), help="Output filename. Defaults to qr_<timestamp>.png")
@click.option("--scale", type=int, default=10, help="Scale (box size) of the QR code. Default: 10")
@click.option("--border", type=int, default=0, help="Border size in modules. Default: 0")
def generate(
    url: str,
    logo: str | None,
    primary: str,
    secondary: str,
    output: str | None,
    scale: int,
    border: int,
) -> None:
    """Generate a branded QR code with custom colors and logo.

    URL is the link to encode in the QR code.
    """
    primary_color = hex_to_rgb(primary)
    secondary_color = hex_to_rgb(secondary)

    output_path = Path(output) if output else Path(_generate_filename())

    click.echo(f"Generating QR for: {url}")
    click.echo(f"Primary: {primary} | Secondary: {secondary}")
    if logo:
        click.echo(f"Logo: {logo}")
    click.echo(f"Output: {output_path}")

    qr = _build_qr(url, scale, border)
    final_image = _composite_qr(qr, primary_color, secondary_color, logo, scale, border)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_image.save(str(output_path))
    click.echo(click.style(f"QR generated successfully: {output_path}", fg="green"))


def cli() -> None:
    generate()


if __name__ == "__main__":
    cli()
