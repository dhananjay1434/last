import os
import logging
import json
import re
import cv2
import pytesseract
from PIL import Image
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ocr_enhancer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OCRContextEnhancer")

class OCRContextEnhancer:
    """
    Enhances OCR results by combining multiple approaches and integrating with transcription.
    
    This class provides methods for:
    1. Improved OCR with multiple preprocessing techniques
    2. Integration with transcription data for better context
    3. Validation and correction of OCR results
    4. Context-aware text extraction
    """
    
    def __init__(self, tesseract_config=None, transcription_service=None):
        """
        Initialize the OCR Context Enhancer.
        
        Args:
            tesseract_config: Configuration for Tesseract OCR
            transcription_service: Optional GeminiTranscriptionService instance
        """
        self.tesseract_config = tesseract_config or {
            'standard': '--psm 6 --oem 3',
            'dense': '--psm 3 --oem 3',
            'sparse': '--psm 1 --oem 3',
            'title': '--psm 7 --oem 3'
        }
        self.transcription_service = transcription_service
        self.ocr_cache = {}
        
        # Common words for validation
        self.common_words = {
            'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'not',
            'are', 'was', 'were', 'will', 'would', 'should', 'could', 'can',
            'may', 'might', 'must', 'shall', 'should', 'who', 'what', 'where',
            'when', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'than', 'too', 'very', 'one', 'two',
            'three', 'four', 'five', 'first', 'last', 'next', 'example', 'note',
            'definition', 'theorem', 'equation', 'function', 'variable', 'value',
            'data', 'result', 'analysis', 'figure', 'table', 'chart', 'graph',
            'slide', 'page', 'chapter', 'section', 'part', 'introduction', 'conclusion'
        }
        
        # Educational patterns
        self.educational_patterns = [
            r'fig(ure)?\.?\s*\d+',
            r'eq(uation)?\.?\s*\d+',
            r'table\s*\d+',
            r'chapter\s*\d+',
            r'section\s*\d+',
            r'theorem\s*\d+',
            r'definition\s*\d+',
            r'example\s*\d+',
            r'algorithm\s*\d+'
        ]
        
    def enhance_ocr(self, image, timestamp=None, transcription_data=None):
        """
        Enhance OCR results using multiple techniques and transcription data.
        
        Args:
            image: Input image (numpy array or PIL Image)
            timestamp: Optional timestamp for finding relevant transcription
            transcription_data: Optional transcription data
            
        Returns:
            Dictionary with enhanced OCR results
        """
        # Convert image to numpy array if it's a PIL Image
        if isinstance(image, Image.Image):
            image = np.array(image)
            
        # Compute image hash for caching
        image_hash = self._compute_image_hash(image)
        
        # Check cache
        if image_hash in self.ocr_cache:
            return self.ocr_cache[image_hash]
            
        # Apply multiple preprocessing techniques
        preprocessed_images = self._preprocess_image(image)
        
        # Extract text using multiple OCR configurations
        ocr_results = {}
        for name, img in preprocessed_images.items():
            for config_name, config in self.tesseract_config.items():
                key = f"{name}_{config_name}"
                try:
                    pil_img = Image.fromarray(img)
                    text = pytesseract.image_to_string(pil_img, config=config)
                    ocr_results[key] = text.strip()
                except Exception as e:
                    logger.error(f"OCR error with {key}: {e}")
                    ocr_results[key] = ""
        
        # Evaluate and select the best OCR result
        best_result, quality_score = self._select_best_ocr_result(ocr_results)
        
        # Get transcription context if available
        transcription_text = ""
        if transcription_data and timestamp is not None:
            transcription_text = self._get_transcription_context(transcription_data, timestamp)
        
        # Combine OCR and transcription
        combined_text = best_result
        if transcription_text:
            combined_text = f"{best_result}\n\nTranscription: {transcription_text}"
        
        # Create result dictionary
        result = {
            'text': best_result,
            'combined_text': combined_text,
            'quality': quality_score,
            'has_transcription': bool(transcription_text),
            'transcription': transcription_text
        }
        
        # Cache the result
        self.ocr_cache[image_hash] = result
        
        return result
    
    def _preprocess_image(self, image):
        """
        Apply multiple preprocessing techniques to improve OCR.
        
        Args:
            image: Input image (numpy array)
            
        Returns:
            Dictionary of preprocessed images
        """
        results = {'original': image}
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            results['gray'] = gray
            
            # Apply adaptive thresholding
            adaptive_threshold = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            results['adaptive'] = adaptive_threshold
            
            # Apply Otsu's thresholding
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            results['otsu'] = otsu
            
            # Apply bilateral filter for noise reduction while preserving edges
            bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
            results['bilateral'] = bilateral
            
            # Apply unsharp masking for sharpening
            gaussian = cv2.GaussianBlur(gray, (0, 0), 3)
            unsharp = cv2.addWeighted(gray, 1.5, gaussian, -0.5, 0)
            results['unsharp'] = unsharp
            
        except Exception as e:
            logger.error(f"Error in image preprocessing: {e}")
            
        return results
    
    def _select_best_ocr_result(self, ocr_results):
        """
        Select the best OCR result from multiple attempts.
        
        Args:
            ocr_results: Dictionary of OCR results
            
        Returns:
            Tuple of (best_text, quality_score)
        """
        best_text = ""
        best_score = 0
        
        for key, text in ocr_results.items():
            if not text:
                continue
                
            # Calculate quality score
            score = self._calculate_text_quality(text)
            
            if score > best_score:
                best_score = score
                best_text = text
        
        # If all results are empty or poor quality, use the original OCR
        if not best_text and 'original_standard' in ocr_results:
            best_text = ocr_results['original_standard']
            
        return best_text, best_score
    
    def _calculate_text_quality(self, text):
        """
        Calculate a quality score for OCR text.
        
        Args:
            text: OCR text to evaluate
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        if not text:
            return 0.0
            
        # Split into words
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        
        if not words:
            return 0.0
            
        # Count valid words
        valid_words = sum(1 for word in words if word in self.common_words)
        
        # Check for educational patterns
        pattern_matches = 0
        for pattern in self.educational_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                pattern_matches += 1
        
        # Calculate base score from valid word ratio
        base_score = valid_words / max(1, len(words))
        
        # Boost score for educational patterns
        pattern_boost = min(0.3, 0.1 * pattern_matches)
        
        # Boost score for longer text (more likely to be meaningful)
        length_boost = min(0.2, 0.01 * len(words))
        
        return min(1.0, base_score + pattern_boost + length_boost)
    
    def _get_transcription_context(self, transcription_data, timestamp):
        """
        Get relevant transcription context for a given timestamp.
        
        Args:
            transcription_data: Transcription data dictionary
            timestamp: Timestamp in seconds
            
        Returns:
            Relevant transcription text
        """
        if not transcription_data or 'segments' not in transcription_data:
            return ""
            
        segments = transcription_data.get('segments', [])
        relevant_text = []
        
        # Find segments that overlap with the timestamp
        for segment in segments:
            start = self._convert_to_seconds(segment.get('start', 0))
            end = self._convert_to_seconds(segment.get('end', 0))
            
            # Use a window around the timestamp (5 seconds before and after)
            if start - 5 <= timestamp <= end + 5:
                relevant_text.append(segment.get('text', ''))
        
        return " ".join(relevant_text)
    
    def _convert_to_seconds(self, timestamp):
        """Convert timestamp to seconds."""
        if isinstance(timestamp, (int, float)):
            return float(timestamp)
        
        if isinstance(timestamp, str):
            # Try to parse time format
            if ':' in timestamp:
                parts = timestamp.split(':')
                if len(parts) == 2:  # MM:SS
                    return int(parts[0]) * 60 + float(parts[1])
                elif len(parts) == 3:  # HH:MM:SS
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            
            # Try direct conversion
            try:
                return float(timestamp)
            except ValueError:
                pass
        
        return 0.0
    
    def _compute_image_hash(self, image):
        """Compute a simple hash for an image for caching purposes."""
        try:
            # Resize to small dimensions for faster hashing
            small = cv2.resize(image, (32, 32))
            # Convert to grayscale
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small
            # Compute mean hash
            avg = gray.mean()
            hash_value = ''.join('1' if v > avg else '0' for v in gray.flatten())
            return hash_value
        except Exception as e:
            logger.error(f"Error computing image hash: {e}")
            # Fallback to a timestamp-based hash
            return str(hash(image.tobytes()))
