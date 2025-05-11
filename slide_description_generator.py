import os
import json
import logging
import re
import sys
import importlib.util

# Try to import Google Generative AI
try:
    # Try different import methods for Google Generative AI
    try:
        import google.generativeai as genai
        GENAI_AVAILABLE = True
        logging.info("Successfully imported Google Generative AI using standard import")
    except ImportError:
        # Try alternative import method

        # Try to find the google.generativeai package
        spec = importlib.util.find_spec("google.generativeai")
        if spec is not None:
            # If found, try to import it directly
            genai_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(genai_module)
            genai = genai_module
            GENAI_AVAILABLE = True
            logging.info("Successfully imported Google Generative AI using importlib")
        else:
            raise ImportError("Could not find google.generativeai package")
except Exception as e:
    logging.warning(f"Google Generative AI not available. Slide description generation will be disabled. Error: {str(e)}")

    # Try to get more information about the google-generativeai package
    try:
        import pkg_resources
        try:
            dist = pkg_resources.get_distribution("google-generativeai")
            logging.info(f"Google Generative AI package found: {dist}")
            logging.info(f"Google Generative AI location: {dist.location}")
        except pkg_resources.DistributionNotFound:
            logging.warning("Google Generative AI package not found using pkg_resources")
    except Exception as diagnostic_error:
        logging.warning(f"Error during diagnostics: {str(diagnostic_error)}")

    GENAI_AVAILABLE = False

# Define timestamp conversion utility
def convert_timestamp_to_seconds(timestamp):
    """Convert various timestamp formats to seconds

    Args:
        timestamp: A timestamp in various formats (string, int, float)

    Returns:
        Float value in seconds
    """
    if timestamp is None:
        return 0.0

    # If already a number, return it
    if isinstance(timestamp, (int, float)):
        return float(timestamp)

    # If it's a string, try to convert
    if isinstance(timestamp, str):
        # Remove any whitespace
        timestamp = timestamp.strip()

        # Try direct conversion to float first
        try:
            return float(timestamp)
        except ValueError:
            pass

        # Try HH:MM:SS format
        time_pattern = r'(\d+):(\d+):(\d+)(?:\.(\d+))?'
        match = re.match(time_pattern, timestamp)
        if match:
            hours, minutes, seconds, ms = match.groups()
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            if ms:
                total_seconds += float(f"0.{ms}")
            return float(total_seconds)

        # Try MM:SS format
        time_pattern = r'(\d+):(\d+)(?:\.(\d+))?'
        match = re.match(time_pattern, timestamp)
        if match:
            minutes, seconds, ms = match.groups()
            total_seconds = int(minutes) * 60 + int(seconds)
            if ms:
                total_seconds += float(f"0.{ms}")
            return float(total_seconds)

        # Try extracting any numbers as a last resort
        numbers = re.findall(r'\d+\.?\d*', timestamp)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass

    # If all else fails, return 0
    logging.warning(f"Could not parse timestamp: {timestamp}, using 0 instead")
    return 0.0

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("slide_description.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SlideDescriptionGenerator")

