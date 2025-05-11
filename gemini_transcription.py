import os
import json
import logging
import tempfile
import re
import sys
import time
import subprocess

# Import audio-extract library
try:
    from audio_extract import extract_audio as audio_extract_lib
    AUDIO_EXTRACT_AVAILABLE = True
    logging.info("Successfully imported audio-extract library")
except ImportError:
    AUDIO_EXTRACT_AVAILABLE = False
    logging.warning("audio-extract library not available. Falling back to other methods.")

# Try to import moviepy, but provide a fallback if it's not available
try:
    # Try different import methods for MoviePy
    try:
        from moviepy.editor import VideoFileClip
        MOVIEPY_AVAILABLE = True
        logging.info("Successfully imported MoviePy using standard import")
    except ImportError:
        # Try alternative import method
        import sys
        import importlib.util

        # Try to find the moviepy package
        spec = importlib.util.find_spec("moviepy")
        if spec is not None:
            # If found, try to import it directly
            moviepy = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(moviepy)

            # Now try to get the VideoFileClip class
            if hasattr(moviepy, 'editor') and hasattr(moviepy.editor, 'VideoFileClip'):
                VideoFileClip = moviepy.editor.VideoFileClip
                MOVIEPY_AVAILABLE = True
                logging.info("Successfully imported MoviePy using importlib")
            else:
                raise ImportError("Could not find VideoFileClip in moviepy.editor")
        else:
            raise ImportError("Could not find moviepy package")
except Exception as e:
    # Print detailed diagnostic information
    logging.warning(f"MoviePy not available. Audio extraction will be disabled. Error: {str(e)}")

    # Try to get more information about the moviepy package
    try:
        import pkg_resources
        try:
            dist = pkg_resources.get_distribution("moviepy")
            logging.info(f"MoviePy package found: {dist}")
            logging.info(f"MoviePy location: {dist.location}")
        except pkg_resources.DistributionNotFound:
            logging.warning("MoviePy package not found using pkg_resources")

        # Check Python path
        logging.info(f"Python path: {sys.path}")

        # Try to find moviepy in the path
        import os
        for path in sys.path:
            moviepy_path = os.path.join(path, "moviepy")
            if os.path.exists(moviepy_path):
                logging.info(f"Found moviepy directory at: {moviepy_path}")
                # Check if editor.py exists
                editor_path = os.path.join(moviepy_path, "editor.py")
                if os.path.exists(editor_path):
                    logging.info(f"Found editor.py at: {editor_path}")
                else:
                    logging.warning(f"editor.py not found at: {moviepy_path}")
    except Exception as diagnostic_error:
        logging.warning(f"Error during diagnostics: {str(diagnostic_error)}")

    MOVIEPY_AVAILABLE = False

# Try to import Google Generative AI
try:
    # Try different import methods for Google Generative AI
    try:
        import google.generativeai as genai
        GENAI_AVAILABLE = True
        logging.info("Successfully imported Google Generative AI using standard import")
    except ImportError:
        # Try alternative import method
        import importlib.util

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
    logging.warning(f"Google Generative AI not available. Transcription will be disabled. Error: {str(e)}")

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("transcription.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GeminiTranscription")

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
    logger.warning(f"Could not parse timestamp: {timestamp}, using 0 instead")
    return 0.0

def format_timestamp(seconds):
    """Convert seconds to a formatted timestamp string (HH:MM:SS or MM:SS).

    Args:
        seconds: Number of seconds to format

    Returns:
        Formatted timestamp string
    """
    if seconds < 3600:  # Less than an hour
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

