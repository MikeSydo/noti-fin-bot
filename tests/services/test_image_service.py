import unittest
import io
from PIL import Image
from services.image_service import compress_image

class TestImageCompression(unittest.TestCase):
    def test_compress_image_size_reduction(self):
        # Create a large red image
        img = Image.new('RGB', (2000, 2000), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        original_bytes = img_byte_arr.getvalue()
        original_size = len(original_bytes)
        
        # Compress it
        compressed_bytes = compress_image(original_bytes, max_dimension=1000, quality=50)
        compressed_size = len(compressed_bytes)
        
        print(f"Original size: {original_size} bytes")
        print(f"Compressed size: {compressed_size} bytes")
        
        self.assertLess(compressed_size, original_size, "Compressed image should be smaller than original")
        
        # Check dimensions
        comp_img = Image.open(io.BytesIO(compressed_bytes))
        self.assertLessEqual(max(comp_img.size), 1000, "Maximum dimension should be 1000px")
        self.assertEqual(comp_img.mode, "RGB", "Image should remain in RGB mode (color)")

    def test_compress_small_image(self):
        # Create a small image (100x100)
        img = Image.new('RGB', (100, 100), color='blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        original_bytes = img_byte_arr.getvalue()
        
        # Compress it
        compressed_bytes = compress_image(original_bytes, max_dimension=1600, quality=85)
        
        # Small images should not be resized up
        comp_img = Image.open(io.BytesIO(compressed_bytes))
        self.assertEqual(comp_img.size, (100, 100))

if __name__ == '__main__':
    unittest.main()
