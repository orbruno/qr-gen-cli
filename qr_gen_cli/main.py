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

def style_inner_eyes(img, scale, border):
    """Creates mask for the inner eyes of the QR code."""
    img_size = img.size[0]
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Dimensions in pixels
    finder_px = 7 * scale
    border_px = border * scale
    
    # Based on original code logic which used offset 40 (4 modules) for inner eye styling?
    # 4 modules seems to target the bottom-right of the finder if finder is 0-7.
    # Standard inner eye is usually 2-5 (3x3 center). 
    # Let's adjust to standard 3x3 center (2 to 5) if we want "standard" inner eyes, 
    # OR stick to the visual style implied by previous code (4 to 7).
    # Previous output looked good, so let's stick to the implied "4 to 7" style logic 
    # BUT applying the border offset.
    
    # Actually, let's look at the previous 'offset_4'.
    # If the intention is to mask the *Inner Eye* (the dot in the middle), that is typically 3x3 modules.
    # Located at (2,2) to (5,5) relative to finder corner.
    # The previous code used (40,40) to (70,70) which is (4,4) to (7,7).
    # That captures the bottom-right corner of the finder pattern.
    # Let's assume the previous code wanted to mask the *inner* part and maybe 40 was a specific choice.
    # However, to be safe and consistent with standard "Inner Eye" coloring:
    # We should probably target the center 3x3 modules (offset 2).
    # Let's try offset 2 (20px) to 5 (50px).
    # Wait, the prompt says "style_inner_eyes".
    # If I change it now, the look might change. 
    # Let's stick to the previous math structure but add border offsets.
    # Previous: 4 * scale.
    
    inner_offset = 4 * scale # preserving previous style choice
    
    # Top Left
    tl_x1 = inner_offset + border_px
    tl_y1 = inner_offset + border_px
    tl_x2 = finder_px + border_px
    tl_y2 = finder_px + border_px
    draw.rectangle((tl_x1, tl_y1, tl_x2, tl_y2), fill=255)

    # Top Right
    # x starts at: img_size - border_px - finder_px
    # But we want the inner part relative to that corner.
    tr_corner_x = img_size - border_px - finder_px
    tr_corner_y = border_px
    
    # Applying the (4,4) to (7,7) offset relative to the finder corner (0,0)
    # The offset logic above was: from (4,4) to (7,7).
    # So relative x: 4*scale, relative y: 4*scale.
    tr_x1 = tr_corner_x + inner_offset
    tr_y1 = tr_corner_y + inner_offset # wait, previous code had 0? 
    # Previous code: draw.rectangle((img_size-70, 0, img_size, 70), fill=255)
    # That covered the whole top-right finder (0 to 70 y).
    # That seems inconsistent with Top-Left (40 to 70).
    # Let's enforce symmetry for "Inner Eyes".
    
    tr_x2 = tr_corner_x + finder_px
    tr_y2 = tr_corner_y + finder_px
    
    # Use symmetric logic (masking the same relative area)
    draw.rectangle((tr_x1, tr_y1, tr_x2, tr_y2), fill=255)

    # Bottom Left
    bl_corner_x = border_px
    bl_corner_y = img_size - border_px - finder_px
    
    bl_x1 = bl_corner_x + inner_offset
    bl_y1 = bl_corner_y + inner_offset
    bl_x2 = bl_corner_x + finder_px
    bl_y2 = bl_corner_y + finder_px
    
    draw.rectangle((bl_x1, bl_y1, bl_x2, bl_y2), fill=255)
    
    return mask

def style_outer_eyes(img, scale, border):
    """Creates mask for the outer eyes of the QR code."""
    img_size = img.size[0]
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    
    finder_px = 7 * scale
    border_px = border * scale

    # Top Left
    draw.rectangle((border_px, border_px, border_px + finder_px, border_px + finder_px), fill=255)
    
    # Top Right
    tr_x = img_size - border_px - finder_px
    draw.rectangle((tr_x, border_px, tr_x + finder_px, border_px + finder_px), fill=255)
    
    # Bottom Left
    bl_y = img_size - border_px - finder_px
    draw.rectangle((border_px, bl_y, border_px + finder_px, bl_y + finder_px), fill=255)
    
    return mask

@click.command()
@click.argument('url')
@click.option('--logo', '-l', type=click.Path(exists=True), help='Path to the logo image file.')
@click.option('--primary', '-p', default='#0047BA', help='Primary brand color (Hex). Default: Turri Blue (#0047BA)')
@click.option('--secondary', '-s', default='#00CE7C', help='Secondary brand color (Hex). Default: Turri Green (#00CE7C)')
@click.option('--output', '-o', help='Output filename. Defaults to qr_<timestamp>.png')
@click.option('--scale', type=int, default=10, help='Scale (box size) of the QR code. Default: 10')
@click.option('--border', type=int, default=0, help='Border size (in modules). Default: 0 (No border)')
def generate(url, logo, primary, secondary, output, scale, border):
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
    click.echo(f"Border: {border}")
    if logo:
        click.echo(f"Logo: {logo}")
    click.echo(f"Output: {output}")

    # Generate QR
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=border, # Apply border here
        box_size=scale
    )
    qr.add_data(url)
    qr.make(fit=True) 

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

    # Apply Masks and Composite with Border adjustments
    inner_eye_mask = style_inner_eyes(qr_img, scale, border)
    outer_eye_mask = style_outer_eyes(qr_img, scale, border)
    
    intermediate_img = Image.composite(qr_inner_eyes_img, qr_img, inner_eye_mask)
    final_image = Image.composite(qr_outer_eyes_img, intermediate_img, outer_eye_mask)

    final_image.save(output)
    click.echo(f"✓ QR generated successfully: {output}")

def cli():
    generate()

if __name__ == '__main__':
    cli()
