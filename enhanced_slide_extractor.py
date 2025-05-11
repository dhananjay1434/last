import os
import json
import logging
from slide_extractor import SlideExtractor
from content_analyzer import ContentAnalyzer
from syllabus_manager import SyllabusManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_extractor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EnhancedSlideExtractor")

class EnhancedSlideExtractor:
    """
    Enhanced slide extractor with advanced content analysis.

    This class extends the base SlideExtractor with:
    1. Advanced content analysis using NLP
    2. Syllabus mapping and topic organization
    3. Concept extraction and relationship mapping
    """

    def __init__(self, video_url=None, output_dir="slides", syllabus_file=None, **kwargs):
        """
        Initialize the EnhancedSlideExtractor.

        Args:
            video_url: URL of the YouTube video
            output_dir: Directory to save slides
            syllabus_file: Path to syllabus JSON file (optional)
            **kwargs: Additional arguments for SlideExtractor
        """
        # Initialize base extractor
        self.base_extractor = SlideExtractor(
            video_url=video_url,
            output_dir=output_dir,
            **kwargs
        )

        # Initialize content analyzer
        self.content_analyzer = ContentAnalyzer()

        # Initialize syllabus manager
        self.syllabus_manager = SyllabusManager()

        # Load syllabus if provided
        if syllabus_file and os.path.exists(syllabus_file):
            self.syllabus_manager.load_syllabus(syllabus_file)
            self.content_analyzer.syllabus_topics = self.syllabus_manager.topics
            self.content_analyzer.topic_keywords = self.syllabus_manager.topic_keywords

        # Create additional directories
        self.analysis_dir = os.path.join(output_dir, "analysis")
        os.makedirs(self.analysis_dir, exist_ok=True)

        # Store enhanced metadata
        self.enhanced_metadata = {}

        # Initialize additional attributes for advanced features
        self.enable_transcription = False
        self.enable_ocr_enhancement = False
        self.enable_concept_extraction = False
        self.enable_slide_descriptions = False
        self.gemini_api_key = None

        # Initialize services
        self.transcription_service = None
        self.description_generator = None

    def extract_slides(self):
        """
        Extract slides and perform enhanced analysis.

        Returns:
            Boolean indicating success
        """
        # Log the video path before extraction
        if hasattr(self.base_extractor, 'video_path') and self.base_extractor.video_path:
            logger.info(f"Using video path: {self.base_extractor.video_path}")
        else:
            logger.warning("No video path set in base extractor")

        # Extract slides using base extractor
        success = self.base_extractor.extract_slides()

        if not success:
            logger.error("Base slide extraction failed")
            return False

        # Initialize Gemini services if API key is provided
        if self.gemini_api_key:
            # Initialize transcription service if enabled
            if self.enable_transcription:
                try:
                    from gemini_transcription import GeminiTranscriptionService
                    self.transcription_service = GeminiTranscriptionService(api_key=self.gemini_api_key)
                    logger.info("Initialized Gemini transcription service")
                except ImportError:
                    logger.error("Failed to import GeminiTranscriptionService")
                    self.enable_transcription = False

            # Initialize slide description generator if enabled
            if self.enable_slide_descriptions:
                try:
                    from slide_description_generator import SlideDescriptionGenerator
                    self.description_generator = SlideDescriptionGenerator(api_key=self.gemini_api_key)
                    logger.info("Initialized Gemini slide description generator")
                except ImportError:
                    logger.error("Failed to import SlideDescriptionGenerator")
                    self.enable_slide_descriptions = False
        else:
            logger.warning("No Gemini API key provided. Advanced features will be disabled.")
            self.enable_transcription = False
            self.enable_slide_descriptions = False

        # Perform transcription if enabled
        transcription_data = None
        if self.enable_transcription and self.transcription_service:
            try:
                # Get video path from base extractor
                video_path = None

                # Try to get video path from the base extractor's video_path attribute
                if hasattr(self.base_extractor, 'video_path') and self.base_extractor.video_path:
                    video_path = self.base_extractor.video_path
                    logger.info(f"Found video path in base_extractor.video_path: {video_path}")

                # If not found, try to get it from the downloaded_video_path attribute
                elif hasattr(self.base_extractor, 'downloaded_video_path') and self.base_extractor.downloaded_video_path:
                    video_path = self.base_extractor.downloaded_video_path
                    logger.info(f"Found video path in base_extractor.downloaded_video_path: {video_path}")

                # If still not found, check metadata
                if not video_path:
                    for metadata in self.base_extractor.slides_metadata.values():
                        if 'video_path' in metadata:
                            video_path = metadata['video_path']
                            logger.info(f"Found video path in metadata: {video_path}")
                            break

                # Store video path in metadata for all slides
                if video_path:
                    for filename in self.base_extractor.slides_metadata:
                        self.base_extractor.slides_metadata[filename]['video_path'] = video_path
                    logger.info(f"Stored video path in metadata for all slides: {video_path}")

                    # Also store it in the base extractor for future use
                    self.base_extractor.video_path = video_path

                if video_path and os.path.exists(video_path):
                    logger.info(f"Transcribing video: {video_path}")
                    audio_path = self.transcription_service.extract_audio(video_path, self.analysis_dir)
                    if audio_path:
                        logger.info(f"Audio extracted to: {audio_path}")
                        transcription_data = self.transcription_service.transcribe(audio_path)
                        if transcription_data:
                            # Save transcription data with proper encoding for non-English characters
                            transcription_path = os.path.join(self.analysis_dir, "transcription.json")
                            try:
                                with open(transcription_path, 'w', encoding='utf-8') as f:
                                    # Use ensure_ascii=False to properly handle non-English characters
                                    json.dump(transcription_data, f, indent=2, ensure_ascii=False)
                                logger.info(f"Saved transcription to {transcription_path}")
                            except Exception as json_error:
                                logger.error(f"Error saving transcription JSON: {json_error}")
                                # Fallback: Save as plain text if JSON encoding fails
                                try:
                                    text_path = os.path.join(self.analysis_dir, "transcription.txt")
                                    with open(text_path, 'w', encoding='utf-8') as f:
                                        f.write(str(transcription_data))
                                    logger.info(f"Saved transcription as text to {text_path}")
                                except Exception as text_error:
                                    logger.error(f"Error saving transcription as text: {text_error}")
                        else:
                            logger.warning("Transcription service returned no data")
                    else:
                        logger.warning("Failed to extract audio from video")
                else:
                    if video_path:
                        logger.warning(f"Video path exists but file not found: {video_path}")
                    else:
                        logger.warning("No video path found for transcription")
            except Exception as e:
                logger.error(f"Error during transcription: {e}")

        # Analyze extracted slides with transcription data
        self.analyze_slides(transcription_data=transcription_data)

        # Generate slide descriptions if enabled
        if self.enable_slide_descriptions and self.description_generator:
            try:
                logger.info("Generating slide descriptions")
                descriptions = self.description_generator.generate_slide_descriptions(
                    self.enhanced_metadata,
                    transcription_data=transcription_data
                )

                if descriptions:
                    # Save descriptions with proper encoding for non-English characters
                    descriptions_path = os.path.join(self.analysis_dir, "slide_descriptions.json")
                    try:
                        with open(descriptions_path, 'w', encoding='utf-8') as f:
                            # Use ensure_ascii=False to properly handle non-English characters
                            json.dump(descriptions, f, indent=2, ensure_ascii=False)
                        logger.info(f"Saved slide descriptions to {descriptions_path}")
                    except Exception as json_error:
                        logger.error(f"Error saving slide descriptions JSON: {json_error}")
                        # Fallback: Save as plain text if JSON encoding fails
                        try:
                            text_path = os.path.join(self.analysis_dir, "slide_descriptions.txt")
                            with open(text_path, 'w', encoding='utf-8') as f:
                                f.write(str(descriptions))
                            logger.info(f"Saved slide descriptions as text to {text_path}")
                        except Exception as text_error:
                            logger.error(f"Error saving slide descriptions as text: {text_error}")
            except Exception as e:
                logger.error(f"Error generating slide descriptions: {e}")

        # Generate study guide
        self._generate_study_guide()

        return True

    def analyze_slides(self, transcription_data=None):
        """
        Perform advanced content analysis on extracted slides.

        Args:
            transcription_data: Optional transcription data to enhance analysis
        """
        logger.info("Starting enhanced content analysis")

        # Load slide metadata from base extractor
        self.enhanced_metadata = self.base_extractor.slides_metadata.copy()

        # Load transcription data if available
        transcription_path = os.path.join(self.analysis_dir, "transcription.json")
        if transcription_data is None and os.path.exists(transcription_path):
            try:
                with open(transcription_path, 'r', encoding='utf-8') as f:
                    transcription_data = json.load(f)
                logger.info("Loaded transcription data from file")
            except json.JSONDecodeError as json_error:
                logger.error(f"Error decoding transcription JSON: {json_error}")
                # Try to load as text and parse manually if JSON decoding fails
                try:
                    with open(transcription_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()

                    # Create a basic structure with the text content
                    transcription_data = {
                        "text": text_content,
                        "segments": [],
                        "language": "unknown"
                    }
                    logger.info("Created basic transcription structure from text content")
                except Exception as text_error:
                    logger.error(f"Error loading transcription as text: {text_error}")
            except Exception as e:
                logger.error(f"Error loading transcription data: {e}")

        # Process each slide
        for filename, metadata in self.enhanced_metadata.items():
            slide_path = metadata.get('path')

            if not slide_path or not os.path.exists(slide_path):
                continue

            # Get slide content from OCR
            slide_content = metadata.get('content', '')

            # If content is not available in metadata, try to extract it
            if not slide_content and hasattr(self.base_extractor, '_extract_text'):
                try:
                    import cv2
                    from PIL import Image

                    # Load image
                    image = cv2.imread(slide_path)
                    if image is not None:
                        # Extract text
                        slide_content = self.base_extractor._extract_text(image)
                except Exception as e:
                    logger.error(f"Error extracting text from slide {filename}: {e}")

            # Skip slides without content
            if not slide_content:
                logger.warning(f"No content available for slide {filename}")
                continue

            # Get slide timestamp
            timestamp = metadata.get('timestamp', 0)

            # Find relevant transcription for this slide if available
            slide_transcription = ""
            if transcription_data and 'segments' in transcription_data:
                # Convert timestamp to seconds
                from gemini_transcription import convert_timestamp_to_seconds
                timestamp_seconds = convert_timestamp_to_seconds(timestamp)

                # Find segments that overlap with this slide's timestamp
                for segment in transcription_data['segments']:
                    segment_start = convert_timestamp_to_seconds(segment.get('start', 0))
                    segment_end = convert_timestamp_to_seconds(segment.get('end', 0))

                    # Check if segment overlaps with slide timestamp
                    if segment_start <= timestamp_seconds <= segment_end:
                        # Get the text and transliteration (if available)
                        text = segment.get('text', '')
                        transliteration = segment.get('transliteration', '')

                        # Add text and transliteration (if available)
                        if transliteration:
                            slide_transcription += f"{text} ({transliteration}) "
                        else:
                            slide_transcription += text + " "

            # Add transcription to metadata
            if slide_transcription:
                self.enhanced_metadata[filename]['transcription'] = slide_transcription.strip()

            # Combine slide content with transcription for better analysis
            combined_content = slide_content
            if slide_transcription:
                combined_content += f"\n\nTranscription: {slide_transcription}"

            # Analyze content
            analysis_result = self.content_analyzer.analyze_slide_content(
                combined_content,
                slide_type=metadata.get('type')
            )

            # Add transcription info to analysis result
            analysis_result['has_transcription'] = bool(slide_transcription)
            analysis_result['transcription'] = slide_transcription

            # Store analysis results
            self.enhanced_metadata[filename]['content_analysis'] = analysis_result

            logger.info(f"Analyzed slide {filename}: found {len(analysis_result['key_concepts'])} key concepts")

        # Save enhanced metadata
        self._save_enhanced_metadata()

    def _save_enhanced_metadata(self):
        """Save enhanced metadata to a JSON file."""
        metadata_path = os.path.join(self.analysis_dir, "enhanced_metadata.json")

        try:
            # Convert paths to relative paths for portability
            portable_metadata = {}
            for filename, metadata in self.enhanced_metadata.items():
                portable_metadata[filename] = metadata.copy()
                if 'path' in portable_metadata[filename]:
                    portable_metadata[filename]['path'] = os.path.relpath(
                        metadata['path'], self.base_extractor.output_dir
                    )

            with open(metadata_path, 'w', encoding='utf-8') as f:
                # Use ensure_ascii=False to properly handle non-English characters
                json.dump(portable_metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved enhanced metadata to {metadata_path}")
        except Exception as e:
            logger.error(f"Error saving enhanced metadata: {e}")

    def _generate_study_guide(self):
        """Generate a comprehensive study guide from analyzed slides."""
        study_guide_path = os.path.join(self.analysis_dir, "study_guide.md")

        try:
            # Check if we have language information from transcription
            language_info = ""
            transcription_path = os.path.join(self.analysis_dir, "transcription.json")
            if os.path.exists(transcription_path):
                try:
                    with open(transcription_path, 'r', encoding='utf-8') as f:
                        transcription_data = json.load(f)

                    # Add language information if available
                    if 'language' in transcription_data:
                        language = transcription_data['language']
                        # Handle potential non-English characters in language name
                        language_info = f"Content Language: {language}\n\n"

                        # If Hindi content is detected, add a note about transliteration
                        if language.lower() in ['hindi', 'हिंदी']:
                            language_info += "Note: Hindi content is presented in both Hindi script and Roman transliteration.\n\n"
                except json.JSONDecodeError as json_error:
                    logger.error(f"Error decoding transcription JSON: {json_error}")
                    # Try to read as text
                    try:
                        with open(transcription_path, 'r', encoding='utf-8') as f:
                            text_content = f.read()
                        if 'hindi' in text_content.lower() or 'हिंदी' in text_content:
                            language_info = "Content Language: Hindi (with transliteration)\n\n"
                    except Exception as text_error:
                        logger.error(f"Error reading transcription as text: {text_error}")
                except Exception as e:
                    logger.error(f"Error loading transcription data for language info: {e}")

            # Generate study guide
            study_guide = self.content_analyzer.generate_study_guide(
                self.enhanced_metadata,
                output_file=study_guide_path,
                additional_info=language_info
            )

            logger.info(f"Generated study guide at {study_guide_path}")
        except Exception as e:
            logger.error(f"Error generating study guide: {e}")

from collections import defaultdict

def main():
    """Command-line interface for EnhancedSlideExtractor."""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced slide extractor with advanced analysis")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--output", default="slides", help="Output directory for slides")
    parser.add_argument("--syllabus", help="Path to syllabus JSON file")
    parser.add_argument("--pdf", action="store_true", help="Generate PDF after extraction")

    args = parser.parse_args()

    # Create enhanced extractor
    extractor = EnhancedSlideExtractor(
        video_url=args.url,
        output_dir=args.output,
        syllabus_file=args.syllabus,
        # Pass additional options to base extractor
        adaptive_sampling=True,
        extract_content=True,
        organize_slides=True
    )

    # Extract and analyze slides
    if extractor.extract_slides():
        print("Enhanced slide extraction completed successfully!")
        print(f"Analysis results saved in: {extractor.analysis_dir}")

        if args.pdf:
            print("Generating PDF...")
            pdf_path = extractor.base_extractor.convert_slides_to_pdf()
            if pdf_path:
                print(f"PDF created at: {pdf_path}")
            else:
                print("PDF generation failed")
    else:
        print("Slide extraction failed.")

if __name__ == "__main__":
    main()
