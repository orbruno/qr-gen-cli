import click
import qrcode
from PIL import Image, ImageDraw
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    RoundedModuleDrawer,
    VerticalBarsDrawer,
    SquareModuleDrawer
)
from qrcode.image.styles.colormasks import SolidFillColorMask
from datetime import datetime
import os

# Fix for PIL compatibility
if not hasattr(Image, 'Resampling'):
    Image.Resampling = Image

def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def style_inner_eyes(img):
    """Creates mask for the inner eyes of the QR code."""
    img_size = img.size[0]
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    # These coordinates seem tuned for box_size=10 (70px finder patterns)
    draw.rectangle((40, 40, 70, 70), fill=255)  # top left eye
    draw.rectangle((img_size-70, 0, img_size, 70), fill=255)  # top right eye
    draw.rectangle((1, img_size-70, 70, img_size-70), fill=255)  # bottom left eye
    return mask

def style_outer_eyes(img):
    """Creates mask for the outer eyes of the QR code."""
    img_size = img.size[0]
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((0, 0, 70, 70), fill=255)  # top left eye
    draw.rectangle((img_size-70, 0, img_size, 70), fill=255)  # top right eye
    draw.rectangle((0, img_size-70, 70, img_size), fill=255)  # bottom left eye
    return mask

@click.command()
@click.argument('url')
@click.option('--logo', '-l', type=click.Path(exists=True), help='Path to the logo image file.')
@click.option('--primary', '-p', default='#0047BA', help='Primary brand color (Hex). Default: Turri Blue (#0047BA)')
@click.option('--secondary', '-s', default='#00CE7C', help='Secondary brand color (Hex). Default: Turri Green (#00CE7C)')
@click.option('--output', '-o', help='Output filename. Defaults to qr_<timestamp>.png')
def generate(url, logo, primary, secondary, output):
    """
    Generate a branded QR code with custom colors and logo.
    
    URL is the link to encode in the QR code.
    """
    try:
        primary_color = hex_to_rgb(primary)
        secondary_color = hex_to_rgb(secondary)
    except ValueError:
        click.echo("Error: Invalid hex color format. Use #RRGGBB.", err=True)
        return

    if not output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output = f"qr_{timestamp}.png"

    click.echo(f"Generating QR for: {url}")
    click.echo(f"Primary Color: {primary} {primary_color}")
    click.echo(f"Secondary Color: {secondary} {secondary_color}")
    if logo:
        click.echo(f"Logo: {logo}")
    click.echo(f"Output: {output}")

    # Generate QR
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=0,
        box_size=10 # Explicitly set to match the hardcoded mask coordinates
    )
    qr.add_data(url)
    qr.make(fit=True) # Ensure it fits

    # Generate layers
    
    # Inner Eyes (Primary Color)
    qr_inner_eyes_img = qr.make_image(
        image_factory=StyledPilImage,
        color_mask=SolidFillColorMask(front_color=primary_color)
    )

    # Outer Eyes (Primary Color, Rounded)
    qr_outer_eyes_img = qr.make_image(
        image_factory=StyledPilImage,
        eye_drawer=RoundedModuleDrawer(radius_ratio=1),
        color_mask=SolidFillColorMask(front_color=primary_color)
    )

    # Main Body (Secondary Color, Rounded, with Logo)
    kwargs = {
        'image_factory': StyledPilImage,
        'module_drawer': RoundedModuleDrawer(),
        'color_mask': SolidFillColorMask(front_color=secondary_color),
    }
    if logo:
        kwargs['embeded_image_path'] = logo

    qr_img = qr.make_image(**kwargs)

    # Convert all to RGB for compositing
    qr_inner_eyes_img = qr_inner_eyes_img.convert('RGB')
    qr_outer_eyes_img = qr_outer_eyes_img.convert('RGB')
    qr_img = qr_img.convert('RGB')

    # Apply Masks and Composite
    # Logic copied from reference:
    # 1. inner_eye_mask keeps the inner eyes from qr_inner_eyes_img
    # 2. But wait, the reference code does:
    # intermediate_img = Image.composite(qr_inner_eyes_img, qr_img, inner_eye_mask)
    # final_image = Image.composite(qr_outer_eyes_img, intermediate_img, outer_eye_mask)
    
    # This implies:
    # - inner_eye_mask defines where we see qr_inner_eyes_img (on top of qr_img)
    # - outer_eye_mask defines where we see qr_outer_eyes_img (on top of intermediate)
    
    inner_eye_mask = style_inner_eyes(qr_img)
    outer_eye_mask = style_outer_eyes(qr_img)
    
    intermediate_img = Image.composite(qr_inner_eyes_img, qr_img, inner_eye_mask)
    final_image = Image.composite(qr_outer_eyes_img, intermediate_img, outer_eye_mask)

    final_image.save(output)
    click.echo(f"✓ QR generated successfully: {output}")

def cli():
    generate()

if __name__ == '__main__':
    cli()
