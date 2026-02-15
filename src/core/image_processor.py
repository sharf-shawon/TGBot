"""Image processing utilities for the Telegram bot."""

import io

import cv2
import numpy as np
from PIL import Image


def remove_background(image_bytes: bytes) -> bytes:
    """Remove background from image using color-based segmentation.
    
    Uses OpenCV to detect and remove background based on color similarity.
    Works by creating an alpha channel mask based on color range detection.
    
    Args:
        image_bytes: Image data in bytes
        
    Returns:
        Image bytes with background removed (PNG format with transparency)
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Failed to decode image")
    
    # Convert BGR to HSV for better color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define range for background (typically lighter colors)
    # Adjust these values for different backgrounds
    lower_bg = np.array([0, 0, 100])
    upper_bg = np.array([180, 100, 255])
    
    # Create mask for background
    mask = cv2.inRange(hsv, lower_bg, upper_bg)
    
    # Apply morphological operations to clean up mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Invert mask (we want foreground, not background)
    mask = cv2.bitwise_not(mask)
    
    # Convert to RGBA
    img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
    
    # Apply mask to create alpha channel
    img_rgba[:, :, 3] = mask
    
    # Convert to PIL and save
    pil_image = Image.fromarray(cv2.cvtColor(img_rgba, cv2.COLOR_BGRA2RGBA))
    
    output_bytes = io.BytesIO()
    pil_image.save(output_bytes, format="PNG")
    output_bytes.seek(0)
    
    return output_bytes.getvalue()


def convert_to_webp(image_bytes: bytes, quality: int = 80) -> bytes:
    """Convert image to WebP format.
    
    Args:
        image_bytes: Image data in bytes
        quality: WebP quality (1-100, default 80)
        
    Returns:
        Image bytes in WebP format
    """
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert RGBA to RGB if necessary
    if image.mode in ["RGBA", "LA", "P"]:
        rgb_image = Image.new("RGB", image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        image = rgb_image
    
    output_bytes = io.BytesIO()
    image.save(output_bytes, format="WEBP", quality=quality)
    output_bytes.seek(0)
    
    return output_bytes.getvalue()


def optimize_image(image_bytes: bytes, quality: int = 85, max_size: tuple = None) -> bytes:
    """Optimize image by reducing quality and optionally resizing.
    
    Args:
        image_bytes: Image data in bytes
        quality: JPEG quality (1-100, default 85)
        max_size: Maximum (width, height) to resize to, default (2000, 2000)
        
    Returns:
        Optimized image bytes
    """
    if max_size is None:
        max_size = (2000, 2000)
    
    image = Image.open(io.BytesIO(image_bytes))
    
    # Resize if necessary
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Convert to RGB if necessary
    if image.mode in ["RGBA", "LA", "P"]:
        rgb_image = Image.new("RGB", image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        image = rgb_image
    
    output_bytes = io.BytesIO()
    image.save(output_bytes, format="JPEG", quality=quality, optimize=True)
    output_bytes.seek(0)
    
    return output_bytes.getvalue()


def convert_to_png(image_bytes: bytes) -> bytes:
    """Convert image to PNG format.
    
    Args:
        image_bytes: Image data in bytes
        
    Returns:
        Image bytes in PNG format
    """
    image = Image.open(io.BytesIO(image_bytes))
    
    output_bytes = io.BytesIO()
    image.save(output_bytes, format="PNG")
    output_bytes.seek(0)
    
    return output_bytes.getvalue()


def convert_to_jpeg(image_bytes: bytes, quality: int = 95) -> bytes:
    """Convert image to JPEG format.
    
    Args:
        image_bytes: Image data in bytes
        quality: JPEG quality (1-100, default 95)
        
    Returns:
        Image bytes in JPEG format
    """
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert to RGB if necessary
    if image.mode in ["RGBA", "LA", "P"]:
        rgb_image = Image.new("RGB", image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        image = rgb_image
    
    output_bytes = io.BytesIO()
    image.save(output_bytes, format="JPEG", quality=quality)
    output_bytes.seek(0)
    
    return output_bytes.getvalue()


def resize_image(image_bytes: bytes, width: int, height: int) -> bytes:
    """Resize image to specific dimensions.
    
    Args:
        image_bytes: Image data in bytes
        width: Target width in pixels
        height: Target height in pixels
        
    Returns:
        Resized image bytes
    """
    image = Image.open(io.BytesIO(image_bytes))
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    
    output_bytes = io.BytesIO()
    # Preserve original format or use PNG
    fmt = image.format or "PNG"
    resized.save(output_bytes, format=fmt)
    output_bytes.seek(0)
    
    return output_bytes.getvalue()


def get_image_info(image_bytes: bytes) -> dict:
    """Get information about an image.
    
    Args:
        image_bytes: Image data in bytes
        
    Returns:
        Dictionary with image information
    """
    image = Image.open(io.BytesIO(image_bytes))
    
    return {
        "format": image.format,
        "size": image.size,
        "mode": image.mode,
        "width": image.width,
        "height": image.height,
        "bytes": len(image_bytes),
    }