class SlideDescriptionGenerator:
    """Generate concise descriptions for slides using Google's Gemini API"""

    def __init__(self, api_key=None):
        """Initialize the description generator with the specified API key"""
        self.api_key = api_key
        self.client = None

    def initialize(self, api_key=None):
        """Initialize the Gemini client with API key"""
        if not GENAI_AVAILABLE:
            logger.error("Cannot initialize: Google Generative AI is not available")
            return False

        try:
            if api_key:
                self.api_key = api_key

            if not self.api_key:
                logger.error("No API key provided for Gemini")
                return False

            logger.info("Initializing Gemini client")

            # Try different ways to create the client
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Created Gemini client using standard method")
            except AttributeError:
                # If genai is not a module with Client attribute, try to access it differently
                if hasattr(genai, 'generativeai') and hasattr(genai.generativeai, 'Client'):
                    self.client = genai.generativeai.Client(api_key=self.api_key)
                    logger.info("Created Gemini client using nested attribute")
                else:
                    # Last resort: try to import directly
                    import google.generativeai
                    google.generativeai.configure(api_key=self.api_key)
                    self.client = google.generativeai
                    logger.info("Created Gemini client using direct import")

            return True
        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")
            return False

    def generate_slide_descriptions(self, slides_metadata, transcription_data=None, callback=None):
        """Generate concise descriptions for each slide using Gemini API

        Args:
            slides_metadata: Dictionary of slide metadata
            transcription_data: Optional transcription data
            callback: Optional callback function for status updates

        Returns:
            Dictionary of slide descriptions
        """
        if self.client is None and not self.initialize():
            logger.error("Gemini client not initialized")
            return None

        try:
            total_slides = len(slides_metadata)
            processed = 0
            descriptions = {}

            # Process each slide
            for filename, metadata in slides_metadata.items():
                # Update status periodically
                processed += 1
                if callback and (processed % 5 == 0 or processed == total_slides):
                    callback(f"Generating description for slide {processed}/{total_slides}...")

                # Get slide content
                slide_content = metadata.get('content', '')
                if not slide_content:
                    continue

                # Get slide timestamp and convert to seconds
                timestamp = convert_timestamp_to_seconds(metadata.get('timestamp', 0))

                # Find relevant transcription for this slide
                slide_transcription = ""
                context_transcription = ""

                if transcription_data and 'segments' in transcription_data:

                    # Find direct transcription for this slide
                    direct_segments = []
                    context_segments = []

                    for segment in transcription_data['segments']:
                        # Convert segment timestamps to seconds
                        start = convert_timestamp_to_seconds(segment.get('start', 0))
                        end = convert_timestamp_to_seconds(segment.get('end', 0))

                        # Check if segment directly overlaps with slide timestamp
                        if start <= timestamp and end >= timestamp:
                            direct_segments.append(segment)
                        # Also collect nearby segments for context (5 seconds before and after)
                        elif (timestamp - 5 <= end and end <= timestamp) or (timestamp <= start and start <= timestamp + 5):
                            context_segments.append(segment)

                    # Sort segments by start time
                    direct_segments.sort(key=lambda x: x.get('start', 0))
                    context_segments.sort(key=lambda x: x.get('start', 0))

                    # Combine direct segments
                    for segment in direct_segments:
                        slide_transcription += segment.get('text', '') + " "

                    # Combine context segments
                    for segment in context_segments:
                        context_transcription += segment.get('text', '') + " "

                # Combine slide content and transcription
                combined_content = slide_content

                if slide_transcription:
                    combined_content += f"\n\nTranscription: {slide_transcription}"

                if context_transcription:
                    combined_content += f"\n\nContext: {context_transcription}"

                # Generate description using Gemini
                try:
                    prompt = f"""
                    You are an expert educational content analyzer specializing in extracting meaningful information from lecture slides and transcriptions. Your task is to analyze the following slide content and transcription, then provide a structured analysis.

                    IMPORTANT CONTEXT:
                    - This is from an educational lecture slide
                    - The content may include text that was poorly extracted by OCR
                    - If the content appears to be gibberish or unclear, focus on any recognizable patterns, formulas, or diagrams that might be present
                    - The transcription (if available) provides spoken context for the slide

                    ANALYSIS INSTRUCTIONS:
                    1. First, determine if the slide content is readable or mostly gibberish
                    2. If readable, extract the key information
                    3. If mostly unreadable, focus on any recognizable patterns, mathematical symbols, or diagrams
                    4. Use the transcription to provide context for unclear content
                    5. For mathematical content, pay special attention to equations, variables, and formulas

                    PROVIDE THE FOLLOWING:
                    1. A concise title (max 10 words) that clearly identifies the main topic
                    2. A brief description (max 50 words) summarizing the key points
                    3. Main topic and subtopics (comma-separated list)
                    4. Key concepts covered (comma-separated list)
                    5. Important formulas or definitions (if any)
                    6. Complexity level (Basic, Intermediate, Advanced)

                    Format the response as JSON with these fields:
                    {{
                      "title": "Concise title",
                      "description": "Brief description",
                      "topics": ["Main topic 1", "Main topic 2"],
                      "subtopics": ["Subtopic 1", "Subtopic 2"],
                      "key_concepts": ["Concept 1", "Concept 2"],
                      "formulas": ["Formula 1", "Formula 2"],
                      "complexity": "Basic/Intermediate/Advanced"
                    }}

                    IMPORTANT:
                    - If the content appears to be mathematical, focus on extracting any equations or formulas
                    - If the content appears to be code, preserve the syntax and structure
                    - If the content is mostly unreadable, use the transcription to infer the topic
                    - Always return valid JSON format
                    - If you're unsure about the content, make your best educated guess based on context

                    Slide Content:
                    {combined_content}
                    """

                    # Handle different client structures
                    if hasattr(self.client, 'models') and hasattr(self.client.models, 'generate_content'):
                        # New Gemini API structure
                        response = self.client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=prompt
                        )
                        response_text = response.text
                    elif hasattr(self.client, 'generate_content'):
                        # Old Gemini API structure
                        response = self.client.generate_content(prompt)
                        response_text = response.text
                    else:
                        # Direct import structure
                        model = self.client.GenerativeModel('gemini-2.0-flash')
                        response = model.generate_content(prompt)
                        response_text = response.text

                    # Process the response
                    try:
                        # First try to parse as JSON directly
                        result = json.loads(response_text)
                    except json.JSONDecodeError:
                        # If not valid JSON, try to extract JSON from the text
                        try:
                            # Look for JSON-like content between triple backticks
                            import re
                            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                            if json_match:
                                result = json.loads(json_match.group(1))
                            else:
                                # Create a simple structure with the raw text
                                result = {
                                    "title": "Slide " + filename,
                                    "description": response_text[:100] + "...",
                                    "topics": [],
                                    "subtopics": [],
                                    "key_concepts": [],
                                    "complexity": "Intermediate"
                                }
                        except Exception as e:
                            logger.error(f"Error parsing response for slide {filename}: {e}")
                            result = {
                                "title": "Slide " + filename,
                                "description": "Could not generate description",
                                "topics": [],
                                "subtopics": [],
                                "key_concepts": [],
                                "complexity": "Intermediate"
                            }

                    # Add timestamp and filename to result
                    result["timestamp"] = timestamp
                    result["filename"] = filename

                    # Store the description
                    descriptions[filename] = result

                except Exception as e:
                    logger.error(f"Error generating description for slide {filename}: {e}")
                    descriptions[filename] = {
                        "title": "Slide " + filename,
                        "description": "Error generating description",
                        "topics": [],
                        "subtopics": [],
                        "key_concepts": [],
                        "complexity": "Intermediate",
                        "timestamp": timestamp,
                        "filename": filename
                    }

            return descriptions

        except Exception as e:
            logger.error(f"Error generating slide descriptions: {e}")
            return None

    def create_topic_index(self, descriptions):
        """Create a searchable index of topics from slide descriptions

        Args:
            descriptions: Dictionary of slide descriptions

        Returns:
            Dictionary mapping topics to slides
        """
        topic_index = {}

        for filename, desc in descriptions.items():
            # Process main topics
            topics = desc.get('topics', [])
            if isinstance(topics, str):
                topics = [t.strip() for t in topics.split(',')]

            for topic in topics:
                if topic not in topic_index:
                    topic_index[topic] = []
                topic_index[topic].append(filename)

            # Process subtopics
            subtopics = desc.get('subtopics', [])
            if isinstance(subtopics, str):
                subtopics = [t.strip() for t in subtopics.split(',')]

            for subtopic in subtopics:
                if subtopic not in topic_index:
                    topic_index[subtopic] = []
                topic_index[subtopic].append(filename)

        return topic_index

    def generate_content_summary(self, descriptions, transcription_data=None):
        """Generate a summary of the entire content

        Args:
            descriptions: Dictionary of slide descriptions
            transcription_data: Optional transcription data

        Returns:
            Dictionary with content summary
        """
        if self.client is None and not self.initialize():
            logger.error("Gemini client not initialized")
            return None

        try:
            # Create a summary of all topics
            all_topics = set()
            all_subtopics = set()

            for desc in descriptions.values():
                topics = desc.get('topics', [])
                if isinstance(topics, str):
                    topics = [t.strip() for t in topics.split(',')]
                all_topics.update(topics)

                subtopics = desc.get('subtopics', [])
                if isinstance(subtopics, str):
                    subtopics = [t.strip() for t in subtopics.split(',')]
                all_subtopics.update(subtopics)

            # Get full transcription text if available
            full_transcript = ""
            if transcription_data and 'text' in transcription_data:
                full_transcript = transcription_data['text']

            # Generate content summary using Gemini
            prompt = f"""
            Based on the following information, generate a comprehensive summary of the educational content:

            Main Topics: {', '.join(all_topics)}
            Subtopics: {', '.join(all_subtopics)}

            Full Transcript:
            {full_transcript[:2000]}... [truncated]

            Provide:
            1. A title for the overall content
            2. A summary of the main topics covered
            3. Learning objectives
            4. Recommended prerequisites
            5. Estimated difficulty level

            Format the response as JSON with these fields: title, summary, learning_objectives, prerequisites, difficulty
            """

            # Handle different client structures
            if hasattr(self.client, 'models') and hasattr(self.client.models, 'generate_content'):
                # New Gemini API structure
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                response_text = response.text
            elif hasattr(self.client, 'generate_content'):
                # Old Gemini API structure
                response = self.client.generate_content(prompt)
                response_text = response.text
            else:
                # Direct import structure
                model = self.client.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(prompt)
                response_text = response.text

            # Process the response
            try:
                # First try to parse as JSON directly
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # If not valid JSON, try to extract JSON from the text
                try:
                    # Look for JSON-like content between triple backticks
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(1))
                    else:
                        # Create a simple structure with the raw text
                        result = {
                            "title": "Content Summary",
                            "summary": response_text[:500] + "...",
                            "learning_objectives": [],
                            "prerequisites": [],
                            "difficulty": "Intermediate"
                        }
                except Exception as e:
                    logger.error(f"Error parsing content summary response: {e}")
                    result = {
                        "title": "Content Summary",
                        "summary": "Could not generate summary",
                        "learning_objectives": [],
                        "prerequisites": [],
                        "difficulty": "Intermediate"
                    }

            return result

        except Exception as e:
            logger.error(f"Error generating content summary: {e}")
            return None
