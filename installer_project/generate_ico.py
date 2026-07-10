from PIL import Image, ImageDraw
import os

ico_path = os.path.join(os.path.dirname(__file__), "app_icons.ico")
if not os.path.exists(ico_path):
    # Generate simple movie camera glyph as a placeholder icon
    img = Image.new('RGBA', (256, 256), color=(13, 13, 18, 255))
    draw = ImageDraw.Draw(img)
    # Circle gradient
    draw.ellipse([32, 32, 224, 224], fill=(203, 166, 247, 255))
    # Triangle glyph inside
    draw.polygon([(96, 80), (96, 176), (176, 128)], fill=(13, 13, 18, 255))
    img.save(ico_path, format='ICO')
    print("✓ Placeholder app_icons.ico file generated successfully.")
