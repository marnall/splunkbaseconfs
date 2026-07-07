import sys

# Print each path on a separate line
for path in sys.path:
    print(path)

# Or print the entire path as a list
print(sys.path)

sys.path.append('/opt/splunk/lib/python3.7/site-packages')

from PIL import Image, ImageDraw, ImageFont
import math

def add_diagonal_watermark(input_image_path, output_image_path, watermark_text):
    # Open the original image
    base_image = Image.open(input_image_path).convert('RGBA')
    
    # Create a transparent overlay image
    txt = Image.new('RGBA', base_image.size, (255,255,255,0))
    
    # Get a drawing context
    d = ImageDraw.Draw(txt)

    # Calculate the appropriate font size
    diagonal = math.sqrt(base_image.width**2 + base_image.height**2)
    font_size = 1
    font = ImageFont.truetype("arial.ttf", font_size)
    while d.textsize(watermark_text, font)[0] < diagonal:
        font_size += 1
        font = ImageFont.truetype("arial.ttf", font_size)

    # Reduce font size slightly to fit comfortably
    font_size = int(font_size * 0.9)
    font = ImageFont.truetype("arial.ttf", font_size)

    # Get text size
    text_width, text_height = d.textsize(watermark_text, font)

    # Calculate the rotation angle
    angle = math.degrees(math.atan2(base_image.height, base_image.width))

    # Rotate the text layer
    txt = txt.rotate(angle, expand=1)

    # Calculate the position to center the text
    x = (txt.width - text_width) / 2
    y = (txt.height - text_height) / 2

    # Draw the text
    d = ImageDraw.Draw(txt)
    d.text((x, y), watermark_text, font=font, fill=(255,255,255,128))

    # Rotate back and crop
    txt = txt.rotate(-angle, expand=1)
    txt = txt.crop((0, 0, base_image.width, base_image.height))

    # Combine the base image and the text overlay
    watermarked = Image.alpha_composite(base_image, txt)

    # Save the watermarked image
    watermarked.save(output_image_path, 'PNG')

# Usage
input_image = 'testexport2.png'
output_image = 'testexport2.png'
watermark_text = 'Your Watermark Text'

add_diagonal_watermark(input_image, output_image, watermark_text)
