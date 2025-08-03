from PIL import Image, ImageDraw
import io
import base64

def create_pixel_art(pattern, colors, size=20):
    """
    Create a 20x20 pixel art image from a pattern and color palette
    
    Args:
        pattern: List of 400 integers (20x20) representing color indices
        colors: List of RGB tuples for the color palette
        size: Size of each pixel (default 20 for 20x20 grid)
    
    Returns:
        PIL Image object
    """
    img = Image.new('RGB', (size, size))
    pixels = img.load()
    
    for i, color_index in enumerate(pattern):
        x = i % size
        y = i // size
        if color_index < len(colors):
            pixels[x, y] = colors[color_index]
    
    return img

def pattern_to_base64(pattern, colors, scale=12):
    """
    Convert a pixel pattern to base64 encoded PNG for Discord embeds
    
    Args:
        pattern: List of 400 integers representing color indices
        colors: List of RGB tuples for colors
        scale: Scale factor to make image visible (default 12 = 240x240px)
    
    Returns:
        Base64 encoded PNG string
    """
    # Create base 20x20 image
    base_img = create_pixel_art(pattern, colors)
    
    # Scale up for visibility
    scaled_img = base_img.resize((20 * scale, 20 * scale), Image.NEAREST)
    
    # Convert to base64
    buffer = io.BytesIO()
    scaled_img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

def create_sword_pattern():
    """Example sword pattern - 20x20 grid"""
    # 0 = transparent/background, 1 = blade silver, 2 = blade highlight, 3 = hilt, 4 = guard, 5 = pommel
    return [
        0,0,0,0,0,0,0,0,2,2,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,
        0,0,0,4,4,4,4,4,4,4,4,4,4,4,4,0,0,0,0,0,
        0,0,0,0,0,0,0,0,3,3,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,3,3,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,3,3,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,5,5,5,5,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,5,5,5,5,5,5,0,0,0,0,0,0,0,0,
    ]

def create_shield_pattern():
    """Example shield pattern - 20x20 grid"""
    # 0 = transparent, 1 = wood base, 2 = wood highlight, 3 = metal rim, 4 = metal highlight, 5 = center boss
    return [
        0,0,0,0,0,3,3,3,3,3,3,3,3,3,3,0,0,0,0,0,
        0,0,0,3,3,3,4,4,4,4,4,4,4,4,3,3,3,0,0,0,
        0,0,3,3,1,1,2,2,2,2,2,2,2,2,1,1,3,3,0,0,
        0,3,3,1,1,2,2,2,2,2,2,2,2,2,2,1,1,3,3,0,
        0,3,1,1,2,2,2,2,2,2,2,2,2,2,2,2,1,1,3,0,
        3,3,1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,3,3,
        3,4,1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,4,3,
        3,4,2,2,2,2,2,2,5,5,5,5,2,2,2,2,2,2,4,3,
        3,4,2,2,2,2,2,5,5,5,5,5,5,2,2,2,2,2,4,3,
        3,4,2,2,2,2,2,5,5,5,5,5,5,2,2,2,2,2,4,3,
        3,4,2,2,2,2,2,5,5,5,5,5,5,2,2,2,2,2,4,3,
        3,4,2,2,2,2,2,5,5,5,5,5,5,2,2,2,2,2,4,3,
        3,4,2,2,2,2,2,2,5,5,5,5,2,2,2,2,2,2,4,3,
        3,4,1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,4,3,
        0,3,1,1,2,2,2,2,2,2,2,2,2,2,2,2,1,1,3,0,
        0,3,3,1,1,2,2,2,2,2,2,2,2,2,2,1,1,3,3,0,
        0,0,3,3,1,1,2,2,2,2,2,2,2,2,1,1,3,3,0,0,
        0,0,0,3,3,3,1,1,2,2,2,2,1,1,3,3,3,0,0,0,
        0,0,0,0,0,3,3,3,1,1,1,1,3,3,3,0,0,0,0,0,
        0,0,0,0,0,0,0,3,3,3,3,3,3,0,0,0,0,0,0,0,
    ]

def create_ring_pattern():
    """Example ring pattern - 20x20 grid"""
    # 0 = transparent, 1 = gold base, 2 = gold highlight, 3 = gold shadow, 4 = gem, 5 = gem highlight
    return [
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,
        0,0,0,0,1,1,2,2,2,2,2,2,2,2,1,1,0,0,0,0,
        0,0,0,1,1,2,2,2,2,2,2,2,2,2,2,1,1,0,0,0,
        0,0,0,1,2,2,0,0,0,0,0,0,0,0,2,2,1,0,0,0,
        0,0,0,1,2,0,0,0,0,4,4,0,0,0,0,2,1,0,0,0,
        0,0,0,1,2,0,0,0,4,4,5,4,0,0,0,2,1,0,0,0,
        0,0,0,1,2,0,0,0,4,5,4,4,0,0,0,2,1,0,0,0,
        0,0,0,1,2,0,0,0,0,4,4,0,0,0,0,2,1,0,0,0,
        0,0,0,1,2,2,0,0,0,0,0,0,0,0,2,2,1,0,0,0,
        0,0,0,1,1,2,2,2,2,2,2,2,2,2,2,1,1,0,0,0,
        0,0,0,0,1,1,3,3,3,3,3,3,3,3,1,1,0,0,0,0,
        0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    ]

# Color palettes
SWORD_COLORS = [
    (0, 0, 0, 0),      # 0: Transparent
    (169, 169, 169),   # 1: Silver blade
    (220, 220, 220),   # 2: Blade highlight
    (139, 69, 19),     # 3: Brown hilt
    (255, 215, 0),     # 4: Gold guard
    (184, 134, 11),    # 5: Dark gold pommel
]

SHIELD_COLORS = [
    (0, 0, 0, 0),      # 0: Transparent
    (139, 69, 19),     # 1: Brown wood base
    (160, 82, 45),     # 2: Wood highlight
    (105, 105, 105),   # 3: Metal rim
    (169, 169, 169),   # 4: Metal highlight
    (255, 215, 0),     # 5: Gold boss
]

RING_COLORS = [
    (0, 0, 0, 0),      # 0: Transparent
    (255, 215, 0),     # 1: Gold base
    (255, 255, 224),   # 2: Gold highlight
    (184, 134, 11),    # 3: Gold shadow
    (220, 20, 60),     # 4: Red gem
    (255, 182, 193),   # 5: Gem highlight
]

# Example usage
if __name__ == "__main__":
    # Create and save example images
    sword_img = create_pixel_art(create_sword_pattern(), SWORD_COLORS)
    sword_img = sword_img.resize((240, 240), Image.NEAREST)
    sword_img.save("sword_example.png")
    
    shield_img = create_pixel_art(create_shield_pattern(), SHIELD_COLORS)
    shield_img = shield_img.resize((240, 240), Image.NEAREST)
    shield_img.save("shield_example.png")
    
    ring_img = create_pixel_art(create_ring_pattern(), RING_COLORS)
    ring_img = ring_img.resize((240, 240), Image.NEAREST)
    ring_img.save("ring_example.png")