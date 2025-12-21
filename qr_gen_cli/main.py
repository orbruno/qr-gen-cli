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

def style_inner_eyes(img, scale):
    """Creates mask for the inner eyes of the QR code."""
    img_size = img.size[0]
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    
    # 7 modules * scale
    finder_size = 7 * scale
    # 4 modules * scale (offset used in original code)
    offset_4 = 4 * scale

    # Original: (40, 40, 70, 70) for box_size=10
    draw.rectangle((offset_4, offset_4, finder_size, finder_size), fill=255)  # top left eye
    
    # Original: (img_size-70, 0, img_size, 70)
    draw.rectangle((img_size-finder_size, 0, img_size, finder_size), fill=255)  # top right eye
    
    # Original: (1, img_size-70, 70, img_size-70) - Keeping logic but suspicious
    # This likely was meant to be the bottom left eye but has a typo in the original code (y2=y1).
    # Since we are preserving logic, we scale the coordinates. 
    # But 1 pixel is likely just 1 pixel or scale/10. Let's stick to 1 to minimize diff.
    draw.rectangle((1, img_size-finder_size, finder_size, img_size-finder_size), fill=255)  # bottom left eye
    return mask

def style_outer_eyes(img, scale):
    """Creates mask for the outer eyes of the QR code."""
    img_size = img.size[0]
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    
    finder_size = 7 * scale

    # Original: (0, 0, 70, 70)
    draw.rectangle((0, 0, finder_size, finder_size), fill=255)  # top left eye
    
    # Original: (img_size-70, 0, img_size, 70)
    draw.rectangle((img_size-finder_size, 0, img_size, finder_size), fill=255)  # top right eye
    
    # Original: (0, img_size-70, 70, img_size)
    draw.rectangle((0, img_size-finder_size, finder_size, img_size), fill=255)  # bottom left eye
    return mask

@click.command()
@click.argument('url')
@click.option('--logo', '-l', type=click.Path(exists=True), help='Path to the logo image file.')
@click.option('--primary', '-p', default='#0047BA', help='Primary brand color (Hex). Default: Turri Blue (#0047BA)')
@click.option('--secondary', '-s', default='#00CE7C', help='Secondary brand color (Hex). Default: Turri Green (#00CE7C)')
@click.option('--output', '-o', help='Output filename. Defaults to qr_<timestamp>.png')
@click.option('--scale', type=int, default=10, help='Scale (box size) of the QR code. Default: 10')
def generate(url, logo, primary, secondary, output, scale):
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
    click.echo(f"Scale: {scale}")
    if logo:
        click.echo(f"Logo: {logo}")
    click.echo(f"Output: {output}")

    # Generate QR
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=0,
        box_size=scale # Dynamic box size
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
    inner_eye_mask = style_inner_eyes(qr_img, scale)
    outer_eye_mask = style_outer_eyes(qr_img, scale)
    
    intermediate_img = Image.composite(qr_inner_eyes_img, qr_img, inner_eye_mask)
    final_image = Image.composite(qr_outer_eyes_img, intermediate_img, outer_eye_mask)

    final_image.save(output)
    click.echo(f"✓ QR generated successfully: {output}")

def cli():
    generate()

if __name__ == '__main__':
    cli()