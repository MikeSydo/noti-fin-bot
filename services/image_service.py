import io
import logging
from PIL import Image, ImageOps, ImageEnhance

logger = logging.getLogger(__name__)

def compress_image(file_bytes: bytes, max_dimension: int = 1600, quality: int = 75) -> bytes:
    """
    Compresses an image from bytes, limiting the maximum dimension and quality.
    Supports JPG, PNG, WebP. Returns compressed JPEG bytes.
    If compressed version is larger than original, returns original bytes.
    """
    try:
        old_size = len(file_bytes)
        # Load image from bytes
        img = Image.open(io.BytesIO(file_bytes))
        
        # Auto-rotate based on EXIF metadata
        img = ImageOps.exif_transpose(img)
        
        # Enhance contrast (slightly) to help OCR
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2) # 20% increase in contrast
        
        # Convert to RGB if it's RGBA or other (stripping alpha for JPEG)
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        # Get original dimensions
        width, height = img.size
        
        # Calculate new dimensions if necessary
        is_resized = False
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            is_resized = True

        # Save to bytes with optimization
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        
        compressed_bytes = output.getvalue()
        new_size = len(compressed_bytes)
        
        # If compressed version is larger than original and we didn't resize, keep original
        # If we resized, we usually want the resized version even if slightly larger (unlikely)
        # but to be safe, if it's larger, we just don't touch it.
        if new_size >= old_size:
            logger.info(f"Compression skipped: new size {new_size/1024:.1f}KB >= old size {old_size/1024:.1f}KB")
            return file_bytes
            
        reduction = (1 - (new_size / old_size)) * 100
        logger.info(f"Image compressed: {old_size/1024:.1f}KB -> {new_size/1024:.1f}KB ({reduction:.1f}% reduction, resized: {is_resized})")
        
        return compressed_bytes

    except Exception as e:
        logger.error(f"Failed to compress image: {e}")
        # Return original bytes if compression fails to avoid breaking the flow
        return file_bytes