class GeminiTranscriptionService:
    """Service for transcribing audio using Google's Gemini API"""

    def __init__(self, api_key=None):
        """Initialize the transcription service with the specified API key"""
        self.api_key = api_key
        self.client = None

    def initialize(self, api_key=None):
        """Initialize the Gemini client with API key"""
        try:
            if api_key:
                self.api_key = api_key

            if not self.api_key:
                logger.error("No API key provided for Gemini")
                return False

            logger.info("Initializing Gemini client")

            # Use the most reliable method first - google.generativeai
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai
                logger.info("Created Gemini client using google.generativeai")
                return True
            except ImportError:
                logger.warning("Failed to import google.generativeai")
            except Exception as e:
                logger.warning(f"Error configuring google.generativeai: {e}")

            # Try the new API format as fallback
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Created Gemini client using google.genai Client")
                return True
            except ImportError:
                logger.warning("Failed to import google.genai")
            except Exception as e:
                logger.warning(f"Error creating client with google.genai: {e}")

            # Last resort: try dynamic import
            try:
                import importlib
                genai_module = importlib.import_module("google.generativeai")
                genai_module.configure(api_key=self.api_key)
                self.client = genai_module
                logger.info("Created Gemini client using dynamic import")
                return True
            except Exception as e:
                logger.error(f"All client creation methods failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")
            return False

    def extract_audio(self, video_path, output_dir):
        """Extract audio from video file"""
        try:
            # Check if video file exists
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None

            # Log video file details
            video_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
            logger.info(f"Video file: {video_path} (Size: {video_size:.2f} MB)")

            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            # Generate output audio path
            audio_filename = f"audio_{int(time.time())}.mp3"
            audio_path = os.path.join(output_dir, audio_filename)

            # Try audio-extract library first (most reliable)
            if AUDIO_EXTRACT_AVAILABLE:
                try:
                    logger.info(f"Attempting to extract audio with audio-extract library")
                    audio_extract_lib(
                        input_path=video_path,
                        output_path=audio_path,
                        output_format="mp3",
                        overwrite=True
                    )

                    # Verify the audio file was created
                    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                        logger.info(f"Audio extracted successfully with audio-extract to {audio_path}")
                        return audio_path
                    else:
                        logger.warning("audio-extract extraction failed: Output file is empty or not created")
                except Exception as e:
                    logger.error(f"Error with audio-extract extraction: {e}")
                    logger.warning("Falling back to ffmpeg")
            else:
                logger.warning("audio-extract library not available. Falling back to ffmpeg")

            # Try ffmpeg as second option
            try:
                logger.info(f"Attempting to extract audio with ffmpeg")
                command = [
                    "ffmpeg",
                    "-i", video_path,
                    "-q:a", "0",
                    "-map", "a",
                    "-y",  # Overwrite output file if it exists
                    audio_path
                ]

                # Run ffmpeg command
                result = subprocess.run(command, capture_output=True, text=True)

                # Check if ffmpeg was successful
                if result.returncode == 0 and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    logger.info(f"Audio extracted successfully with ffmpeg to {audio_path}")
                    return audio_path
                else:
                    logger.warning(f"ffmpeg extraction failed: {result.stderr}")
                    logger.warning("Trying MoviePy as fallback")
            except Exception as e:
                logger.error(f"Error with ffmpeg extraction: {e}")
                logger.warning("Falling back to MoviePy")

            # Try MoviePy as last resort
            if MOVIEPY_AVAILABLE:
                try:
                    logger.info(f"Attempting to extract audio with MoviePy")
                    video = VideoFileClip(video_path)
                    if video.audio is None:
                        logger.warning("No audio track found in video")
                        return None

                    video.audio.write_audiofile(audio_path, verbose=False, logger=None)
                    video.close()

                    # Verify the audio file was created
                    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                        logger.info(f"Audio extracted to {audio_path}")
                        return audio_path
                    else:
                        logger.error("Audio extraction failed: Output file is empty or not created")
                        return None
                except Exception as e:
                    logger.error(f"Error extracting audio with MoviePy: {e}")
                    return None
            else:
                logger.error("Cannot extract audio: No extraction methods available or all methods failed")
                return None
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return None

    def transcribe(self, audio_path, callback=None):
        """Transcribe audio file using Gemini API"""
        try:
            if callback:
                callback("Transcribing audio with Gemini... This may take a few minutes.")

            # Check if audio file exists
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return None

            # Log audio file details
            audio_size = os.path.getsize(audio_path) / (1024 * 1024)  # Size in MB
            logger.info(f"Audio file: {audio_path} (Size: {audio_size:.2f} MB)")

            # Initialize Gemini client if needed
            if self.client is None:
                self.initialize(self.api_key)
                if self.client is None:
                    logger.error("Failed to initialize Gemini client")
                    return None

            # Method 1: Use GenerativeModel for transcription (most reliable)
            try:
                logger.info("Using GenerativeModel for transcription")

                # Import and configure Gemini
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)

                # Create model
                model = genai.GenerativeModel('gemini-2.0-flash')

                # Read the audio file
                with open(audio_path, 'rb') as f:
                    audio_bytes = f.read()

                # Generate a transcript with special handling for Hindi content and improved analysis
                prompt = """Generate a detailed transcript of the speech with accurate timestamps.

1. LANGUAGE HANDLING:
   - Detect the language of the content
   - If the content is in Hindi, provide both Hindi script and transliteration in Roman script
   - For all content, provide an English translation if the original is not in English

2. CONTENT ANALYSIS:
   - Identify the main topic being taught in the video
   - Extract key concepts and important points
   - For each timestamp segment, provide a concise summary of what has been taught up to that point

3. FORMAT REQUIREMENTS:
   - Format the output as a JSON with the following structure:
     - 'text': full transcription in the original language
     - 'language': detected language name
     - 'topic': main topic being taught in the video
     - 'summary': concise summary of the entire content (1-2 paragraphs)
     - 'key_concepts': array of important concepts covered
     - 'segments': array of objects with:
       - 'start': timestamp in seconds when segment begins
       - 'end': timestamp in seconds when segment ends
       - 'text': transcribed text for this segment
       - 'transliteration': (for Hindi content) Roman script version
       - 'translation': English translation if original is not in English
       - 'summary': concise summary of what has been taught up to this point

4. RESPONSE LANGUAGE:
   - All summaries, analysis, and metadata should be in English, regardless of the original content language
   - Only the original transcription and transliteration should be in the source language"""

                # Create content parts
                content = [
                    {"text": prompt},
                    {"mime_type": "audio/mp3", "data": audio_bytes}
                ]

                # Generate content
                logger.info("Generating transcription with Gemini")
                response = model.generate_content(content)

                # Process the response
                if hasattr(response, 'text'):
                    response_text = response.text
                    logger.info(f"Transcription successful: {len(response_text)} characters")

                    # Save the transcription to a file (for debugging)
                    output_dir = os.path.dirname(audio_path)
                    transcription_path = os.path.join(output_dir, "transcription.txt")

                    with open(transcription_path, 'w', encoding='utf-8') as f:
                        f.write(response_text)

                    logger.info(f"Transcription saved to {transcription_path}")

                    # Try to parse as JSON
                    try:
                        # First try to parse as JSON directly
                        result = json.loads(response_text)

                        # Save as JSON file (for debugging)
                        json_path = os.path.join(output_dir, "transcription.json")
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2)

                        logger.info(f"JSON transcription saved to {json_path}")
                        return result
                    except json.JSONDecodeError:
                        # If not valid JSON, try to extract JSON from the text
                        try:
                            # Look for JSON-like content between triple backticks
                            import re
                            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                            if json_match:
                                result = json.loads(json_match.group(1))

                                # Save as JSON file (for debugging)
                                json_path = os.path.join(output_dir, "transcription.json")
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(result, f, indent=2)

                                logger.info(f"JSON transcription saved to {json_path}")
                                return result
                            else:
                                # Try to create a more structured JSON with enhanced content
                                logger.warning("Could not parse JSON from response, creating structured format with enhanced content")

                                # Try to detect language (especially for Hindi content)
                                language = "unknown"
                                if "hindi" in response_text.lower() or "हिंदी" in response_text:
                                    language = "Hindi"

                                # Extract topic and summary if possible
                                topic = "Unknown"
                                summary = ""
                                key_concepts = []

                                # Look for topic indicators
                                topic_match = re.search(r'(?:topic|subject|about)[\s:]+([^\n\.]+)', response_text, re.IGNORECASE)
                                if topic_match:
                                    topic = topic_match.group(1).strip()

                                # Look for summary indicators
                                summary_match = re.search(r'(?:summary|overview)[\s:]+([^\n]+(?:\n[^\n]+){0,5})', response_text, re.IGNORECASE)
                                if summary_match:
                                    summary = summary_match.group(1).strip()

                                # Look for key concepts
                                concepts_match = re.search(r'(?:key concepts|important points|main ideas)[\s:]+([^\n]+(?:\n[^\n]+){0,10})', response_text, re.IGNORECASE)
                                if concepts_match:
                                    concepts_text = concepts_match.group(1)
                                    # Extract bullet points or numbered items
                                    concept_items = re.findall(r'(?:[-•*]\s*|\d+\.\s*)([^\n]+)', concepts_text)
                                    if concept_items:
                                        key_concepts = [item.strip() for item in concept_items]
                                    else:
                                        # If no bullet points, just split by sentences
                                        key_concepts = [s.strip() for s in re.split(r'[.;]', concepts_text) if s.strip()]

                                # Try to extract segments with timestamps
                                segments = []

                                # Try multiple timestamp patterns to handle different formats
                                # Pattern 1: Standard timestamp format "00:01:23: Text content"
                                timestamp_pattern1 = r'(\d+:\d+:\d+|\d+:\d+)(?:\s*-\s*(\d+:\d+:\d+|\d+:\d+))?\s*[:：]?\s*(.*?)(?=\n\d+:\d+|\n\d+:\d+:\d+|$)'

                                # Pattern 2: Timestamp at beginning of line with text following
                                timestamp_pattern2 = r'^\s*\[?(\d+:\d+:\d+|\d+:\d+)\]?\s*(?:-\s*\[?(\d+:\d+:\d+|\d+:\d+)\]?)?\s*[:：]?\s*(.*?)$'

                                # Pattern 3: Timestamp in brackets or parentheses
                                timestamp_pattern3 = r'\[(\d+:\d+:\d+|\d+:\d+)\]\s*(?:\[(\d+:\d+:\d+|\d+:\d+)\])?\s*(.*?)(?=\n\s*\[\d+|\n\s*\(\d+|$)'

                                # Try all patterns
                                patterns = [timestamp_pattern1, timestamp_pattern2, timestamp_pattern3]
                                matches = []

                                for pattern in patterns:
                                    matches = re.findall(pattern, response_text, re.MULTILINE | re.DOTALL)
                                    if matches:
                                        logger.info(f"Found {len(matches)} segments using pattern: {pattern}")
                                        break

                                # Process matches to create segments with enhanced information
                                if matches:
                                    current_summary = ""
                                    for i, match in enumerate(matches):
                                        start_time = match[0].strip()
                                        end_time = match[1].strip() if match[1] else ""
                                        text = match[2].strip()

                                        # Convert timestamps to seconds
                                        start_seconds = convert_timestamp_to_seconds(start_time)
                                        end_seconds = convert_timestamp_to_seconds(end_time) if end_time else start_seconds + 30

                                        # Extract transliteration and translation if available
                                        transliteration = ""
                                        translation = ""
                                        segment_summary = ""

                                        # Look for transliteration in parentheses for Hindi content
                                        if language == "Hindi":
                                            trans_match = re.search(r'(.*?)(?:\s*\((.*?)\))?$', text)
                                            if trans_match and trans_match.group(2):
                                                text = trans_match.group(1).strip()
                                                transliteration = trans_match.group(2).strip()

                                        # Look for translation marked with "Translation:" or similar
                                        trans_match = re.search(r'(?:Translation|English)[\s:]+([^\n]+)', text, re.IGNORECASE)
                                        if trans_match:
                                            translation = trans_match.group(1).strip()

                                        # Look for summary marked with "Summary:" or similar
                                        summary_match = re.search(r'(?:Summary|Up to this point)[\s:]+([^\n]+)', text, re.IGNORECASE)
                                        if summary_match:
                                            segment_summary = summary_match.group(1).strip()

                                        # If no explicit summary found, generate a simple one based on position
                                        if not segment_summary:
                                            if i == 0:
                                                segment_summary = "Introduction to the topic"
                                            else:
                                                segment_summary = f"Continuing explanation of {topic}"

                                        # Update the current summary for progressive summaries
                                        current_summary = segment_summary

                                        # Create segment with all available information
                                        segment = {
                                            "start": start_seconds,
                                            "end": end_seconds,
                                            "text": text,
                                            "summary": segment_summary
                                        }

                                        if transliteration:
                                            segment["transliteration"] = transliteration

                                        if translation:
                                            segment["translation"] = translation

                                        segments.append(segment)

                                # If no matches found with any pattern, create segments by content analysis
                                if not matches:
                                    logger.warning("No timestamp patterns found, creating segments by content analysis")

                                    # Split content by newlines and create segments
                                    lines = [line.strip() for line in response_text.split('\n') if line.strip()]

                                    # Try to find any timestamps in the content
                                    timestamp_finder = r'(\d+:\d+:\d+|\d+:\d+)'

                                    current_time = 0
                                    segment_text = ""

                                    for line in lines:
                                        # Check if line contains a timestamp
                                        time_match = re.search(timestamp_finder, line)
                                        if time_match:
                                            # If we have accumulated text, save it as a segment
                                            if segment_text:
                                                segments.append({
                                                    "start": current_time,
                                                    "end": current_time + 30,
                                                    "text": segment_text.strip(),
                                                    "summary": f"Content at {format_timestamp(current_time)}"
                                                })

                                            # Update current time and start new segment
                                            current_time = convert_timestamp_to_seconds(time_match.group(1))
                                            # Remove timestamp from the line
                                            segment_text = re.sub(timestamp_finder, '', line).strip()
                                        else:
                                            # Add line to current segment
                                            segment_text += " " + line

                                    # Add the last segment if there's text
                                    if segment_text:
                                        segments.append({
                                            "start": current_time,
                                            "end": current_time + 30,
                                            "text": segment_text.strip(),
                                            "summary": f"Content at {format_timestamp(current_time)}"
                                        })

                                    logger.info(f"Created {len(segments)} segments by content analysis")

                                for match in matches:
                                    start_time = match[0].strip()
                                    end_time = match[1].strip() if match[1] else ""
                                    text = match[2].strip()

                                    # Convert timestamps to seconds
                                    start_seconds = convert_timestamp_to_seconds(start_time)
                                    end_seconds = convert_timestamp_to_seconds(end_time) if end_time else start_seconds + 10

                                    # Check for Hindi content and create transliteration field if needed
                                    transliteration = ""
                                    if language == "Hindi":
                                        # Look for transliteration in parentheses
                                        trans_match = re.search(r'(.*?)(?:\s*\((.*?)\))?$', text)
                                        if trans_match and trans_match.group(2):
                                            text = trans_match.group(1).strip()
                                            transliteration = trans_match.group(2).strip()

                                    segment = {
                                        "start": start_seconds,
                                        "end": end_seconds,
                                        "text": text
                                    }

                                    if transliteration:
                                        segment["transliteration"] = transliteration

                                    segments.append(segment)

                                # If no segments were found with any method, create at least one segment with the full text
                                if not segments:
                                    logger.warning("No segments created by any method, creating a single segment with full text")
                                    segments = [{
                                        "start": 0,
                                        "end": 60,  # Assume 1 minute for the full content
                                        "text": response_text.strip(),
                                        "summary": "Full content of the video"
                                    }]

                                # Create the enhanced result structure with all the metadata
                                result = {
                                    "text": response_text,
                                    "language": language,
                                    "topic": topic,
                                    "summary": summary if summary else "No summary available",
                                    "key_concepts": key_concepts if key_concepts else ["No key concepts extracted"],
                                    "segments": segments
                                }

                                # Save the structured JSON for debugging
                                json_path = os.path.join(output_dir, "transcription_structured.json")
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(result, f, indent=2, ensure_ascii=False)

                                logger.info(f"Created enhanced structured JSON with {len(segments)} segments")
                                return result
                        except Exception as e:
                            logger.error(f"Error parsing JSON: {e}")
                            # Return the raw text if JSON parsing failed
                            return {"text": response_text, "segments": []}
                else:
                    logger.error("No response from Gemini API")
                    return None

            except Exception as e:
                logger.error(f"Error with GenerativeModel method: {e}")
                logger.info("Falling back to alternative methods")

                # Method 2: Try Files API (for files > 20MB)
                try:
                    # Check if client has files attribute
                    if hasattr(self.client, 'files') and hasattr(self.client.files, 'upload'):
                        logger.info("Trying Files API method")
                        myfile = self.client.files.upload(file=audio_path)
                        logger.info(f"Audio file uploaded successfully with ID: {myfile.name}")

                        # Generate a transcript with special handling for Hindi content
                        prompt = "Generate a transcript of the speech with timestamps. If the content is in Hindi, keep it in Hindi script and also provide transliteration in Roman script (do not translate to English). Format the output as a JSON with 'text' containing the full transcription, 'language' indicating the detected language, and 'segments' containing an array of objects with 'start' (in seconds), 'end' (in seconds), 'text' fields, and 'transliteration' field for Hindi content."

                        # Check if client has models attribute
                        if hasattr(self.client, 'models') and hasattr(self.client.models, 'generate_content'):
                            response = self.client.models.generate_content(
                                model="gemini-2.0-flash",
                                contents=[prompt, myfile]
                            )

                            # Process the response
                            if response and hasattr(response, 'text'):
                                response_text = response.text
                                logger.info(f"Transcription successful: {len(response_text)} characters")

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
                                            # Try to create a more structured JSON
                                            logger.warning("Could not parse JSON from response, creating structured format")

                                            # Try to detect language (especially for Hindi content)
                                            language = "unknown"
                                            if "hindi" in response_text.lower() or "हिंदी" in response_text:
                                                language = "Hindi"

                                            # Try to extract segments with timestamps
                                            segments = []

                                            # First try to extract the full text content
                                            full_text = response_text.strip()

                                            # Try multiple timestamp patterns to handle different formats
                                            # Pattern 1: Standard timestamp format "00:01:23: Text content"
                                            timestamp_pattern1 = r'(\d+:\d+:\d+|\d+:\d+)(?:\s*-\s*(\d+:\d+:\d+|\d+:\d+))?\s*[:：]?\s*(.*?)(?=\n\d+:\d+|\n\d+:\d+:\d+|$)'

                                            # Pattern 2: Timestamp at beginning of line with text following
                                            timestamp_pattern2 = r'^\s*\[?(\d+:\d+:\d+|\d+:\d+)\]?\s*(?:-\s*\[?(\d+:\d+:\d+|\d+:\d+)\]?)?\s*[:：]?\s*(.*?)$'

                                            # Pattern 3: Timestamp in brackets or parentheses
                                            timestamp_pattern3 = r'\[(\d+:\d+:\d+|\d+:\d+)\]\s*(?:\[(\d+:\d+:\d+|\d+:\d+)\])?\s*(.*?)(?=\n\s*\[\d+|\n\s*\(\d+|$)'

                                            # Try all patterns
                                            patterns = [timestamp_pattern1, timestamp_pattern2, timestamp_pattern3]

                                            for pattern in patterns:
                                                matches = re.findall(pattern, response_text, re.MULTILINE | re.DOTALL)
                                                if matches:
                                                    logger.info(f"Found {len(matches)} segments using pattern: {pattern}")
                                                    break

                                            # If no matches found with any pattern, try to create segments by splitting on newlines
                                            if not matches:
                                                logger.warning("No timestamp patterns found, creating segments by content analysis")

                                                # Split content by newlines and create segments
                                                lines = [line.strip() for line in response_text.split('\n') if line.strip()]

                                                # Try to find any timestamps in the content
                                                timestamp_finder = r'(\d+:\d+:\d+|\d+:\d+)'

                                                current_time = 0
                                                segment_text = ""

                                                for line in lines:
                                                    # Check if line contains a timestamp
                                                    time_match = re.search(timestamp_finder, line)
                                                    if time_match:
                                                        # If we have accumulated text, save it as a segment
                                                        if segment_text:
                                                            segments.append({
                                                                "start": current_time,
                                                                "end": current_time + 10,
                                                                "text": segment_text.strip()
                                                            })

                                                        # Update current time and start new segment
                                                        current_time = convert_timestamp_to_seconds(time_match.group(1))
                                                        # Remove timestamp from the line
                                                        segment_text = re.sub(timestamp_finder, '', line).strip()
                                                    else:
                                                        # Add line to current segment
                                                        segment_text += " " + line

                                                # Add the last segment if there's text
                                                if segment_text:
                                                    segments.append({
                                                        "start": current_time,
                                                        "end": current_time + 10,
                                                        "text": segment_text.strip()
                                                    })

                                                logger.info(f"Created {len(segments)} segments by content analysis")

                                            for match in matches:
                                                start_time = match[0].strip()
                                                end_time = match[1].strip() if match[1] else ""
                                                text = match[2].strip()

                                                # Convert timestamps to seconds
                                                start_seconds = convert_timestamp_to_seconds(start_time)
                                                end_seconds = convert_timestamp_to_seconds(end_time) if end_time else start_seconds + 10

                                                # Check for Hindi content and create transliteration field if needed
                                                transliteration = ""
                                                if language == "Hindi":
                                                    # Look for transliteration in parentheses
                                                    trans_match = re.search(r'(.*?)(?:\s*\((.*?)\))?$', text)
                                                    if trans_match and trans_match.group(2):
                                                        text = trans_match.group(1).strip()
                                                        transliteration = trans_match.group(2).strip()

                                                segment = {
                                                    "start": start_seconds,
                                                    "end": end_seconds,
                                                    "text": text
                                                }

                                                if transliteration:
                                                    segment["transliteration"] = transliteration

                                                segments.append(segment)

                                            # If no segments were found with any method, create at least one segment with the full text
                                            if not segments:
                                                logger.warning("No segments created by any method, creating a single segment with full text")
                                                segments = [{
                                                    "start": 0,
                                                    "end": 60,  # Assume 1 minute for the full content
                                                    "text": response_text.strip()
                                                }]

                                            # Create the result structure
                                            result = {
                                                "text": response_text,
                                                "language": language,
                                                "segments": segments
                                            }
                                    except Exception as e:
                                        logger.error(f"Error parsing response: {e}")
                                        result = {
                                            "text": response_text,
                                            "segments": []
                                        }

                                logger.info("Transcription complete")
                                return result
                            else:
                                logger.error("No response from Gemini API")
                                return None
                        else:
                            logger.error("Client does not have 'models.generate_content' method")
                    else:
                        logger.error("Client does not have 'files.upload' method")

                except Exception as e:
                    logger.error(f"Error with Files API method: {e}")
                    logger.info("Falling back to inline audio data method")

                    # Method 3: Pass inline audio data (for files < 20MB)
                    try:
                        # Check if file is too large for inline
                        if audio_size > 19:  # 19MB to be safe
                            logger.error("Audio file too large for inline method (>19MB)")
                            return None

                        # Try to import types for inline audio
                        try:
                            from google.genai import types

                            # Read the audio file
                            with open(audio_path, 'rb') as f:
                                audio_bytes = f.read()

                            logger.info(f"Sending inline audio data ({audio_size:.2f} MB)")

                            prompt = "Generate a transcript of the speech with timestamps. If the content is in Hindi, keep it in Hindi script and also provide transliteration in Roman script (do not translate to English). Format the output as a JSON with 'text' containing the full transcription, 'language' indicating the detected language, and 'segments' containing an array of objects with 'start' (in seconds), 'end' (in seconds), 'text' fields, and 'transliteration' field for Hindi content."

                            # Check if client has models attribute
                            if hasattr(self.client, 'models') and hasattr(self.client.models, 'generate_content'):
                                response = self.client.models.generate_content(
                                    model='gemini-2.0-flash',
                                    contents=[
                                        prompt,
                                        types.Part.from_bytes(
                                            data=audio_bytes,
                                            mime_type='audio/mp3',
                                        )
                                    ]
                                )

                                # Process the response
                                if response and hasattr(response, 'text'):
                                    response_text = response.text
                                    logger.info(f"Transcription successful: {len(response_text)} characters")

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
                                                # Try to create a more structured JSON
                                                logger.warning("Could not parse JSON from response, creating structured format")

                                                # Try to detect language (especially for Hindi content)
                                                language = "unknown"
                                                if "hindi" in response_text.lower() or "हिंदी" in response_text:
                                                    language = "Hindi"

                                                # Try to extract segments with timestamps
                                                segments = []

                                                # Try multiple timestamp patterns to handle different formats
                                                # Pattern 1: Standard timestamp format "00:01:23: Text content"
                                                timestamp_pattern1 = r'(\d+:\d+:\d+|\d+:\d+)(?:\s*-\s*(\d+:\d+:\d+|\d+:\d+))?\s*[:：]?\s*(.*?)(?=\n\d+:\d+|\n\d+:\d+:\d+|$)'

                                                # Pattern 2: Timestamp at beginning of line with text following
                                                timestamp_pattern2 = r'^\s*\[?(\d+:\d+:\d+|\d+:\d+)\]?\s*(?:-\s*\[?(\d+:\d+:\d+|\d+:\d+)\]?)?\s*[:：]?\s*(.*?)$'

                                                # Pattern 3: Timestamp in brackets or parentheses
                                                timestamp_pattern3 = r'\[(\d+:\d+:\d+|\d+:\d+)\]\s*(?:\[(\d+:\d+:\d+|\d+:\d+)\])?\s*(.*?)(?=\n\s*\[\d+|\n\s*\(\d+|$)'

                                                # Try all patterns
                                                patterns = [timestamp_pattern1, timestamp_pattern2, timestamp_pattern3]

                                                for pattern in patterns:
                                                    matches = re.findall(pattern, response_text, re.MULTILINE | re.DOTALL)
                                                    if matches:
                                                        logger.info(f"Found {len(matches)} segments using pattern: {pattern}")
                                                        break

                                                # If no matches found with any pattern, try to create segments by splitting on newlines
                                                if not matches:
                                                    logger.warning("No timestamp patterns found, creating segments by content analysis")

                                                    # Split content by newlines and create segments
                                                    lines = [line.strip() for line in response_text.split('\n') if line.strip()]

                                                    # Try to find any timestamps in the content
                                                    timestamp_finder = r'(\d+:\d+:\d+|\d+:\d+)'

                                                    current_time = 0
                                                    segment_text = ""

                                                    for line in lines:
                                                        # Check if line contains a timestamp
                                                        time_match = re.search(timestamp_finder, line)
                                                        if time_match:
                                                            # If we have accumulated text, save it as a segment
                                                            if segment_text:
                                                                segments.append({
                                                                    "start": current_time,
                                                                    "end": current_time + 10,
                                                                    "text": segment_text.strip()
                                                                })

                                                            # Update current time and start new segment
                                                            current_time = convert_timestamp_to_seconds(time_match.group(1))
                                                            # Remove timestamp from the line
                                                            segment_text = re.sub(timestamp_finder, '', line).strip()
                                                        else:
                                                            # Add line to current segment
                                                            segment_text += " " + line

                                                    # Add the last segment if there's text
                                                    if segment_text:
                                                        segments.append({
                                                            "start": current_time,
                                                            "end": current_time + 10,
                                                            "text": segment_text.strip()
                                                        })

                                                    logger.info(f"Created {len(segments)} segments by content analysis")

                                                for match in matches:
                                                    start_time = match[0].strip()
                                                    end_time = match[1].strip() if match[1] else ""
                                                    text = match[2].strip()

                                                    # Convert timestamps to seconds
                                                    start_seconds = convert_timestamp_to_seconds(start_time)
                                                    end_seconds = convert_timestamp_to_seconds(end_time) if end_time else start_seconds + 10

                                                    # Check for Hindi content and create transliteration field if needed
                                                    transliteration = ""
                                                    if language == "Hindi":
                                                        # Look for transliteration in parentheses
                                                        trans_match = re.search(r'(.*?)(?:\s*\((.*?)\))?$', text)
                                                        if trans_match and trans_match.group(2):
                                                            text = trans_match.group(1).strip()
                                                            transliteration = trans_match.group(2).strip()

                                                    segment = {
                                                        "start": start_seconds,
                                                        "end": end_seconds,
                                                        "text": text
                                                    }

                                                    if transliteration:
                                                        segment["transliteration"] = transliteration

                                                    segments.append(segment)

                                                # If no segments were found with any method, create at least one segment with the full text
                                                if not segments:
                                                    logger.warning("No segments created by any method, creating a single segment with full text")
                                                    segments = [{
                                                        "start": 0,
                                                        "end": 60,  # Assume 1 minute for the full content
                                                        "text": response_text.strip()
                                                    }]

                                                # Create the result structure
                                                result = {
                                                    "text": response_text,
                                                    "language": language,
                                                    "segments": segments
                                                }
                                        except Exception as e:
                                            logger.error(f"Error parsing response: {e}")
                                            result = {
                                                "text": response_text,
                                                "segments": []
                                            }

                                    logger.info("Transcription complete")
                                    return result
                                else:
                                    logger.error("No response from Gemini API")
                                    return None
                            else:
                                logger.error("Client does not have 'models.generate_content' method")
                                return None
                        except ImportError:
                            logger.error("Could not import 'google.genai.types'")
                            return None

                    except Exception as e:
                        logger.error(f"Error with inline audio data method: {e}")
                        return None

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            if callback:
                callback(f"Error transcribing audio: {str(e)}")
            return None

    def transcribe_segments(self, video_path, segments, output_dir, callback=None):
        """Transcribe specific segments of a video"""
        try:
            # Initialize Gemini client if needed
            if self.client is None:
                self.initialize(self.api_key)
                if self.client is None:
                    logger.error("Failed to initialize Gemini client")
                    return None

            # Extract full audio
            audio_path = self.extract_audio(video_path, output_dir)
            if not audio_path:
                return None

            results = []

            # Import and configure Gemini
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)

            # Process each segment
            for i, segment in enumerate(segments):
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)

                if callback:
                    callback(f"Transcribing segment {i+1}/{len(segments)} ({start_time:.1f}s - {end_time:.1f}s)")

                # Create a temporary file for the segment
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_path = temp_file.name

                try:
                    # Extract segment audio using audio-extract if available
                    if AUDIO_EXTRACT_AVAILABLE:
                        try:
                            logger.info(f"Extracting segment audio with audio-extract library")
                            audio_extract_lib(
                                input_path=video_path,
                                output_path=temp_path,
                                output_format="mp3",
                                start_time=f"{int(start_time//60):02d}:{int(start_time%60):02d}",
                                duration=end_time-start_time,
                                overwrite=True
                            )

                            # Verify the audio file was created
                            if not (os.path.exists(temp_path) and os.path.getsize(temp_path) > 0):
                                raise Exception("Failed to extract segment audio with audio-extract")
                        except Exception as e:
                            logger.error(f"Error extracting segment with audio-extract: {e}")
                            logger.info("Falling back to MoviePy for segment extraction")

                            # Fall back to MoviePy
                            if MOVIEPY_AVAILABLE:
                                audio_clip = VideoFileClip(video_path).subclip(start_time, end_time).audio
                                audio_clip.write_audiofile(temp_path, verbose=False, logger=None)
                            else:
                                logger.error("Cannot extract segment: MoviePy not available")
                                continue
                    else:
                        # Use MoviePy if audio-extract is not available
                        if MOVIEPY_AVAILABLE:
                            audio_clip = VideoFileClip(video_path).subclip(start_time, end_time).audio
                            audio_clip.write_audiofile(temp_path, verbose=False, logger=None)
                        else:
                            logger.error("Cannot extract segment: No extraction methods available")
                            continue

                    # Method 1: Use GenerativeModel for transcription (most reliable)
                    try:
                        logger.info("Using GenerativeModel for segment transcription")

                        # Create model
                        model = genai.GenerativeModel('gemini-2.0-flash')

                        # Read the audio file
                        with open(temp_path, 'rb') as f:
                            audio_bytes = f.read()

                        # Generate a transcript with special handling for Hindi content
                        prompt = "Transcribe this audio clip accurately. If the content is in Hindi, keep it in Hindi script and also provide transliteration in Roman script (do not translate to English)."

                        # Create content parts
                        content = [
                            {"text": prompt},
                            {"mime_type": "audio/mp3", "data": audio_bytes}
                        ]

                        # Generate content
                        logger.info("Generating segment transcription with Gemini")
                        response = model.generate_content(content)

                        # Process the response
                        if hasattr(response, 'text'):
                            response_text = response.text
                            logger.info(f"Segment transcription successful: {len(response_text)} characters")

                            # Add to results
                            results.append({
                                'start': start_time,
                                'end': end_time,
                                'text': response_text
                            })
                        else:
                            logger.error("No response from Gemini API for segment")

                    except Exception as e:
                        logger.error(f"Error with GenerativeModel method for segment: {e}")
                        logger.info("Falling back to alternative methods")

                        # Method 2: Try Files API (for files > 20MB)
                        try:
                            # Check if client has files attribute
                            if hasattr(self.client, 'files') and hasattr(self.client.files, 'upload'):
                                logger.info("Trying Files API method for segment")
                                myfile = self.client.files.upload(file=temp_path)
                                logger.info(f"Segment audio file uploaded successfully")

                                prompt = "Transcribe this audio clip accurately. If the content is in Hindi, keep it in Hindi script and also provide transliteration in Roman script (do not translate to English)."

                                # Check if client has models attribute
                                if hasattr(self.client, 'models') and hasattr(self.client.models, 'generate_content'):
                                    response = self.client.models.generate_content(
                                        model="gemini-2.0-flash",
                                        contents=[prompt, myfile]
                                    )

                                    if response and hasattr(response, 'text'):
                                        response_text = response.text
                                        logger.info(f"Segment transcription successful: {len(response_text)} characters")

                                        # Add to results
                                        results.append({
                                            'start': start_time,
                                            'end': end_time,
                                            'text': response_text
                                        })
                                    else:
                                        logger.error("No response from Gemini API for segment")
                                else:
                                    logger.error("Client does not have 'models.generate_content' method")
                            else:
                                logger.error("Client does not have 'files.upload' method")

                        except Exception as e:
                            logger.error(f"Error with Files API method for segment: {e}")
                            logger.info("Trying inline audio data method for segment")

                            # Method 3: Pass inline audio data (for files < 20MB)
                            try:
                                # Get file size
                                audio_size = os.path.getsize(temp_path) / (1024 * 1024)  # Size in MB

                                # Check if file is too large for inline
                                if audio_size > 19:  # 19MB to be safe
                                    logger.error("Segment audio file too large for inline method (>19MB)")
                                    continue

                                # Try to import types for inline audio
                                try:
                                    from google.genai import types

                                    # Read the audio file
                                    with open(temp_path, 'rb') as f:
                                        audio_bytes = f.read()

                                    logger.info(f"Sending inline segment audio data ({audio_size:.2f} MB)")

                                    prompt = "Transcribe this audio clip accurately. If the content is in Hindi, keep it in Hindi script and also provide transliteration in Roman script (do not translate to English)."

                                    # Check if client has models attribute
                                    if hasattr(self.client, 'models') and hasattr(self.client.models, 'generate_content'):
                                        response = self.client.models.generate_content(
                                            model='gemini-2.0-flash',
                                            contents=[
                                                prompt,
                                                types.Part.from_bytes(
                                                    data=audio_bytes,
                                                    mime_type='audio/mp3',
                                                )
                                            ]
                                        )

                                        if response and hasattr(response, 'text'):
                                            response_text = response.text
                                            logger.info(f"Segment transcription successful: {len(response_text)} characters")

                                            # Add to results
                                            results.append({
                                                'start': start_time,
                                                'end': end_time,
                                                'text': response_text
                                            })
                                        else:
                                            logger.error("No response from Gemini API for segment")
                                    else:
                                        logger.error("Client does not have 'models.generate_content' method")
                                except ImportError:
                                    logger.error("Failed to import google.genai.types")
                                    continue

                            except Exception as e:
                                logger.error(f"Error with inline audio data method for segment: {e}")

                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)

            # Combine results
            if results:
                full_text = " ".join(segment['text'] for segment in results)

                return {
                    'text': full_text,
                    'segments': results
                }
            else:
                logger.error("No segments were successfully transcribed")
                return None

        except Exception as e:
            logger.error(f"Error transcribing segments: {e}")
            return None
