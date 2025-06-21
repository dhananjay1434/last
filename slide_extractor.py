import os
import cv2
import numpy as np
import subprocess
import io
import json
import re
import shutil
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from datetime import timedelta
import argparse
import threading
import multiprocessing
import time
import random
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from skimage.metrics import structural_similarity as ssim
from functools import lru_cache
from collections import defaultdict
import logging
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("slide_extractor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SlideExtractor")

# Import HumanDetector as a fallback for YOLO
try:
    from human_detector import HumanDetector
except ImportError:
    # Create a simple fallback HumanDetector class
    class HumanDetector:
        def __init__(self):
            pass

        def detect_humans(self, frame):
            """Fallback human detection - returns empty list"""
            return []

# YOLO model configuration
# Using a more OpenCV-compatible model
# We'll use a pre-trained MobileNet SSD model which is known to work well with OpenCV
YOLO_MODEL_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
YOLO_MODEL_WEIGHTS_URL = "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20180205_fp16/res10_300x300_ssd_iter_140000_fp16.caffemodel"
YOLO_MODEL_PATH = "deploy.prototxt"
YOLO_MODEL_WEIGHTS_PATH = "res10_300x300_ssd_iter_140000_fp16.caffemodel"
YOLO_CONFIDENCE_THRESHOLD = 0.5
YOLO_PERSON_CLASS_ID = 1  # For face detection, we'll use any detection as a "person"

def download_yolo_model():
    """Download the YOLO model and weights if they don't exist."""
    model_exists = os.path.exists(YOLO_MODEL_PATH)
    weights_exist = os.path.exists(YOLO_MODEL_WEIGHTS_PATH)

    if not model_exists or not weights_exist:
        try:
            # Download model configuration file
            if not model_exists:
                logger.info(f"Downloading model configuration from {YOLO_MODEL_URL}")
                response = requests.get(YOLO_MODEL_URL, stream=True)
                response.raise_for_status()

                with open(YOLO_MODEL_PATH, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"Model configuration downloaded to {YOLO_MODEL_PATH}")

            # Download model weights file
            if not weights_exist:
                logger.info(f"Downloading model weights from {YOLO_MODEL_WEIGHTS_URL}")
                response = requests.get(YOLO_MODEL_WEIGHTS_URL, stream=True)
                response.raise_for_status()

                with open(YOLO_MODEL_WEIGHTS_PATH, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"Model weights downloaded to {YOLO_MODEL_WEIGHTS_PATH}")

            return True
        except Exception as e:
            logger.error(f"Error downloading model files: {e}")
            return False
    return True

class SlideExtractor:
    """
    Advanced YouTube Slide Extractor with scene detection, content analysis, and slide organization.

    Features:
    - Adaptive frame sampling using scene detection
    - Content-aware slide classification
    - Intelligent slide organization
    - Advanced image processing for better quality
    - Metadata extraction and indexing
    """

    # Slide types for classification
    SLIDE_TYPES = {
        'title': 0,
        'content': 1,
        'image': 2,
        'chart': 3,
        'code': 4,
        'table': 5,
        'end': 6,
        'other': 7
    }

    def __init__(self, video_url, output_dir="slides", interval=5, similarity_threshold=0.98, ocr_confidence=30,
                 resize_factor=0.5, histogram_threshold=0.95, use_multiprocessing=False, callback=None,
                 adaptive_sampling=True, enhance_quality=True, extract_content=True, organize_slides=True,
                 min_scene_length=5, max_scene_length=30, ignore_human_movement=True):
        """
        Initialize the SlideExtractor with advanced options.

        Args:
            video_url: URL of the YouTube video
            output_dir: Directory to save slides
            interval: Base interval between frames (seconds) - used when adaptive_sampling is False
            similarity_threshold: Threshold for slide similarity (0.0-1.0)
            ocr_confidence: Confidence threshold for OCR (0-100)
            resize_factor: Factor to resize frames for faster processing
            histogram_threshold: Threshold for quick histogram comparison
            use_multiprocessing: Whether to use parallel processing
            callback: Function to call with status updates
            adaptive_sampling: Use scene detection for adaptive frame sampling
            enhance_quality: Apply image enhancement to improve slide quality
            extract_content: Extract and index slide content
            organize_slides: Organize slides by content and type
            min_scene_length: Minimum scene length in seconds
            max_scene_length: Maximum scene length in seconds
            ignore_human_movement: Ignore human movements when detecting slide changes
        """
        self.video_url = video_url
        self.output_dir = output_dir
        self.interval = interval
        self.similarity_threshold = similarity_threshold
        self.ocr_confidence = ocr_confidence
        self.video_path = os.path.join(self.output_dir, "temp_video.mp4")
        self.previous_text = ""
        self.resize_factor = resize_factor
        self.histogram_threshold = histogram_threshold
        self.use_multiprocessing = use_multiprocessing
        self.callback = callback
        self.stop_requested = False

        # Advanced options
        self.adaptive_sampling = adaptive_sampling
        self.enhance_quality = enhance_quality
        self.extract_content = extract_content
        self.organize_slides = organize_slides
        self.min_scene_length = min_scene_length
        self.max_scene_length = max_scene_length
        self.ignore_human_movement = ignore_human_movement

        # Create directory structure
        self.temp_dir = os.path.join(self.output_dir, "temp")
        self.metadata_dir = os.path.join(self.output_dir, "metadata")
        self.organized_dir = os.path.join(self.output_dir, "organized")

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)

        # Initialize data structures
        self.slides_metadata = {}
        self.scene_boundaries = []
        self.slide_content_index = defaultdict(list)

        # OCR cache - using frame hashes as keys
        self.ocr_cache = {}

        # Initialize YOLO model if ignore_human_movement is enabled
        self.yolo_model = None
        if self.ignore_human_movement:
            self._initialize_yolo_model()

        logger.info(f"Initialized SlideExtractor with video: {video_url}")
        logger.info(f"Advanced options: adaptive_sampling={adaptive_sampling}, "
                   f"enhance_quality={enhance_quality}, extract_content={extract_content}, "
                   f"organize_slides={organize_slides}, ignore_human_movement={ignore_human_movement}")

    def _initialize_yolo_model(self):
        """Initialize the SSD MobileNet model for human detection."""
        try:
            # Check if model files exist
            import os
            model_path = os.path.abspath(YOLO_MODEL_PATH)
            weights_path = os.path.abspath(YOLO_MODEL_WEIGHTS_PATH)

            model_exists = os.path.exists(YOLO_MODEL_PATH)
            weights_exist = os.path.exists(YOLO_MODEL_WEIGHTS_PATH)

            if model_exists and weights_exist:
                logger.info(f"Model configuration found at: {model_path}")
                logger.info(f"Model weights found at: {weights_path}")
                model_size = os.path.getsize(YOLO_MODEL_PATH) / 1024  # Size in KB
                weights_size = os.path.getsize(YOLO_MODEL_WEIGHTS_PATH) / (1024 * 1024)  # Size in MB
                logger.info(f"Model configuration size: {model_size:.2f} KB")
                logger.info(f"Model weights size: {weights_size:.2f} MB")
            else:
                logger.info("Model files not found, attempting to download")
                # Try to download the model
                if download_yolo_model():
                    logger.info(f"Model files downloaded successfully")
                else:
                    logger.error("Failed to download model files")
                    logger.info("Falling back to HumanDetector for human detection")
                    self.human_detector = HumanDetector()
                    return False

            try:
                # Load the face detection model (Caffe model)
                logger.info(f"Attempting to load model from: {YOLO_MODEL_PATH} and {YOLO_MODEL_WEIGHTS_PATH}")
                self.yolo_model = cv2.dnn.readNetFromCaffe(YOLO_MODEL_PATH, YOLO_MODEL_WEIGHTS_PATH)
                logger.info("Model initialized successfully")

                # Set backend and target (CUDA if available)
                if hasattr(cv2, 'cuda') and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    logger.info("CUDA is available, setting CUDA backend")
                    self.yolo_model.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                    self.yolo_model.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                    logger.info("Model using CUDA acceleration")
                else:
                    logger.info("CUDA not available, using CPU backend")
                    self.yolo_model.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.yolo_model.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                    logger.info("Model using CPU")

                # Try to get output layer names to verify model is loaded correctly
                try:
                    output_layers = self.yolo_model.getUnconnectedOutLayersNames()
                    logger.info(f"Model output layers: {output_layers}")
                except Exception as e:
                    logger.warning(f"Could not get output layer names: {e}")

                return True
            except Exception as e:
                logger.error(f"Error initializing model: {e}")
                logger.info("Falling back to HumanDetector for human detection")
                # Initialize the fallback human detector
                self.human_detector = HumanDetector()
                return False
        except Exception as e:
            logger.error(f"Error in model initialization process: {e}")
            logger.info("Falling back to HumanDetector for human detection")
            # Initialize the fallback human detector
            self.human_detector = HumanDetector()
            return False

    def _detect_humans(self, frame):
        """
        Detect faces in a frame using SSD face detector or fallback to HumanDetector.
        We use face detection as a proxy for human detection.

        Args:
            frame: The frame to analyze

        Returns:
            List of bounding boxes for detected faces: [(x1, y1, x2, y2), ...]
        """
        # If model is not available, use the fallback HumanDetector
        if self.yolo_model is None:
            if hasattr(self, 'human_detector'):
                # Use the fallback human detector
                boxes = self.human_detector.detect_humans(frame)
                # Convert from (x, y, w, h) to (x1, y1, x2, y2) format
                return [(box[0], box[1], box[0] + box[2], box[1] + box[3]) for box in boxes]
            return []

        try:
            # Get frame dimensions
            height, width = frame.shape[:2]

            # Create a blob from the frame - Face detector uses 300x300 input size
            # Mean values for the face detector are (104.0, 177.0, 123.0)
            blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0), swapRB=False, crop=False)

            # Set the input to the model
            self.yolo_model.setInput(blob)

            # Forward pass through the network
            detections = self.yolo_model.forward()

            # Process the outputs
            face_boxes = []

            # Face detector output format:
            # detections shape is [1, 1, N, 7] where:
            # - N is the number of detections
            # - 7 = [image_id, label, confidence, x_min, y_min, x_max, y_max]

            # Extract detections with confidence > threshold
            for i in range(detections.shape[2]):
                # Extract confidence
                confidence = detections[0, 0, i, 2]

                # For face detector, we don't need to check class ID as it only detects faces
                if confidence > YOLO_CONFIDENCE_THRESHOLD:
                    # Face detector returns normalized coordinates [x_min, y_min, x_max, y_max]
                    # Extract and denormalize the coordinates
                    x1 = int(detections[0, 0, i, 3] * width)
                    y1 = int(detections[0, 0, i, 4] * height)
                    x2 = int(detections[0, 0, i, 5] * width)
                    y2 = int(detections[0, 0, i, 6] * height)

                    # Add some padding around the face to capture more of the person
                    padding_x = int((x2 - x1) * 1.0)  # 100% wider
                    padding_y = int((y2 - y1) * 2.0)  # 200% taller (to capture body)

                    x1 = max(0, x1 - padding_x)
                    y1 = max(0, y1 - padding_y // 2)
                    x2 = min(width, x2 + padding_x)
                    y2 = min(height, y2 + padding_y)

                    # Add the bounding box to the list
                    face_boxes.append((x1, y1, x2, y2))

            return face_boxes

        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            logger.info("Falling back to HumanDetector for this frame")

            # Fallback to HumanDetector
            if hasattr(self, 'human_detector'):
                boxes = self.human_detector.detect_humans(frame)
                # Convert from (x, y, w, h) to (x1, y1, x2, y2) format
                return [(box[0], box[1], box[0] + box[2], box[1] + box[3]) for box in boxes]
            return []

    def _create_human_mask(self, frame, human_boxes):
        """
        Create a mask that excludes regions with humans.

        Args:
            frame: The original frame
            human_boxes: List of bounding boxes for detected humans in format (x1, y1, x2, y2) or (x, y, w, h)

        Returns:
            A mask where human regions are black (0) and the rest is white (255)
        """
        height, width = frame.shape[:2]
        mask = np.ones((height, width), dtype=np.uint8) * 255

        # Draw filled black rectangles for each human detection
        for box in human_boxes:
            # Check if box is in (x1, y1, x2, y2) format or (x, y, w, h) format
            if len(box) == 4:
                if box[2] > box[0] and box[3] > box[1]:  # (x1, y1, x2, y2) format
                    x1, y1, x2, y2 = box
                else:  # (x, y, w, h) format
                    x1, y1, w, h = box
                    x2, y2 = x1 + w, y1 + h
            else:
                # Skip invalid boxes
                continue

            # Add some padding around the human
            padding = 10
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(width, x2 + padding)
            y2 = min(height, y2 + padding)

            cv2.rectangle(mask, (x1, y1), (x2, y2), 0, -1)  # -1 means filled rectangle

        return mask

    def download_video(self):
        """Download the YouTube video using yt-dlp with multiple fallback strategies"""
        try:
            if self.callback:
                self.callback("Downloading video...")

            # Enhanced download strategies with better anti-bot measures
            import random
            import time

            # Rotate user agents to avoid detection
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0"
            ]

            strategies = [
                # Strategy 1: Enhanced with random user agent and delays
                [
                    "yt-dlp",
                    "-f", "best[height<=720][ext=mp4]/best[height<=720]/best",
                    "-o", self.video_path,
                    "--user-agent", random.choice(user_agents),
                    "--add-header", "Accept-Language:en-US,en;q=0.9",
                    "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "--add-header", "Accept-Encoding:gzip, deflate, br",
                    "--add-header", "Connection:keep-alive",
                    "--add-header", "Upgrade-Insecure-Requests:1",
                    "--extractor-args", "youtube:skip=dash,hls;player_skip=configs",
                    "--sleep-interval", "2",
                    "--max-sleep-interval", "5",
                    "--no-check-certificates",
                    "--ignore-errors",
                    self.video_url
                ],
                # Strategy 2: Mobile user agent with lower quality
                [
                    "yt-dlp",
                    "-f", "best[height<=480][ext=mp4]/worst[height>=240]",
                    "-o", self.video_path,
                    "--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                    "--add-header", "Accept-Language:en-US,en;q=0.9",
                    "--extractor-args", "youtube:skip=dash,hls",
                    "--sleep-interval", "3",
                    "--max-sleep-interval", "7",
                    "--no-check-certificates",
                    self.video_url
                ],
                # Strategy 3: Very conservative approach
                [
                    "yt-dlp",
                    "-f", "18/worst[ext=mp4]/worst",  # Format 18 is 360p MP4
                    "-o", self.video_path,
                    "--user-agent", random.choice(user_agents),
                    "--extractor-args", "youtube:skip=dash,hls,live_chat",
                    "--sleep-interval", "5",
                    "--max-sleep-interval", "10",
                    "--retries", "3",
                    "--fragment-retries", "3",
                    "--no-check-certificates",
                    "--ignore-errors",
                    self.video_url
                ],
                # Strategy 4: Separate audio/video streams
                [
                    "yt-dlp",
                    "-f", "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
                    "-o", self.video_path,
                    "--user-agent", random.choice(user_agents),
                    "--merge-output-format", "mp4",
                    "--sleep-interval", "4",
                    "--no-check-certificates",
                    "--ignore-errors",
                    self.video_url
                ],
                # Strategy 5: Minimal approach with basic format
                [
                    "yt-dlp",
                    "-f", "worst",
                    "-o", self.video_path,
                    "--user-agent", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                    "--no-check-certificates",
                    "--ignore-errors",
                    "--no-warnings",
                    self.video_url
                ]
            ]

            for i, command in enumerate(strategies, 1):
                try:
                    if self.callback:
                        self.callback(f"Trying download method {i}/{len(strategies)}...")

                    print(f"Attempting download with strategy {i}")

                    # Add random delay between attempts to avoid rate limiting
                    if i > 1:
                        delay = random.uniform(2, 5)
                        time.sleep(delay)

                    result = subprocess.run(command, capture_output=True, text=True, timeout=240)

                    if result.returncode == 0 and os.path.exists(self.video_path):
                        file_size = os.path.getsize(self.video_path)
                        if file_size > 1024:  # File should be larger than 1KB
                            print(f"✅ Video downloaded successfully using method {i} (Size: {file_size/1024/1024:.1f}MB)")
                            if self.callback:
                                self.callback("Video downloaded successfully")
                            return True
                        else:
                            print(f"❌ Downloaded file too small ({file_size} bytes), trying next method")
                            if os.path.exists(self.video_path):
                                os.remove(self.video_path)
                    else:
                        print(f"❌ Method {i} failed with return code {result.returncode}")

                except subprocess.TimeoutExpired:
                    print(f"⏰ Method {i} timed out after 3 minutes")
                    continue
                except Exception as e:
                    print(f"💥 Method {i} exception: {str(e)[:100]}...")
                    continue

            # If all methods fail, provide helpful error message
            error_msg = "❌ Failed to download video after trying all methods.\n\n"
            error_msg += "This is likely due to YouTube's enhanced bot detection. Possible solutions:\n"
            error_msg += "1. Try a different YouTube video (some are more restricted)\n"
            error_msg += "2. Use a video from a different platform\n"
            error_msg += "3. Try again later (YouTube restrictions may be temporary)\n"
            error_msg += "4. Use a shorter or more popular video\n\n"
            error_msg += "The service is working correctly - this is a YouTube access limitation."

            print(error_msg)
            if self.callback:
                self.callback(f"Download failed: YouTube bot detection active. Try a different video.")
            return False

        except Exception as e:
            error_msg = f"Unexpected error during video download: {e}"
            print(error_msg)
            if self.callback:
                self.callback(f"Error: {error_msg}")
            return False

    def detect_scenes(self, cap, fps, total_frames):
        """
        Detect scene changes in the video for adaptive frame sampling.

        This method analyzes the video to find significant changes that likely
        represent transitions between slides or content sections.

        Args:
            cap: OpenCV video capture object
            fps: Frames per second of the video
            total_frames: Total number of frames in the video

        Returns:
            List of frame numbers where scene changes occur
        """
        if self.callback:
            self.callback("Detecting scene changes for adaptive sampling...")

        logger.info("Starting scene detection")

        # Parameters for scene detection
        sample_rate = max(1, int(fps))  # Sample every second for scene detection
        min_scene_frames = int(fps * self.min_scene_length)
        max_scene_frames = int(fps * self.max_scene_length)

        # Use a lower threshold for scene detection than for slide comparison
        scene_threshold = max(0.3, self.similarity_threshold - 0.3)

        scene_boundaries = [0]  # Always include the first frame
        prev_frame = None
        last_scene_frame = 0

        # Sample frames at regular intervals for scene detection
        for frame_num in range(0, total_frames, sample_rate):
            if self.stop_requested:
                break

            # Skip if we're too close to the last detected scene
            if frame_num - last_scene_frame < min_scene_frames:
                continue

            # Force a scene boundary if we've exceeded max scene length
            if frame_num - last_scene_frame > max_scene_frames:
                scene_boundaries.append(frame_num)
                last_scene_frame = frame_num
                continue

            # Read the current frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()

            if not ret:
                continue

            # Skip the first frame
            if prev_frame is None:
                prev_frame = frame
                continue

            # Calculate difference between frames
            diff = self._calculate_frame_difference(prev_frame, frame)

            # If difference exceeds threshold, mark as a scene boundary
            if diff > scene_threshold:
                scene_boundaries.append(frame_num)
                last_scene_frame = frame_num

                if self.callback and len(scene_boundaries) % 5 == 0:
                    self.callback(f"Detected {len(scene_boundaries)} scene changes...")

            prev_frame = frame

        # Always include the last frame
        if total_frames - 1 not in scene_boundaries:
            scene_boundaries.append(total_frames - 1)

        # Sort and deduplicate
        scene_boundaries = sorted(set(scene_boundaries))

        logger.info(f"Scene detection complete. Found {len(scene_boundaries)} scene boundaries")
        if self.callback:
            self.callback(f"Detected {len(scene_boundaries)} scene changes")

        self.scene_boundaries = scene_boundaries
        return scene_boundaries

    def _calculate_frame_difference(self, frame1, frame2):
        """Calculate the difference between two frames using histogram comparison"""
        # Convert to grayscale for faster processing
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Calculate histogram difference
        hist_diff = self._histogram_difference(frame1, frame2)

        # For significant histogram differences, return immediately
        if hist_diff > self.histogram_threshold + 0.1:
            return 1.0

        # For borderline cases, use structural similarity
        similarity, _ = ssim(gray1, gray2, full=True)
        return 1.0 - similarity

    def _get_adaptive_frame_numbers(self, scene_boundaries, fps, total_frames):
        """
        Generate frame numbers to sample based on scene boundaries.

        This method uses scene detection results to adaptively sample frames,
        taking more samples during complex scenes and fewer during static scenes.

        Args:
            scene_boundaries: List of frame numbers where scenes change
            fps: Frames per second of the video
            total_frames: Total number of frames in the video

        Returns:
            List of frame numbers to process
        """
        frame_numbers = []

        # Process each scene
        for i in range(len(scene_boundaries) - 1):
            start_frame = scene_boundaries[i]
            end_frame = scene_boundaries[i + 1]
            scene_length = end_frame - start_frame

            # Always include the start frame
            frame_numbers.append(start_frame)

            # For very short scenes, just use the start frame
            if scene_length < fps * 1.5:
                continue

            # Calculate adaptive sampling rate based on scene length
            # Longer scenes get sampled less frequently
            scene_duration = scene_length / fps

            if scene_duration < 5:
                # Short scenes: sample every 1-2 seconds
                sample_interval = int(fps * 1.5)
            elif scene_duration < 15:
                # Medium scenes: sample every 2-3 seconds
                sample_interval = int(fps * 2.5)
            else:
                # Long scenes: sample every 3-5 seconds
                sample_interval = int(fps * 4)

            # Add intermediate frames
            for frame in range(start_frame + sample_interval, end_frame, sample_interval):
                frame_numbers.append(frame)

        # Ensure the last frame is included
        if total_frames - 1 not in frame_numbers:
            frame_numbers.append(total_frames - 1)

        # Sort and deduplicate
        frame_numbers = sorted(set(frame_numbers))

        logger.info(f"Adaptive sampling generated {len(frame_numbers)} frames to analyze")
        return frame_numbers

    def is_playlist_url(self, url):
        """
        Check if the URL is a YouTube playlist.

        Args:
            url: YouTube URL to check

        Returns:
            Boolean indicating if the URL is a playlist
        """
        # Check for playlist indicators in URL
        return 'list=' in url

    def extract_playlist_videos(self, playlist_url):
        """
        Extract individual video URLs from a YouTube playlist.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            List of individual video URLs
        """
        try:
            if self.callback:
                self.callback("Extracting videos from playlist...")

            # Use yt-dlp to get playlist info
            command = [
                "yt-dlp",
                "--flat-playlist",
                "--print", "id",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "--extractor-args", "youtube:skip=dash,hls",
                "--no-check-certificates",
                playlist_url
            ]

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                # Extract video IDs and create URLs
                video_ids = result.stdout.strip().split('\n')
                video_urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids if video_id]

                if self.callback:
                    self.callback(f"Found {len(video_urls)} videos in playlist")

                return video_urls
            else:
                error_msg = f"Error extracting playlist: {result.stderr}"
                logger.error(error_msg)
                if self.callback:
                    self.callback(f"Error: {error_msg}")
                return []

        except Exception as e:
            error_msg = f"Error processing playlist: {str(e)}"
            logger.error(error_msg)
            if self.callback:
                self.callback(f"Error: {error_msg}")
            return []

    def extract_slides_from_playlist(self):
        """
        Process all videos in a YouTube playlist to extract slides.

        This method:
        1. Extracts all video URLs from the playlist
        2. Processes each video in sequence
        3. Organizes slides by video

        Returns:
            Boolean indicating success or failure
        """
        if self.stop_requested:
            return False

        # Extract videos from playlist
        video_urls = self.extract_playlist_videos(self.video_url)

        if not video_urls:
            if self.callback:
                self.callback("No videos found in playlist or error occurred")
            return False

        # Track overall success
        overall_success = True
        total_slides = 0

        # Process each video
        for i, video_url in enumerate(video_urls):
            if self.stop_requested:
                break

            # Create a subdirectory for this video
            video_id = urllib.parse.parse_qs(urllib.parse.urlparse(video_url).query).get('v', ['unknown'])[0]
            video_dir = os.path.join(self.output_dir, f"video_{i+1}_{video_id}")
            os.makedirs(video_dir, exist_ok=True)

            if self.callback:
                self.callback(f"Processing video {i+1}/{len(video_urls)}: {video_url}")

            # Create a new extractor for this video
            video_extractor = SlideExtractor(
                video_url=video_url,
                output_dir=video_dir,
                interval=self.interval,
                similarity_threshold=self.similarity_threshold,
                ocr_confidence=self.ocr_confidence,
                resize_factor=self.resize_factor,
                histogram_threshold=self.histogram_threshold,
                use_multiprocessing=self.use_multiprocessing,
                callback=self.callback,
                adaptive_sampling=self.adaptive_sampling,
                enhance_quality=self.enhance_quality,
                extract_content=self.extract_content,
                organize_slides=self.organize_slides,
                min_scene_length=self.min_scene_length,
                max_scene_length=self.max_scene_length,
                ignore_human_movement=self.ignore_human_movement
            )

            # Extract slides from this video
            success = video_extractor.extract_slides()

            if success:
                # Count slides from this video
                video_slides = len([f for f in os.listdir(video_dir) if f.lower().endswith('.png') and f.startswith('slide_')])
                total_slides += video_slides

                if self.callback:
                    self.callback(f"Extracted {video_slides} slides from video {i+1}")
            else:
                if self.callback:
                    self.callback(f"Failed to extract slides from video {i+1}")
                overall_success = False

        # Create a master index.html that links to all video subdirectories
        if overall_success and total_slides > 0:
            self._create_playlist_index()

        if self.callback:
            self.callback(f"Playlist processing complete. Extracted {total_slides} slides from {len(video_urls)} videos.")

        return overall_success

    def _create_playlist_index(self):
        """Create a master index.html that links to all video subdirectories"""
        try:
            # Find all video directories
            video_dirs = [d for d in os.listdir(self.output_dir)
                         if os.path.isdir(os.path.join(self.output_dir, d)) and d.startswith("video_")]

            if not video_dirs:
                return

            # Sort by video number
            video_dirs.sort(key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 999)

            # Create the index HTML
            index_path = os.path.join(self.output_dir, "playlist_index.html")

            with open(index_path, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Playlist Slides</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .video-list { list-style-type: none; padding: 0; }
        .video-item { margin-bottom: 15px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }
        .video-item a { color: #1a73e8; text-decoration: none; font-weight: bold; }
        .video-item a:hover { text-decoration: underline; }
        .video-info { color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>YouTube Playlist Slides</h1>
        <p>Select a video to view its extracted slides:</p>
        <ul class="video-list">
""")

                # Add links to each video's slides
                for video_dir in video_dirs:
                    video_path = os.path.join(self.output_dir, video_dir)
                    slide_index = os.path.join(video_path, "slide_index.html")
                    slide_count = len([f for f in os.listdir(video_path) if f.lower().endswith('.png') and f.startswith('slide_')])

                    video_id = video_dir.split('_')[-1]
                    video_num = video_dir.split('_')[1]

                    # Check if the slide index exists
                    if os.path.exists(slide_index):
                        f.write(f"""
            <li class="video-item">
                <a href="{video_dir}/slide_index.html">Video {video_num}</a>
                <div class="video-info">{slide_count} slides extracted | ID: {video_id}</div>
            </li>
""")
                    else:
                        f.write(f"""
            <li class="video-item">
                <span>Video {video_num}</span>
                <div class="video-info">{slide_count} slides extracted | ID: {video_id} | No index available</div>
            </li>
""")

                f.write("""
        </ul>
    </div>
</body>
</html>
""")

            logger.info(f"Created playlist index at {index_path}")
            return index_path

        except Exception as e:
            logger.error(f"Error creating playlist index: {e}")
            return None

    def extract_slides(self):
        """
        Process the video to extract slides with advanced features.

        This method handles the entire slide extraction process, including:
        1. Video download
        2. Scene detection (if adaptive_sampling is enabled)
        3. Frame extraction and analysis
        4. Slide identification and saving
        5. Content extraction and organization (if enabled)
        """
        if self.stop_requested:
            return False

        # Check if this is a playlist
        if self.is_playlist_url(self.video_url):
            if self.callback:
                self.callback("Detected YouTube playlist. Processing all videos...")
            return self.extract_slides_from_playlist()

        # Start time for timeout tracking
        start_time = time.time()
        max_processing_time = 3600  # 1 hour maximum processing time

        # Set up more frequent progress updates
        last_progress_update = time.time()
        progress_update_interval = 5  # Update every 5 seconds

        if not os.path.exists(self.video_path):
            if self.callback:
                self.callback("Downloading video - this may take a few minutes...")
            if not self.download_video():
                return False

        if self.callback:
            self.callback("Analyzing video...")

        # Open video file
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        logger.info(f"Video duration: {timedelta(seconds=duration)}")
        logger.info(f"FPS: {fps}, Total frames: {total_frames}")

        if self.callback:
            self.callback(f"Video duration: {timedelta(seconds=duration)}")
            self.callback(f"Starting frame analysis - this may take several minutes for long videos")

        # Determine frames to process
        if self.adaptive_sampling:
            # Use scene detection for adaptive sampling
            if self.callback:
                self.callback("Detecting scene changes for adaptive sampling...")
            scene_boundaries = self.detect_scenes(cap, fps, total_frames)
            frame_numbers = self._get_adaptive_frame_numbers(scene_boundaries, fps, total_frames)
            if self.callback:
                self.callback(f"Found {len(scene_boundaries)} scene changes, will process {len(frame_numbers)} frames")
        else:
            # Use fixed interval sampling
            frame_interval = int(fps * self.interval)
            frame_numbers = list(range(0, total_frames, frame_interval))
            if self.callback:
                self.callback(f"Using fixed interval sampling, will process {len(frame_numbers)} frames")

        total_frames_to_process = len(frame_numbers)
        logger.info(f"Processing {total_frames_to_process} frames")

        if self.callback:
            self.callback(f"Processing {total_frames_to_process} frames...")

        # Close the video capture before parallel processing to avoid threading issues
        cap.release()

        # Extract frames in parallel or sequentially
        frames_data = []

        if self.use_multiprocessing and total_frames_to_process > 10:
            # Use multiprocessing for large videos, but with a smaller number of workers
            # to avoid overwhelming the video decoder
            max_workers = min(multiprocessing.cpu_count(), 4)  # Limit to 4 workers max
            logger.info(f"Using parallel processing with {max_workers} workers")

            if self.callback:
                self.callback(f"Processing frames using {max_workers} parallel workers - this may take a while")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []

                # Submit tasks to extract frames
                for i, frame_num in enumerate(frame_numbers):
                    if self.stop_requested:
                        break

                    # Check for timeout
                    current_time = time.time()
                    if current_time - start_time > max_processing_time:
                        logger.warning("Processing timeout reached, stopping extraction")
                        if self.callback:
                            self.callback("Processing is taking too long, stopping extraction")
                        self.stop_requested = True
                        break

                    # Update progress more frequently
                    if self.callback and current_time - last_progress_update > progress_update_interval:
                        progress_percent = min(100, (i / total_frames_to_process) * 100)
                        self.callback(f"Processing frames: {i}/{total_frames_to_process} ({progress_percent:.1f}%)")
                        last_progress_update = current_time

                    # We don't pass the cap object anymore - each worker creates its own
                    futures.append(executor.submit(
                        self._extract_frame_data, None, frame_num, fps, i, total_frames_to_process
                    ))

                # Collect results as they complete
                completed = 0
                for future in futures:
                    if self.stop_requested:
                        break

                    # Check for timeout
                    current_time = time.time()
                    if current_time - start_time > max_processing_time:
                        logger.warning("Processing timeout reached, stopping extraction")
                        if self.callback:
                            self.callback("Processing is taking too long, stopping extraction")
                        self.stop_requested = True
                        break

                    result = future.result()
                    if result:
                        frames_data.append(result)

                    # Update progress for completed frames
                    completed += 1
                    if self.callback and current_time - last_progress_update > progress_update_interval:
                        progress_percent = min(100, (completed / total_frames_to_process) * 100)
                        self.callback(f"Processed {completed}/{total_frames_to_process} frames ({progress_percent:.1f}%)")
                        last_progress_update = current_time
        else:
            # Sequential processing for smaller videos
            logger.info("Using sequential frame processing")
            if self.callback:
                self.callback("Processing frames sequentially - this may take a while")

            for i, frame_num in enumerate(frame_numbers):
                if self.stop_requested:
                    break

                # Check for timeout
                current_time = time.time()
                if current_time - start_time > max_processing_time:
                    logger.warning("Processing timeout reached, stopping extraction")
                    if self.callback:
                        self.callback("Processing is taking too long, stopping extraction")
                    self.stop_requested = True
                    break

                # Update progress more frequently
                if self.callback and current_time - last_progress_update > progress_update_interval:
                    progress_percent = min(100, (i / total_frames_to_process) * 100)
                    self.callback(f"Processing frames: {i}/{total_frames_to_process} ({progress_percent:.1f}%)")
                    last_progress_update = current_time

                result = self._extract_frame_data(None, frame_num, fps, i, total_frames_to_process)
                if result:
                    frames_data.append(result)

        if self.stop_requested:
            return False

        # Sort frames by their original order
        frames_data.sort(key=lambda x: x['index'])

        # Process frames to find unique slides
        if self.callback:
            self.callback("Identifying unique slides...")

        slide_count = 0
        prev_frame = None
        slide_paths = []
        slide_hashes = []  # Store perceptual hashes for post-processing

        for data in frames_data:
            if self.stop_requested:
                break

            frame = data['frame']
            timestamp = data['timestamp']
            frame_num = data.get('frame_num', 0)

            if prev_frame is None:
                slide_path = self._save_slide(frame, timestamp, slide_count, frame_num)
                slide_paths.append(slide_path)
                # Store hash for later duplicate detection
                slide_hashes.append(self._compute_perceptual_hash(frame))
                prev_frame = frame
                slide_count += 1
                continue

            if self._is_different_slide(prev_frame, frame):
                slide_path = self._save_slide(frame, timestamp, slide_count, frame_num)
                slide_paths.append(slide_path)
                # Store hash for later duplicate detection
                slide_hashes.append(self._compute_perceptual_hash(frame))
                prev_frame = frame
                slide_count += 1

            if self.callback and slide_count % 5 == 0:
                progress = f"Found {slide_count} unique slides so far..."
                self.callback(progress)

        # Post-process to remove duplicate slides that might have been missed
        if slide_count > 0 and not self.stop_requested:
            if self.callback:
                self.callback("Post-processing slides to remove duplicates...")

            # Find and remove duplicates
            unique_slide_paths = self._remove_duplicate_slides(slide_paths, slide_hashes)

            if len(unique_slide_paths) < len(slide_paths):
                if self.callback:
                    self.callback(f"Removed {len(slide_paths) - len(unique_slide_paths)} duplicate slides")
                slide_paths = unique_slide_paths

            # Process extracted slides if requested
            if self.extract_content:
                self._extract_slide_content(slide_paths)

            if self.organize_slides:
                self._organize_slides_by_content(slide_paths)

        # Clean up temp files
        self._cleanup_temp_files()

        # Get the actual number of slides (may be less than slide_count if duplicates were removed)
        final_slide_count = len([f for f in os.listdir(self.output_dir) if f.lower().endswith('.png') and f.startswith('slide_')])

        result_message = f"Extracted {final_slide_count} unique slides to {self.output_dir}"
        logger.info(result_message)

        if self.callback:
            self.callback(result_message)

        return True

    def _extract_frame_data(self, cap, frame_num, fps, index, total):
        """
        Extract a single frame and its metadata with enhanced processing.

        Args:
            cap: OpenCV video capture object (not used, each worker creates its own)
            frame_num: Frame number to extract
            fps: Frames per second of the video
            index: Index of this frame in the processing sequence
            total: Total number of frames to process

        Returns:
            Dictionary containing frame data and metadata
        """
        # Calculate timestamp without needing to access the video
        current_time = frame_num / fps
        timestamp = str(timedelta(seconds=current_time)).split(".")[0]

        # Report progress more frequently (every 5% instead of 10%)
        if self.callback and index % max(1, total // 20) == 0:
            progress = f"Processing frame {index + 1}/{total} ({(index + 1) / total * 100:.1f}%)"
            self.callback(progress)

        # Extract frame - with retry mechanism for robustness
        frame = self._safe_extract_frame(frame_num)

        if frame is None:
            return None

        # Apply image enhancement if enabled
        if self.enhance_quality:
            frame = self._enhance_image_quality(frame)

        return {
            'frame': frame,
            'timestamp': timestamp,
            'index': index,
            'frame_num': frame_num,
            'time_seconds': current_time
        }

    def _safe_extract_frame(self, frame_num, max_retries=3):
        """
        Safely extract a frame with retry mechanism to handle FFmpeg threading issues.

        Args:
            frame_num: Frame number to extract
            max_retries: Maximum number of retry attempts

        Returns:
            Extracted frame or None if failed
        """
        # Use a separate capture object for each frame to avoid threading issues
        try:
            # Create a new capture for this extraction
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video file for frame {frame_num}")
                return None

            # Set position and read frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()

            # Close capture immediately
            cap.release()

            if ret:
                # Human detection feature has been removed
                return frame

            # If failed, try alternative approach
            if max_retries > 0:
                logger.warning(f"Failed to extract frame {frame_num}, retrying with alternative method")
                return self._extract_frame_alternative(frame_num, max_retries - 1)

            return None

        except Exception as e:
            logger.error(f"Error extracting frame {frame_num}: {e}")
            if max_retries > 0:
                logger.warning(f"Retrying frame {frame_num}")
                return self._safe_extract_frame(frame_num, max_retries - 1)
            return None

    def _extract_frame_alternative(self, frame_num, max_retries=1):
        """
        Alternative method to extract a frame using ffmpeg directly.
        Used as a fallback when OpenCV fails.

        Args:
            frame_num: Frame number to extract
            max_retries: Maximum number of retry attempts

        Returns:
            Extracted frame or None if failed
        """
        try:
            # Create a temporary file for the extracted frame
            temp_frame_path = os.path.join(self.temp_dir, f"temp_frame_{frame_num}.png")

            # Calculate timestamp for ffmpeg
            fps = 30.0  # Default assumption if we can't get it from the video
            try:
                cap = cv2.VideoCapture(self.video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()
            except:
                pass

            timestamp = frame_num / fps

            # Use ffmpeg to extract the frame directly
            command = [
                "ffmpeg",
                "-ss", str(timestamp),
                "-i", self.video_path,
                "-vframes", "1",
                "-q:v", "2",
                temp_frame_path,
                "-y"  # Overwrite if exists
            ]

            # Run ffmpeg
            try:
                subprocess.run(command, capture_output=True, check=True)

                # Read the extracted frame
                if os.path.exists(temp_frame_path):
                    frame = cv2.imread(temp_frame_path)
                    os.remove(temp_frame_path)  # Clean up
                    return frame
            except:
                # If ffmpeg fails, try one more approach with OpenCV
                if max_retries > 0:
                    # Try reading the entire video up to this frame
                    cap = cv2.VideoCapture(self.video_path)
                    current_frame = 0
                    while current_frame < frame_num:
                        ret = cap.grab()  # Just grab frames without decoding
                        if not ret:
                            break
                        current_frame += 1

                    # Now read the frame we want
                    ret, frame = cap.read()
                    cap.release()

                    if ret:
                        return frame

            return None

        except Exception as e:
            logger.error(f"Alternative frame extraction failed for frame {frame_num}: {e}")
            return None

    def _enhance_image_quality(self, frame):
        """
        Enhance image quality for better slide extraction.

        This method applies various image processing techniques to improve
        the quality and readability of slides.

        Args:
            frame: Input frame to enhance

        Returns:
            Enhanced frame
        """
        # Convert to PIL Image for enhancement
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)

        # Apply a series of enhancements
        try:
            # Sharpen the image
            enhancer = ImageEnhance.Sharpness(pil_img)
            pil_img = enhancer.enhance(1.5)

            # Increase contrast slightly
            enhancer = ImageEnhance.Contrast(pil_img)
            pil_img = enhancer.enhance(1.2)

            # Convert back to OpenCV format
            enhanced_frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return enhanced_frame
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return frame  # Return original frame if enhancement fails

    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            temp_ocr_path = os.path.join(self.temp_dir, "temp_ocr.png")
            if os.path.exists(temp_ocr_path):
                os.remove(temp_ocr_path)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")

    def _is_different_slide(self, frame1, frame2):
        """
        Determine if two frames represent different slides using a multi-stage approach:
        1. Perceptual hash comparison (very fast, robust to minor variations)
        2. Quick histogram comparison (fast)
        3. Structural similarity comparison (medium)
        4. OCR text comparison (slow, only if needed)

        Enhanced to be robust against human movements by focusing on the central content
        region of slides and using very aggressive thresholds to ignore minor changes.
        """
        try:
            # Process frames to ignore human regions if enabled
            if self.ignore_human_movement and self.yolo_model is not None:
                # Detect humans in both frames
                human_boxes1 = self._detect_humans(frame1)
                human_boxes2 = self._detect_humans(frame2)

                # Even more improved approach: Focus on a very central region of the slide
                # and completely ignore human detection in this comparison
                h1, w1 = frame1.shape[:2]
                h2, w2 = frame2.shape[:2]

                # Define a smaller central region (60% of the frame) to focus on the most important content
                margin_x1 = int(w1 * 0.2)  # 20% margin on each side
                margin_y1 = int(h1 * 0.2)
                margin_x2 = int(w2 * 0.2)
                margin_y2 = int(h2 * 0.2)

                # Extract central regions only
                masked_frame1 = frame1[margin_y1:h1-margin_y1, margin_x1:w1-margin_x1].copy()
                masked_frame2 = frame2[margin_y2:h2-margin_y2, margin_x2:w2-margin_x2].copy()

                # Completely ignore human detection for slide change detection
                # This is a radical approach but should be more effective for lecture videos
                # where the teacher's movements shouldn't trigger slide changes

                # Log human detection results
                if human_boxes1 or human_boxes2:
                    logger.info(f"Detected {len(human_boxes1)} humans in frame1 and {len(human_boxes2)} humans in frame2")

                # Use masked frames for comparison
                comparison_frame1 = masked_frame1
                comparison_frame2 = masked_frame2

                # Use these masked frames for perceptual hash comparison
                hash1 = self._compute_perceptual_hash(masked_frame1)
                hash2 = self._compute_perceptual_hash(masked_frame2)
            else:
                # Use the entire frames if not ignoring human movement
                comparison_frame1 = frame1
                comparison_frame2 = frame2
                hash1 = self._compute_perceptual_hash(frame1)
                hash2 = self._compute_perceptual_hash(frame2)

            hash_diff = self._hamming_distance(hash1, hash2)

            # If hashes are very similar, it's definitely the same slide
            # This is robust against minor variations from blurring or human movement
            if hash_diff < 20:  # Much more tolerant of minor variations
                return False

            # If hashes are very different, it's definitely a different slide
            if hash_diff > 25:  # Higher threshold to be more strict about differences
                return True

            # Resize frames for faster processing
            if self.resize_factor != 1.0:
                h1, w1 = comparison_frame1.shape[:2]
                h2, w2 = comparison_frame2.shape[:2]
                frame1_small = cv2.resize(comparison_frame1, (int(w1 * self.resize_factor), int(h1 * self.resize_factor)))
                frame2_small = cv2.resize(comparison_frame2, (int(w2 * self.resize_factor), int(h2 * self.resize_factor)))
            else:
                frame1_small = comparison_frame1
                frame2_small = comparison_frame2

            # Stage 1: Quick histogram comparison
            hist_diff = self._histogram_difference(frame1_small, frame2_small)

            # Use a much more aggressive histogram threshold
            effective_hist_threshold = self.histogram_threshold

            if hist_diff > effective_hist_threshold:
                # Double-check with structural similarity for borderline cases
                if hist_diff < effective_hist_threshold + 0.25:  # Much wider borderline range
                    # Convert to grayscale for SSIM
                    gray1 = cv2.cvtColor(frame1_small, cv2.COLOR_BGR2GRAY)
                    gray2 = cv2.cvtColor(frame2_small, cv2.COLOR_BGR2GRAY)
                    similarity, _ = ssim(gray1, gray2, full=True)

                    # If similarity is high despite histogram difference, consider it the same slide
                    if similarity > self.similarity_threshold - 0.15:  # Much more tolerant threshold
                        return False
                return True

            # Stage 2: Structural similarity comparison
            gray1 = cv2.cvtColor(frame1_small, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2_small, cv2.COLOR_BGR2GRAY)

            similarity, _ = ssim(gray1, gray2, full=True)

            # If similarity is very low, it's definitely a different slide
            if similarity < self.similarity_threshold - 0.2:  # Much less lenient threshold
                return True

            # If similarity is very high, it's definitely the same slide
            if similarity > self.similarity_threshold - 0.1:  # Much more aggressive threshold
                return False

            # Stage 3: OCR text comparison (only for borderline cases)
            # If we're ignoring human movement, extract text from the central region
            if self.ignore_human_movement:
                # Extract the central region for OCR
                h1, w1 = comparison_frame1.shape[:2]
                h2, w2 = comparison_frame2.shape[:2]

                margin_x1 = int(w1 * 0.2)
                margin_y1 = int(h1 * 0.2)
                margin_x2 = int(w2 * 0.2)
                margin_y2 = int(h2 * 0.2)

                center_frame1 = comparison_frame1[margin_y1:h1-margin_y1, margin_x1:w1-margin_x1]
                center_frame2 = comparison_frame2[margin_y2:h2-margin_y2, margin_x2:w2-margin_x2]

                text1 = self._extract_text(center_frame1)
                text2 = self._extract_text(center_frame2)
            else:
                text1 = self._extract_text(comparison_frame1)
                text2 = self._extract_text(comparison_frame2)

            if text1 and text2:
                words1 = set(text1.split())
                words2 = set(text2.split())

                # If either slide has very few words, use similarity score
                if len(words1) < 3 or len(words2) < 3:
                    return similarity < self.similarity_threshold

                common_words = words1.intersection(words2)
                total_words = max(len(words1), len(words2))

                # Avoid division by zero
                if total_words == 0:
                    return similarity < self.similarity_threshold

                diff_ratio = 1 - len(common_words) / total_words

                # Much more aggressive text difference threshold
                text_diff_threshold = 0.7  # Significantly increased to be much more tolerant of text differences

                if diff_ratio > text_diff_threshold:
                    return True

            # Default to using the similarity threshold
            return similarity < self.similarity_threshold

        except Exception as e:
            # If comparison fails, log the error and assume they're different
            logger.error(f"Error comparing slides: {e}")
            return True

    def _histogram_difference(self, img1, img2):
        """Calculate histogram difference between two images (faster than SSIM)"""
        hist1 = cv2.calcHist([img1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([img2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

        # Normalize histograms
        cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

        # Calculate difference
        diff = cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)
        return diff

    def _compute_frame_hash(self, frame):
        """
        Compute a hash for a frame to use as a cache key.
        This creates a perceptual hash that's resistant to small changes.
        """
        try:
            # Resize to a small size for faster hashing
            small_frame = cv2.resize(frame, (32, 32))
            # Convert to grayscale
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            # Compute mean value
            mean_val = gray.mean()
            # Create binary hash
            hash_val = 0
            for i in range(32):
                for j in range(32):
                    if gray[i, j] > mean_val:
                        hash_val = hash_val * 2 + 1
                    else:
                        hash_val = hash_val * 2
            return hash_val
        except Exception as e:
            logger.error(f"Error computing frame hash: {e}")
            # Return a unique value to avoid cache collisions
            return id(frame)

    def _compute_perceptual_hash(self, frame):
        """
        Compute a perceptual hash (pHash) for a frame.
        This is more robust against variations caused by different types of blurring or human removal.

        Returns:
            64-bit perceptual hash as a binary string
        """
        try:
            # Resize to 32x32
            small_frame = cv2.resize(frame, (32, 32))
            # Convert to grayscale
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            # Resize to 8x8
            tiny = cv2.resize(gray, (8, 8))
            # Compute DCT (Discrete Cosine Transform)
            dct = cv2.dct(np.float32(tiny))
            # Take the top-left 8x8 of DCT coefficients
            dct_low = dct[:8, :8]
            # Compute the median value
            med = np.median(dct_low)
            # Create binary hash
            hash_str = ''
            for i in range(8):
                for j in range(8):
                    if dct_low[i, j] > med:
                        hash_str += '1'
                    else:
                        hash_str += '0'
            return hash_str
        except Exception as e:
            logger.error(f"Error computing perceptual hash: {e}")
            # Return a unique hash to avoid collisions
            return ''.join(['1' if random.random() > 0.5 else '0' for _ in range(64)])

    def _hamming_distance(self, hash1, hash2):
        """
        Calculate the Hamming distance between two hash strings.
        This counts the number of positions at which the corresponding bits are different.

        Returns:
            Integer representing the number of differing bits
        """
        try:
            # Ensure both hashes are the same length
            min_len = min(len(hash1), len(hash2))
            hash1 = hash1[:min_len]
            hash2 = hash2[:min_len]

            # Count differing bits
            return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        except Exception as e:
            logger.error(f"Error calculating Hamming distance: {e}")
            return 64  # Maximum possible distance for 64-bit hash

    def _extract_text(self, frame):
        """Extract text from a frame using enhanced OCR with preprocessing and validation"""
        try:
            # Compute a hash for the frame to use as a cache key
            frame_hash = self._compute_frame_hash(frame)

            # Check if we have this frame in the cache
            if frame_hash in self.ocr_cache:
                return self.ocr_cache[frame_hash]

            # Enhanced preprocessing for better OCR results
            # 1. Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 2. Apply adaptive thresholding for better text extraction
            # This works better than simple thresholding for varying lighting conditions
            adaptive_threshold = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # 3. Apply morphological operations to clean up the image
            # Create a kernel for morphological operations
            kernel = np.ones((1, 1), np.uint8)
            # Dilate to enhance text
            dilated = cv2.dilate(adaptive_threshold, kernel, iterations=1)
            # Erode to remove noise
            eroded = cv2.erode(dilated, kernel, iterations=1)

            # 4. Apply noise reduction
            denoised = cv2.fastNlMeansDenoising(eroded, None, 10, 7, 21)

            # 5. Increase contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # Convert to PIL Image for OCR
            pil_img = Image.fromarray(enhanced)

            # Try multiple OCR configurations for better results
            # First try with page segmentation mode 6 (assume a single uniform block of text)
            text1 = pytesseract.image_to_string(pil_img, config='--psm 6 --oem 3')

            # Then try with page segmentation mode 3 (fully automatic page segmentation)
            text2 = pytesseract.image_to_string(pil_img, config='--psm 3 --oem 3')

            # Choose the result with more valid words
            text1_words = len([w for w in text1.split() if len(w) > 2])
            text2_words = len([w for w in text2.split() if len(w) > 2])

            result = text1 if text1_words >= text2_words else text2
            result = result.strip()

            # Validate OCR result - if it looks like gibberish, try another approach
            valid_word_ratio = self._validate_ocr_text(result)

            # If the result seems poor, try with the original image
            if valid_word_ratio < 0.3 and len(result) > 0:
                # Try with the original image
                text3 = pytesseract.image_to_string(Image.fromarray(gray), config='--psm 1 --oem 3')

                # Check if this result is better
                if self._validate_ocr_text(text3) > valid_word_ratio:
                    result = text3.strip()

            # Cache the result
            self.ocr_cache[frame_hash] = result

            return result
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return ""

    def _validate_ocr_text(self, text):
        """Validate OCR text to detect gibberish

        Returns:
            Float between 0 and 1 indicating the ratio of valid words
        """
        if not text:
            return 0

        # Split into words
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())

        if not words:
            return 0

        # Common English words to check against
        common_words = {
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

        # Count words that are in our common word list
        valid_words = sum(1 for word in words if word in common_words)

        # Check for common patterns in educational content
        if re.search(r'fig(ure)?\.?\s*\d+', text, re.IGNORECASE) or \
           re.search(r'eq(uation)?\.?\s*\d+', text, re.IGNORECASE) or \
           re.search(r'table\s*\d+', text, re.IGNORECASE) or \
           re.search(r'chapter\s*\d+', text, re.IGNORECASE) or \
           re.search(r'section\s*\d+', text, re.IGNORECASE):
            # Boost the score if we find educational patterns
            valid_words += 2

        # Return ratio of valid words to total words
        return valid_words / len(words) if words else 0

    def _save_slide(self, frame, timestamp, count, frame_num=0):
        """
        Save a slide as a PNG image with metadata.

        Args:
            frame: The image frame to save
            timestamp: Video timestamp for the slide
            count: Slide counter (for filename)
            frame_num: Frame number in the video

        Returns:
            Path to the saved slide
        """
        filename = f"slide_{count:03d}_{timestamp.replace(':', '-')}.png"
        path = os.path.join(self.output_dir, filename)

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create PIL image
        pil_image = Image.fromarray(rgb_frame)

        # Save with compression to reduce file size
        pil_image.save(path, optimize=True, quality=95)

        # Create metadata for this slide
        metadata = {
            'filename': filename,
            'path': path,
            'timestamp': timestamp,
            'frame_number': frame_num,
            'index': count,
            'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Save metadata
        self.slides_metadata[filename] = metadata

        logger.info(f"Saved slide: {filename}")

        if self.callback:
            self.callback(f"Saved slide: {filename}")

        return path

    def _extract_slide_content(self, slide_paths):
        """
        Extract and index content from slides.

        This method performs OCR on each slide to extract text content,
        identifies key elements, and builds a searchable index.

        Args:
            slide_paths: List of paths to slide images
        """
        if not slide_paths:
            return

        if self.callback:
            self.callback("Extracting content from slides...")

        logger.info(f"Extracting content from {len(slide_paths)} slides")

        # Process each slide
        for i, path in enumerate(slide_paths):
            if self.stop_requested:
                break

            try:
                # Get filename from path
                filename = os.path.basename(path)

                # Skip if we've already processed this slide
                if filename in self.slides_metadata and 'content' in self.slides_metadata[filename]:
                    continue

                # Open the image
                image = Image.open(path)

                # Extract text using OCR
                text = pytesseract.image_to_string(image, config='--psm 6')

                # Extract potential title (first line or large text)
                title = self._extract_title(image, text)

                # Classify slide type
                slide_type = self._classify_slide_type(image, text)

                # Extract keywords
                keywords = self._extract_keywords(text)

                # Update metadata
                if filename in self.slides_metadata:
                    self.slides_metadata[filename].update({
                        'content': text,
                        'title': title,
                        'type': slide_type,
                        'keywords': keywords
                    })

                    # Add to content index
                    for keyword in keywords:
                        self.slide_content_index[keyword].append(filename)

                # Report progress
                if self.callback and (i + 1) % 5 == 0:
                    self.callback(f"Processed content for {i + 1}/{len(slide_paths)} slides")

            except Exception as e:
                logger.error(f"Error extracting content from {path}: {e}")

        # Save content index and metadata
        self._save_metadata()

        logger.info("Content extraction complete")
        if self.callback:
            self.callback("Content extraction complete")

    def _extract_title(self, image, text):
        """Extract the title from a slide"""
        if not text:
            return ""

        # Simple approach: use the first line as title
        lines = text.strip().split('\n')
        if lines:
            return lines[0].strip()
        return ""

    def _classify_slide_type(self, image, text):
        """
        Classify the type of slide based on content and layout.

        This is a simple heuristic-based classifier. For production use,
        this could be replaced with a machine learning model.
        """
        if not text:
            # No text might indicate an image-heavy slide
            return 'image'

        text_lower = text.lower()

        # Check for title slides
        if len(text.strip().split('\n')) <= 2 and len(text) < 100:
            title_indicators = ['agenda', 'outline', 'contents', 'introduction',
                               'overview', 'summary', 'conclusion', 'thank you']
            for indicator in title_indicators:
                if indicator in text_lower:
                    return 'title'

        # Check for code slides
        code_indicators = ['def ', 'class ', 'function', 'import ', 'var ', 'const ',
                          'return ', 'if (', 'for (', 'while (', '{', '}', '();']
        code_count = sum(1 for indicator in code_indicators if indicator in text)
        if code_count >= 3:
            return 'code'

        # Check for table slides
        if text.count('|') > 5 or text.count('\t') > 5:
            return 'table'

        # Default to content slide
        return 'content'

    def _extract_keywords(self, text):
        """Extract important keywords from slide text"""
        if not text:
            return []

        # Simple keyword extraction based on word frequency
        # In a production system, this could use NLP techniques like TF-IDF
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter out common stop words
        stop_words = {'and', 'the', 'for', 'with', 'this', 'that', 'from', 'have', 'not'}
        filtered_words = [word for word in words if word not in stop_words]

        # Count word frequency
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Get top keywords
        keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in keywords[:10]]  # Return top 10 keywords

    def _remove_duplicate_slides(self, slide_paths, slide_hashes):
        """
        Post-process slides to remove duplicates that might have been missed during extraction.
        Uses perceptual hashing to identify similar slides even with minor variations.

        Args:
            slide_paths: List of paths to slide images
            slide_hashes: List of perceptual hashes corresponding to each slide

        Returns:
            List of unique slide paths after removing duplicates
        """
        if not slide_paths or len(slide_paths) <= 1:
            return slide_paths

        logger.info(f"Post-processing {len(slide_paths)} slides to remove duplicates")

        # Create a list of (path, hash) tuples
        slides_with_hashes = list(zip(slide_paths, slide_hashes))

        # Sort by timestamp (which is encoded in the filename)
        slides_with_hashes.sort(key=lambda x: os.path.basename(x[0]))

        # List to store unique slides
        unique_slides = []
        removed_slides = []

        # First slide is always kept
        unique_slides.append(slides_with_hashes[0][0])

        # Compare each slide with all previous unique slides
        for i in range(1, len(slides_with_hashes)):
            current_path, current_hash = slides_with_hashes[i]
            is_duplicate = False

            # Compare with previous unique slides
            for unique_path, unique_hash in zip(unique_slides, [h for p, h in slides_with_hashes if p in unique_slides]):
                # Calculate hash difference
                hash_diff = self._hamming_distance(current_hash, unique_hash)

                # If hashes are very similar, consider it a duplicate
                if hash_diff < 25:  # Much more aggressive duplicate detection
                    is_duplicate = True
                    removed_slides.append((current_path, unique_path))
                    break

                # For borderline cases, load the images and compare them directly
                if 25 <= hash_diff <= 35:
                    try:
                        # Load images
                        img1 = cv2.imread(current_path)
                        img2 = cv2.imread(unique_path)

                        if img1 is not None and img2 is not None:
                            # Resize to same dimensions for comparison
                            h1, w1 = img1.shape[:2]
                            img2 = cv2.resize(img2, (w1, h1))

                            # Compare using structural similarity
                            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
                            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
                            similarity, _ = ssim(gray1, gray2, full=True)

                            if similarity > self.similarity_threshold - 0.15:  # Much more aggressive similarity threshold
                                is_duplicate = True
                                removed_slides.append((current_path, unique_path))
                                break
                    except Exception as e:
                        logger.error(f"Error comparing images for duplicate detection: {e}")

            # If not a duplicate, add to unique slides
            if not is_duplicate:
                unique_slides.append(current_path)

        # Log removed duplicates
        if removed_slides:
            logger.info(f"Removed {len(removed_slides)} duplicate slides")
            for removed, kept in removed_slides:
                logger.debug(f"Removed duplicate: {os.path.basename(removed)} (duplicate of {os.path.basename(kept)})")

                # Remove the file if it exists
                try:
                    if os.path.exists(removed):
                        os.remove(removed)
                        # Also remove from metadata
                        removed_filename = os.path.basename(removed)
                        if removed_filename in self.slides_metadata:
                            del self.slides_metadata[removed_filename]
                except Exception as e:
                    logger.error(f"Error removing duplicate slide file: {e}")

        return unique_slides

    def _organize_slides_by_content(self, slide_paths):
        """
        Organize slides into categories based on content.

        This method creates a structured organization of slides based on
        their content, type, and relationships.
        """
        if not slide_paths or not self.slides_metadata:
            return

        if self.callback:
            self.callback("Organizing slides by content...")

        # Create organized directory if it doesn't exist
        os.makedirs(self.organized_dir, exist_ok=True)

        # Group slides by type
        slide_types = {}
        for filename, metadata in self.slides_metadata.items():
            slide_type = metadata.get('type', 'other')
            if slide_type not in slide_types:
                slide_types[slide_type] = []
            slide_types[slide_type].append(metadata)

        # Create directories for each type and copy slides
        for slide_type, slides in slide_types.items():
            type_dir = os.path.join(self.organized_dir, slide_type)
            os.makedirs(type_dir, exist_ok=True)

            # Copy slides to type directory
            for slide_metadata in slides:
                src_path = slide_metadata['path']
                dst_path = os.path.join(type_dir, slide_metadata['filename'])
                try:
                    shutil.copy2(src_path, dst_path)
                except Exception as e:
                    logger.error(f"Error copying {src_path} to {dst_path}: {e}")

        # Create an HTML index for easy browsing
        self._create_html_index()

        logger.info("Slide organization complete")
        if self.callback:
            self.callback("Slides organized by content type")

    def _create_html_index(self):
        """Create an HTML index of all slides for easy browsing"""
        index_path = os.path.join(self.output_dir, "slide_index.html")

        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extracted Slides Index</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; }
        .slide-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
        .slide-card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .slide-card img { width: 100%; height: auto; }
        .slide-info { padding: 15px; }
        .slide-title { font-weight: bold; margin-bottom: 5px; }
        .slide-meta { color: #666; font-size: 0.9em; }
        .slide-type { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 0.8em; margin-top: 5px; }
        .type-title { background: #e3f2fd; color: #0d47a1; }
        .type-content { background: #e8f5e9; color: #1b5e20; }
        .type-code { background: #fffde7; color: #f57f17; }
        .type-image { background: #f3e5f5; color: #6a1b9a; }
        .type-table { background: #e0f2f1; color: #00695c; }
        .type-other { background: #f5f5f5; color: #616161; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Extracted Slides</h1>
        <div class="slide-grid">
""")

                # Add each slide to the index
                for filename, metadata in sorted(self.slides_metadata.items(), key=lambda x: x[1]['index']):
                    slide_type = metadata.get('type', 'other')
                    title = metadata.get('title', 'Untitled Slide')
                    timestamp = metadata.get('timestamp', '')

                    # Create relative path to the image
                    img_path = os.path.relpath(metadata['path'], self.output_dir).replace('\\', '/')

                    f.write(f"""
            <div class="slide-card">
                <img src="{img_path}" alt="{title}">
                <div class="slide-info">
                    <div class="slide-title">{title}</div>
                    <div class="slide-meta">Time: {timestamp}</div>
                    <div class="slide-type type-{slide_type}">{slide_type.capitalize()}</div>
                </div>
            </div>
""")

                f.write("""
        </div>
    </div>
</body>
</html>
""")

            logger.info(f"Created HTML index at {index_path}")
            if self.callback:
                self.callback(f"Created HTML index at {index_path}")

        except Exception as e:
            logger.error(f"Error creating HTML index: {e}")

    def _save_metadata(self):
        """Save slide metadata to a JSON file"""
        metadata_path = os.path.join(self.metadata_dir, "slides_metadata.json")

        try:
            # Convert paths to relative paths for portability
            portable_metadata = {}
            for filename, metadata in self.slides_metadata.items():
                portable_metadata[filename] = metadata.copy()
                if 'path' in portable_metadata[filename]:
                    portable_metadata[filename]['path'] = os.path.relpath(
                        metadata['path'], self.output_dir
                    )

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(portable_metadata, f, indent=2)

            logger.info(f"Saved metadata to {metadata_path}")
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def get_slides(self):
        """
        Get the list of extracted slides with metadata.

        Returns:
            List of slide dictionaries with metadata
        """
        slides = []
        for filename, metadata in self.slides_metadata.items():
            slide_info = {
                'filename': filename,
                'path': metadata.get('path', ''),
                'timestamp': metadata.get('timestamp', ''),
                'content': metadata.get('content', ''),
                'title': metadata.get('title', ''),
                'type': metadata.get('type', 'unknown'),
                'keywords': metadata.get('keywords', []),
                'similarity': metadata.get('similarity', 0.0),
                'frame_number': metadata.get('frame_number', 0)
            }
            slides.append(slide_info)

        return slides

    def get_metadata(self):
        """
        Get metadata for all slides.

        Returns:
            Dictionary of slide metadata
        """
        return self.slides_metadata

    def get_video_path(self):
        """
        Get the path to the downloaded video file.

        Returns:
            String path to video file
        """
        return self.video_path

    def convert_slides_to_pdf(self, pdf_name="slides_output.pdf", batch_size=10,
                           include_toc=True, include_metadata=True, include_timestamps=True,
                           page_numbers=True, quality="high"):
        """
        Convert all extracted slides to a single PDF file with advanced features.

        Args:
            pdf_name: Name of the output PDF file
            batch_size: Number of images to process at once (for memory efficiency)
            include_toc: Whether to include a table of contents
            include_metadata: Whether to include slide metadata
            include_timestamps: Whether to include timestamps on slides
            page_numbers: Whether to include page numbers
            quality: PDF quality ("low", "medium", "high")

        Returns:
            Path to the created PDF file
        """
        if self.callback:
            self.callback("Creating enhanced PDF...")

        logger.info(f"Creating PDF with options: toc={include_toc}, metadata={include_metadata}, "
                   f"timestamps={include_timestamps}, quality={quality}")

        # Get all slide images
        image_files = []

        # If we have metadata, use it to sort slides
        if self.slides_metadata and os.path.exists(self.metadata_dir):
            # Sort by index to maintain order
            sorted_metadata = sorted(self.slides_metadata.items(), key=lambda x: x[1]['index'])
            for filename, metadata in sorted_metadata:
                path = metadata['path']
                if os.path.exists(path) and path.lower().endswith(".png"):
                    image_files.append((path, metadata))
        else:
            # Fall back to directory listing
            image_files = [(
                os.path.join(self.output_dir, file),
                {'filename': file, 'timestamp': '', 'title': f"Slide {i+1}"}
            ) for i, file in enumerate(sorted(
                f for f in os.listdir(self.output_dir)
                if f.lower().endswith(".png") and f.startswith("slide_")
            ))]

        if not image_files:
            message = "No slide images found to convert."
            logger.warning(message)
            if self.callback:
                self.callback(message)
            return None

        pdf_path = os.path.join(self.output_dir, pdf_name)

        # Set quality parameters
        if quality == "low":
            resolution = 72.0
            compress_level = 9
        elif quality == "medium":
            resolution = 150.0
            compress_level = 6
        else:  # high
            resolution = 300.0
            compress_level = 3

        # Create PDF with reportlab for more control
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage
            from reportlab.platypus import TableOfContents, Table, TableStyle

            # Create document
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=letter,
                title=f"Slides from {os.path.basename(self.video_url)}",
                author="YouTube Slide Extractor"
            )

            # Styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            normal_style = styles['Normal']
            toc_style = ParagraphStyle(
                'TOCHeading',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=20
            )

            # Build document content
            content = []

            # Add title page
            content.append(Paragraph("Extracted Slides", title_style))
            content.append(Spacer(1, 0.25*inch))
            content.append(Paragraph(f"Source: {self.video_url}", normal_style))
            content.append(Paragraph(f"Extracted: {time.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            content.append(Paragraph(f"Total Slides: {len(image_files)}", normal_style))
            content.append(PageBreak())

            # Add table of contents if requested
            if include_toc:
                content.append(Paragraph("Table of Contents", toc_style))
                toc = TableOfContents()
                toc.levelStyles = [
                    ParagraphStyle(name='TOC1', fontSize=14, leftIndent=20, firstLineIndent=-20),
                    ParagraphStyle(name='TOC2', fontSize=12, leftIndent=40, firstLineIndent=-20),
                ]
                content.append(toc)
                content.append(PageBreak())

            # Process slides in batches
            total_slides = len(image_files)
            last_progress_percent = -1

            for i, (img_path, metadata) in enumerate(image_files):
                if self.stop_requested:
                    break

                # Calculate progress percentage
                progress_percent = int((i / total_slides) * 100)

                # Update progress more frequently for large slide sets
                if self.callback and (progress_percent > last_progress_percent or i % 5 == 0):
                    last_progress_percent = progress_percent
                    progress = f"Adding slide {i+1}/{total_slides} to PDF... ({progress_percent}%)"
                    self.callback(progress)

                    # Also print to terminal for command-line users
                    if i % 10 == 0 or i == total_slides - 1:
                        print(f"Processing slide {i+1}/{total_slides} ({progress_percent}%)")

                try:
                    # Get slide metadata
                    title = metadata.get('title', f"Slide {i+1}")
                    slide_type = metadata.get('type', 'content')
                    timestamp = metadata.get('timestamp', '')

                    # For playlist slides, try to extract playlist and video info from filename
                    if 'playlist' in os.path.basename(img_path):
                        try:
                            filename = os.path.basename(img_path)
                            parts = filename.split('_')
                            if 'playlist' in parts[0] and 'video' in parts[1]:
                                playlist_num = parts[0].replace('playlist', '')
                                video_num = parts[1].replace('video', '')
                                title = f"Playlist {playlist_num} - Video {video_num} - {title}"
                        except:
                            pass

                    # Add slide title as bookmark
                    if include_toc:
                        content.append(Paragraph(title, title_style))

                    # Add image
                    img = RLImage(img_path, width=7*inch, height=5*inch, kind='proportional')
                    content.append(img)

                    # Add metadata if requested
                    if include_metadata:
                        metadata_table = []
                        if include_timestamps and timestamp:
                            metadata_table.append(["Timestamp:", timestamp])
                        if slide_type:
                            metadata_table.append(["Type:", slide_type.capitalize()])

                        # Add source information for combined PDFs
                        if 'playlist' in os.path.basename(img_path):
                            try:
                                filename = os.path.basename(img_path)
                                parts = filename.split('_')
                                if 'playlist' in parts[0] and 'video' in parts[1]:
                                    playlist_num = parts[0].replace('playlist', '')
                                    video_num = parts[1].replace('video', '')
                                    metadata_table.append(["Source:", f"Playlist {playlist_num}, Video {video_num}"])
                            except:
                                pass

                        if metadata_table:
                            t = Table(metadata_table, colWidths=[1*inch, 6*inch])
                            t.setStyle(TableStyle([
                                ('TEXTCOLOR', (0, 0), (-1, -1), colors.darkblue),
                                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
                                ('FONT', (1, 0), (1, -1), 'Helvetica'),
                                ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ]))
                            content.append(t)

                    # Add page break after each slide except the last one
                    if i < len(image_files) - 1:
                        content.append(PageBreak())

                except Exception as e:
                    error_msg = f"Error adding slide {img_path} to PDF: {e}"
                    logger.error(error_msg)
                    if self.callback:
                        self.callback(f"Warning: {error_msg}")

            # Build the PDF
            doc.build(
                content,
                onFirstPage=self._add_page_number if page_numbers else None,
                onLaterPages=self._add_page_number if page_numbers else None
            )

            result_message = f"Enhanced PDF created at: {pdf_path}"
            logger.info(result_message)

            if self.callback:
                self.callback(result_message)

            return pdf_path

        except ImportError:
            # Fall back to simple PDF creation if reportlab features aren't available
            logger.warning("Advanced PDF features not available. Creating simple PDF.")
            return self._create_simple_pdf(image_files, pdf_path, batch_size)
        except Exception as e:
            logger.error(f"Error creating enhanced PDF: {e}")
            # Fall back to simple PDF creation
            logger.warning("Falling back to simple PDF creation.")
            return self._create_simple_pdf(image_files, pdf_path, batch_size)

    def _add_page_number(self, canvas, doc):
        """Add page number to PDF pages"""
        canvas.saveState()
        canvas.setFont('Helvetica', 10)
        canvas.drawRightString(
            7.5*inch, 0.5*inch, f"Page {doc.page}")
        canvas.restoreState()

    def create_combined_pdf(self, slide_dirs, output_file="combined_slides.pdf", batch_size=10,
                           toc=True, metadata=True, timestamps=True, page_numbers=True, quality="high"):
        """
        Create a combined PDF from multiple slide directories.

        Args:
            slide_dirs: List of directories containing slides
            output_file: Path to the output PDF file
            batch_size: Number of images to process at once
            toc: Whether to include a table of contents
            metadata: Whether to include slide metadata
            timestamps: Whether to include timestamps
            page_numbers: Whether to include page numbers
            quality: PDF quality ("low", "medium", "high")

        Returns:
            Path to the created PDF file
        """
        # Try to create a safer output path if needed
        try:
            # Check if we can write to the output directory
            output_dir = os.path.dirname(output_file)
            if not os.access(output_dir, os.W_OK):
                # Try to use a different directory
                alt_dir = os.path.join(os.path.expanduser("~"), "Documents")
                if not os.path.exists(alt_dir):
                    alt_dir = os.path.expanduser("~")

                base_name = os.path.basename(output_file)
                output_file = os.path.join(alt_dir, f"slides_{base_name}")

                if self.callback:
                    self.callback(f"Changed output location to {output_file} due to permission issues")
                logger.info(f"Changed output location to {output_file} due to permission issues")
        except Exception as e:
            logger.warning(f"Error checking output permissions: {e}")
            # Continue with the original path and handle errors later
        if self.callback:
            self.callback(f"Creating combined PDF from {len(slide_dirs)} directories...")

        logger.info(f"Creating PDF with options: toc={toc}, metadata={metadata}, timestamps={timestamps}, quality={quality}")

        # Collect all slide images from all directories
        all_images = []

        for dir_idx, slide_dir in enumerate(slide_dirs):
            if self.callback:
                self.callback(f"Scanning directory {dir_idx+1}/{len(slide_dirs)}: {os.path.basename(slide_dir)}")

            # Check if directory exists
            if not os.path.exists(slide_dir) or not os.path.isdir(slide_dir):
                logger.warning(f"Directory not found or not a directory: {slide_dir}")
                continue

            # Find all PNG files in this directory
            try:
                slide_files = sorted([
                    f for f in os.listdir(slide_dir)
                    if f.lower().endswith(".png") and f.startswith("slide_")
                ])

                # Extract metadata if available
                metadata_path = os.path.join(slide_dir, "metadata", "slides_metadata.json")
                dir_metadata = {}

                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            dir_metadata = json.load(f)
                    except Exception as e:
                        logger.error(f"Error loading metadata from {metadata_path}: {e}")

                # Add each slide with its metadata
                for slide_idx, slide_file in enumerate(slide_files):
                    slide_path = os.path.join(slide_dir, slide_file)

                    # Get metadata for this slide if available
                    slide_metadata = dir_metadata.get(slide_file, {})
                    if not slide_metadata:
                        # Create basic metadata if not available
                        slide_metadata = {
                            'filename': slide_file,
                            'timestamp': slide_file.split('_')[-1].replace('-', ':').replace('.png', ''),
                            'title': f"Slide {slide_idx+1} from {os.path.basename(slide_dir)}",
                            'index': slide_idx
                        }

                    # Add directory information to metadata
                    slide_metadata['source_dir'] = os.path.basename(slide_dir)

                    # Add to the list of images
                    all_images.append((slide_path, slide_metadata))

                if self.callback and slide_files:
                    self.callback(f"Added {len(slide_files)} slides from {os.path.basename(slide_dir)}")

            except Exception as e:
                logger.error(f"Error processing directory {slide_dir}: {e}")

        # Check if we found any slides
        if not all_images:
            logger.warning("No slide images found to convert.")
            if self.callback:
                self.callback("No slide images found to convert.")
            return None

        # Now create the PDF with all collected images
        if self.callback:
            self.callback(f"Creating PDF with {len(all_images)} slides...")

        # Set quality parameters
        if quality == "low":
            resolution = 72.0
            compress_level = 9
        elif quality == "medium":
            resolution = 150.0
            compress_level = 6
        else:  # high
            resolution = 300.0
            compress_level = 3

        # Create PDF with reportlab for more control
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage
            from reportlab.platypus import TableOfContents, Table, TableStyle

            # Create document
            doc = SimpleDocTemplate(
                output_file,
                pagesize=letter,
                title="Combined Slides",
                author="YouTube Slide Extractor"
            )

            # Styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            normal_style = styles['Normal']
            toc_style = ParagraphStyle(
                'TOCHeading',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=20
            )

            # Build document content
            content = []

            # Add title page
            content.append(Paragraph("Combined Slides", title_style))
            content.append(Spacer(1, 0.25*inch))
            content.append(Paragraph(f"Total Slides: {len(all_images)}", normal_style))
            content.append(Paragraph(f"Created: {time.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            content.append(PageBreak())

            # Add table of contents if requested
            if toc:
                content.append(Paragraph("Table of Contents", toc_style))
                toc = TableOfContents()
                toc.levelStyles = [
                    ParagraphStyle(name='TOC1', fontSize=14, leftIndent=20, firstLineIndent=-20),
                    ParagraphStyle(name='TOC2', fontSize=12, leftIndent=40, firstLineIndent=-20),
                ]
                content.append(toc)
                content.append(PageBreak())

            # Process slides in batches
            total_slides = len(all_images)
            last_progress_percent = -1

            for i, (img_path, metadata) in enumerate(all_images):
                if self.stop_requested:
                    break

                # Calculate progress percentage
                progress_percent = int((i / total_slides) * 100)

                # Update progress more frequently for large slide sets
                if self.callback and (progress_percent > last_progress_percent or i % 5 == 0):
                    last_progress_percent = progress_percent
                    progress = f"Adding slide {i+1}/{total_slides} to PDF... ({progress_percent}%)"
                    self.callback(progress)

                try:
                    # Get slide metadata
                    title = metadata.get('title', f"Slide {i+1}")
                    slide_type = metadata.get('type', 'content')
                    timestamp = metadata.get('timestamp', '')
                    source_dir = metadata.get('source_dir', '')

                    # Add slide title as bookmark
                    if toc:
                        content.append(Paragraph(title, title_style))

                    # Add image
                    img = RLImage(img_path, width=7*inch, height=5*inch, kind='proportional')
                    content.append(img)

                    # Add metadata if requested
                    if metadata:
                        metadata_table = []
                        if timestamps and timestamp:
                            metadata_table.append(["Timestamp:", timestamp])
                        if slide_type:
                            metadata_table.append(["Type:", slide_type.capitalize()])
                        if source_dir:
                            metadata_table.append(["Source:", source_dir])

                        if metadata_table:
                            t = Table(metadata_table, colWidths=[1*inch, 6*inch])
                            t.setStyle(TableStyle([
                                ('TEXTCOLOR', (0, 0), (-1, -1), colors.darkblue),
                                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
                                ('FONT', (1, 0), (1, -1), 'Helvetica'),
                                ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ]))
                            content.append(t)

                    # Add page break after each slide except the last one
                    if i < len(all_images) - 1:
                        content.append(PageBreak())

                except Exception as e:
                    error_msg = f"Error adding slide {img_path} to PDF: {e}"
                    logger.error(error_msg)
                    if self.callback:
                        self.callback(f"Warning: {error_msg}")

            # Build the PDF
            doc.build(
                content,
                onFirstPage=self._add_page_number if page_numbers else None,
                onLaterPages=self._add_page_number if page_numbers else None
            )

            result_message = f"Combined PDF created at: {output_file}"
            logger.info(result_message)

            if self.callback:
                self.callback(result_message)

            return output_file

        except ImportError:
            # Fall back to simple PDF creation if reportlab features aren't available
            logger.warning("Advanced PDF features not available. Creating simple PDF.")
            return self._create_simple_pdf_from_dirs(slide_dirs, output_file, batch_size)
        except Exception as e:
            logger.error(f"Error creating enhanced PDF: {e}")
            # Fall back to simple PDF creation
            logger.warning("Falling back to simple PDF creation.")
            return self._create_simple_pdf_from_dirs(slide_dirs, output_file, batch_size)

    def _create_simple_pdf_from_dirs(self, slide_dirs, pdf_path, batch_size):
        """Create a simple PDF from multiple directories without advanced features using img2pdf"""
        try:
            # Collect all slide paths
            all_paths = []
            for slide_dir in slide_dirs:
                if not os.path.exists(slide_dir) or not os.path.isdir(slide_dir):
                    continue

                slide_files = sorted([
                    os.path.join(slide_dir, f) for f in os.listdir(slide_dir)
                    if f.lower().endswith(".png") and f.startswith("slide_")
                ])
                all_paths.extend(slide_files)

            if not all_paths:
                logger.warning("No slide images found to convert.")
                if self.callback:
                    self.callback("No slide images found to convert.")
                return None

            if self.callback:
                self.callback(f"Creating PDF with {len(all_paths)} slides using img2pdf...")

            try:
                # Try using img2pdf for better quality and performance
                import img2pdf

                # Filter out any non-existent files
                valid_paths = [p for p in all_paths if os.path.exists(p)]

                if not valid_paths:
                    logger.warning("No valid image files found for PDF creation")
                    if self.callback:
                        self.callback("No valid image files found for PDF creation")
                    return None

                # Try to create the PDF in the specified location
                try:
                    with open(pdf_path, "wb") as f:
                        f.write(img2pdf.convert(valid_paths))
                    logger.info(f"PDF created at: {pdf_path}")
                except PermissionError as e:
                    logger.error(f"Permission error saving PDF: {e}")
                    # Try saving to user's home directory
                    try:
                        home_dir = os.path.expanduser("~")
                        temp_name = f"slides_{int(time.time())}.pdf"
                        home_path = os.path.join(home_dir, temp_name)
                        logger.info(f"Creating PDF in home directory: {home_path}")

                        with open(home_path, "wb") as f:
                            f.write(img2pdf.convert(valid_paths))

                        pdf_path = home_path
                        if self.callback:
                            self.callback(f"Created PDF in home directory: {home_path}")
                    except Exception as home_e:
                        logger.error(f"Error creating PDF in home directory: {home_e}")
                        # Try system temp directory as a last resort
                        try:
                            import tempfile
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                            temp_file.close()  # Close it so we can use it
                            temp_path = temp_file.name
                            logger.info(f"Creating PDF in system temp directory: {temp_path}")

                            with open(temp_path, "wb") as f:
                                f.write(img2pdf.convert(valid_paths))

                            pdf_path = temp_path
                            if self.callback:
                                self.callback(f"Created PDF in system temp directory: {temp_path}")
                        except Exception as temp_e:
                            logger.error(f"Error creating PDF in system temp directory: {temp_e}")
                            return self._create_simple_pdf_from_dirs_fallback(all_paths, pdf_path, batch_size)

                result_message = f"Combined PDF created at: {pdf_path} using img2pdf"
                logger.info(result_message)

                if self.callback:
                    self.callback(result_message)

                return pdf_path

            except ImportError:
                logger.warning("img2pdf not available, falling back to PIL")
                return self._create_simple_pdf_from_dirs_fallback(all_paths, pdf_path, batch_size)

        except Exception as e:
            logger.error(f"Error creating PDF with img2pdf: {e}")
            # Fall back to PIL method
            return self._create_simple_pdf_from_dirs_fallback(all_paths, pdf_path, batch_size)

    def _create_simple_pdf_from_dirs_fallback(self, all_paths, pdf_path, batch_size):
        """Fallback method to create PDF from multiple directories using PIL if img2pdf fails"""
        try:
            if self.callback:
                self.callback("Falling back to PIL for PDF creation...")

            # Process images in batches to reduce memory usage
            first_image = Image.open(all_paths[0]).convert("RGB")

            # Save first image to PDF
            try:
                first_image.save(pdf_path, "PDF", resolution=100.0, save_all=True)
            except PermissionError as e:
                logger.error(f"Permission error saving PDF: {e}")
                try:
                    # Try saving to a different location in the same directory
                    dir_name = os.path.dirname(pdf_path)
                    temp_name = f"temp_pdf_{int(time.time())}.pdf"
                    temp_path = os.path.join(dir_name, temp_name)
                    logger.info(f"Trying to save to alternate location: {temp_path}")
                    first_image.save(temp_path, "PDF", resolution=100.0, save_all=True)
                    # Return the temp path instead
                    pdf_path = temp_path
                except Exception as inner_e:
                    logger.error(f"Error saving to alternate location: {inner_e}")
                    # Try saving to user's home directory
                    try:
                        home_dir = os.path.expanduser("~")
                        temp_name = f"slides_{int(time.time())}.pdf"
                        home_path = os.path.join(home_dir, temp_name)
                        logger.info(f"Trying to save to home directory: {home_path}")
                        first_image.save(home_path, "PDF", resolution=100.0, save_all=True)
                        # Return the home path instead
                        pdf_path = home_path
                        if self.callback:
                            self.callback(f"Saved PDF to home directory: {home_path}")
                    except Exception as home_e:
                        logger.error(f"Error saving to home directory: {home_e}")
                        # Try system temp directory as a last resort
                        try:
                            import tempfile
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                            temp_file.close()  # Close it so we can use it
                            temp_path = temp_file.name
                            logger.info(f"Trying to save to system temp directory: {temp_path}")
                            first_image.save(temp_path, "PDF", resolution=100.0, save_all=True)
                            # Return the temp path instead
                            pdf_path = temp_path
                            if self.callback:
                                self.callback(f"Saved PDF to system temp directory: {temp_path}")
                        except Exception as temp_e:
                            logger.error(f"Error saving to system temp directory: {temp_e}")
                            # Continue and let the outer try-except handle it
            finally:
                first_image.close()

            # Process remaining images in batches
            for i in range(1, len(all_paths), batch_size):
                if self.stop_requested:
                    break

                batch = all_paths[i:i+batch_size]

                if self.callback:
                    progress = f"Adding slides to PDF: {i}/{len(all_paths)} ({i/len(all_paths)*100:.1f}%)"
                    self.callback(progress)

                # Open all images in the batch
                images = []
                for img_path in batch:
                    try:
                        img = Image.open(img_path).convert("RGB")
                        images.append(img)
                    except Exception as e:
                        logger.error(f"Error opening image {img_path}: {e}")

                # Append to PDF
                if images:
                    try:
                        with open(pdf_path, "ab") as f:
                            images[0].save(f, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
                    except PermissionError as e:
                        logger.error(f"Permission error appending to PDF: {e}")
                        # Skip trying the same directory and go straight to home directory
                        try:
                            home_dir = os.path.expanduser("~")
                            temp_name = f"slides_{int(time.time())}.pdf"
                            home_path = os.path.join(home_dir, temp_name)
                            logger.info(f"Creating PDF in home directory: {home_path}")

                            images[0].save(home_path, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
                            pdf_path = home_path

                            if self.callback:
                                self.callback(f"Created PDF in home directory: {home_path}")
                        except Exception as home_e:
                            logger.error(f"Error creating PDF in home directory: {home_e}")
                            # If home directory fails, try a different approach with a temporary file
                            try:
                                # Create a temporary file in the system temp directory
                                import tempfile
                                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                                temp_file.close()  # Close it so we can use it
                                temp_path = temp_file.name
                                logger.info(f"Creating PDF in system temp directory: {temp_path}")

                                images[0].save(temp_path, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
                                pdf_path = temp_path

                                if self.callback:
                                    self.callback(f"Created PDF in system temp directory: {temp_path}")
                            except Exception as temp_e:
                                logger.error(f"Error creating PDF in temp directory: {temp_e}")
                    except Exception as e:
                        logger.error(f"Error appending to PDF: {e}")
                    finally:
                        # Close all images
                        for img in images:
                            img.close()

            result_message = f"Simple combined PDF created at: {pdf_path} using PIL"
            logger.info(result_message)

            if self.callback:
                self.callback(result_message)

            return pdf_path
        except Exception as e:
            logger.error(f"Error creating simple combined PDF with PIL: {e}")
            return None

    def _create_simple_pdf(self, image_files, pdf_path, batch_size):
        """Create a simple PDF without advanced features using img2pdf"""
        try:
            # Extract just the paths from image_files tuples
            paths = [path for path, _ in image_files] if isinstance(image_files[0], tuple) else image_files

            if self.callback:
                self.callback(f"Creating PDF with {len(paths)} slides using img2pdf...")

            try:
                # Try using img2pdf for better quality and performance
                import img2pdf

                # Filter out any non-existent files
                valid_paths = [p for p in paths if os.path.exists(p)]

                if not valid_paths:
                    logger.warning("No valid image files found for PDF creation")
                    if self.callback:
                        self.callback("No valid image files found for PDF creation")
                    return None

                # Try to create the PDF in the specified location
                try:
                    with open(pdf_path, "wb") as f:
                        f.write(img2pdf.convert(valid_paths))
                    logger.info(f"PDF created at: {pdf_path}")
                except PermissionError as e:
                    logger.error(f"Permission error saving PDF: {e}")
                    # Try saving to user's home directory
                    try:
                        home_dir = os.path.expanduser("~")
                        temp_name = f"slides_{int(time.time())}.pdf"
                        home_path = os.path.join(home_dir, temp_name)
                        logger.info(f"Creating PDF in home directory: {home_path}")

                        with open(home_path, "wb") as f:
                            f.write(img2pdf.convert(valid_paths))

                        pdf_path = home_path
                        if self.callback:
                            self.callback(f"Created PDF in home directory: {home_path}")
                    except Exception as home_e:
                        logger.error(f"Error creating PDF in home directory: {home_e}")
                        # Try system temp directory as a last resort
                        try:
                            import tempfile
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                            temp_file.close()  # Close it so we can use it
                            temp_path = temp_file.name
                            logger.info(f"Creating PDF in system temp directory: {temp_path}")

                            with open(temp_path, "wb") as f:
                                f.write(img2pdf.convert(valid_paths))

                            pdf_path = temp_path
                            if self.callback:
                                self.callback(f"Created PDF in system temp directory: {temp_path}")
                        except Exception as temp_e:
                            logger.error(f"Error creating PDF in system temp directory: {temp_e}")
                            return self._create_simple_pdf_fallback(paths, pdf_path, batch_size)

                result_message = f"PDF created at: {pdf_path} using img2pdf"
                logger.info(result_message)

                if self.callback:
                    self.callback(result_message)

                return pdf_path

            except ImportError:
                logger.warning("img2pdf not available, falling back to PIL")
                return self._create_simple_pdf_fallback(paths, pdf_path, batch_size)

        except Exception as e:
            logger.error(f"Error creating PDF with img2pdf: {e}")
            # Fall back to PIL method
            return self._create_simple_pdf_fallback(paths, pdf_path, batch_size)

    def _create_simple_pdf_fallback(self, paths, pdf_path, batch_size):
        """Fallback method to create PDF using PIL if img2pdf fails"""
        try:
            if self.callback:
                self.callback("Falling back to PIL for PDF creation...")

            # Process images in batches to reduce memory usage
            first_image = Image.open(paths[0]).convert("RGB")

            # Save first image to PDF
            try:
                first_image.save(pdf_path, "PDF", resolution=100.0, save_all=True)
            except PermissionError as e:
                logger.error(f"Permission error saving PDF: {e}")
                try:
                    # Try saving to a different location in the same directory
                    dir_name = os.path.dirname(pdf_path)
                    temp_name = f"temp_pdf_{int(time.time())}.pdf"
                    temp_path = os.path.join(dir_name, temp_name)
                    logger.info(f"Trying to save to alternate location: {temp_path}")
                    first_image.save(temp_path, "PDF", resolution=100.0, save_all=True)
                    # Return the temp path instead
                    pdf_path = temp_path
                except Exception as inner_e:
                    logger.error(f"Error saving to alternate location: {inner_e}")
                    # Try saving to user's home directory
                    try:
                        home_dir = os.path.expanduser("~")
                        temp_name = f"slides_{int(time.time())}.pdf"
                        home_path = os.path.join(home_dir, temp_name)
                        logger.info(f"Trying to save to home directory: {home_path}")
                        first_image.save(home_path, "PDF", resolution=100.0, save_all=True)
                        # Return the home path instead
                        pdf_path = home_path
                        if self.callback:
                            self.callback(f"Saved PDF to home directory: {home_path}")
                    except Exception as home_e:
                        logger.error(f"Error saving to home directory: {home_e}")
                        # Try system temp directory as a last resort
                        try:
                            import tempfile
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                            temp_file.close()  # Close it so we can use it
                            temp_path = temp_file.name
                            logger.info(f"Trying to save to system temp directory: {temp_path}")
                            first_image.save(temp_path, "PDF", resolution=100.0, save_all=True)
                            # Return the temp path instead
                            pdf_path = temp_path
                            if self.callback:
                                self.callback(f"Saved PDF to system temp directory: {temp_path}")
                        except Exception as temp_e:
                            logger.error(f"Error saving to system temp directory: {temp_e}")
                            # Continue and let the outer try-except handle it
            finally:
                first_image.close()

            # Process remaining images in batches
            for i in range(1, len(paths), batch_size):
                if self.stop_requested:
                    break

                batch = paths[i:i+batch_size]

                if self.callback:
                    progress = f"Adding slides to PDF: {i}/{len(paths)} ({i/len(paths)*100:.1f}%)"
                    self.callback(progress)

                # Open all images in the batch
                images = []
                for img_path in batch:
                    try:
                        img = Image.open(img_path).convert("RGB")
                        images.append(img)
                    except Exception as e:
                        logger.error(f"Error opening image {img_path}: {e}")

                # Append to PDF
                if images:
                    try:
                        with open(pdf_path, "ab") as f:
                            images[0].save(f, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
                    except PermissionError as e:
                        logger.error(f"Permission error appending to PDF: {e}")
                        # Skip trying the same directory and go straight to home directory
                        try:
                            home_dir = os.path.expanduser("~")
                            temp_name = f"slides_{int(time.time())}.pdf"
                            home_path = os.path.join(home_dir, temp_name)
                            logger.info(f"Creating PDF in home directory: {home_path}")

                            images[0].save(home_path, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
                            pdf_path = home_path

                            if self.callback:
                                self.callback(f"Created PDF in home directory: {home_path}")
                        except Exception as home_e:
                            logger.error(f"Error creating PDF in home directory: {home_e}")
                            # If home directory fails, try a different approach with a temporary file
                            try:
                                # Create a temporary file in the system temp directory
                                import tempfile
                                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                                temp_file.close()  # Close it so we can use it
                                temp_path = temp_file.name
                                logger.info(f"Creating PDF in system temp directory: {temp_path}")

                                images[0].save(temp_path, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
                                pdf_path = temp_path

                                if self.callback:
                                    self.callback(f"Created PDF in system temp directory: {temp_path}")
                            except Exception as temp_e:
                                logger.error(f"Error creating PDF in temp directory: {temp_e}")
                    except Exception as e:
                        logger.error(f"Error appending to PDF: {e}")
                    finally:
                        # Close all images
                        for img in images:
                            img.close()

            result_message = f"Simple PDF created at: {pdf_path} using PIL"
            logger.info(result_message)

            if self.callback:
                self.callback(result_message)

            return pdf_path
        except Exception as e:
            logger.error(f"Error creating simple PDF with PIL: {e}")
            return None

    def stop(self):
        """Stop the extraction process"""
        self.stop_requested = True
        if self.callback:
            self.callback("Stopping extraction...")


def main():
    parser = argparse.ArgumentParser(description="Extract slides from educational YouTube videos")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--output", default="slides", help="Output directory for slides")
    parser.add_argument("--interval", type=int, default=5, help="Seconds between frame checks")
    parser.add_argument("--threshold", type=float, default=0.9, help="Similarity threshold")
    parser.add_argument("--pdf", action="store_true", help="Generate PDF after extraction")
    parser.add_argument("--multiprocessing", action="store_true", help="Enable parallel processing")
    parser.add_argument("--no-adaptive", action="store_true", help="Disable adaptive sampling")
    parser.add_argument("--no-content", action="store_true", help="Disable content extraction")
    parser.add_argument("--no-organize", action="store_true", help="Disable slide organization")
    parser.add_argument("--no-ignore-human-movement", action="store_true", help="Don't ignore human movements when detecting slide changes")
    parser.add_argument("--remove-humans", action="store_true", help="Detect and remove humans from frames")

    # New advanced options
    parser.add_argument("--enhanced", action="store_true", help="Use enhanced extraction with advanced content analysis")
    parser.add_argument("--syllabus", help="Path to syllabus JSON file for topic mapping")

    args = parser.parse_args()

    # Configure logging for command line mode
    logger.setLevel(logging.INFO)

    # Print startup message
    print("Advanced YouTube Slide Extractor")
    print(f"Processing video: {args.url}")
    print(f"Output directory: {args.output}")
    print(f"Frame interval: {args.interval} seconds")
    print(f"Similarity threshold: {args.threshold}")
    print(f"Multiprocessing: {'enabled' if args.multiprocessing else 'disabled'}")
    print(f"Adaptive sampling: {'disabled' if args.no_adaptive else 'enabled'}")
    print(f"Content extraction: {'disabled' if args.no_content else 'enabled'}")
    print(f"Slide organization: {'disabled' if args.no_organize else 'enabled'}")
    print(f"Ignore human movement: {'disabled' if args.no_ignore_human_movement else 'enabled'}")
    print(f"Human removal: {'enabled' if args.remove_humans else 'disabled'}")
    print(f"Enhanced mode: {'enabled' if args.enhanced else 'disabled'}")
    print("Starting extraction...")

    # Use enhanced extractor if requested
    if args.enhanced:
        try:
            from enhanced_slide_extractor import EnhancedSlideExtractor

            extractor = EnhancedSlideExtractor(
                video_url=args.url,
                output_dir=args.output,
                syllabus_file=args.syllabus,
                interval=args.interval,
                similarity_threshold=args.threshold,
                use_multiprocessing=args.multiprocessing,
                adaptive_sampling=not args.no_adaptive,
                extract_content=not args.no_content,
                organize_slides=not args.no_organize,
                ignore_human_movement=not args.no_ignore_human_movement
            )

            if extractor.extract_slides():
                print("Enhanced slide extraction completed successfully!")

                # Generate PDF if requested
                if args.pdf:
                    print("Generating PDF...")
                    pdf_path = extractor.base_extractor.convert_slides_to_pdf()
                    if pdf_path:
                        print(f"PDF created at: {pdf_path}")
                    else:
                        print("PDF generation failed")

                print("Analysis results available in:", extractor.analysis_dir)
            else:
                print("Slide extraction failed.")

        except ImportError:
            print("Enhanced extraction mode not available. Using standard extraction.")
            # Fall back to standard extraction
            standard_extraction(args)
    else:
        # Use standard extraction
        standard_extraction(args)

def standard_extraction(args):
    """Run standard slide extraction without enhanced features."""
    extractor = SlideExtractor(
        video_url=args.url,
        output_dir=args.output,
        interval=args.interval,
        similarity_threshold=args.threshold,
        use_multiprocessing=args.multiprocessing,
        adaptive_sampling=not args.no_adaptive,
        extract_content=not args.no_content,
        organize_slides=not args.no_organize,
        ignore_human_movement=not args.no_ignore_human_movement
    )

    if extractor.extract_slides():
        print("Slide extraction completed successfully!")
        if args.pdf:
            print("Generating PDF...")
            pdf_path = extractor.convert_slides_to_pdf()
            if pdf_path:
                print(f"PDF created at: {pdf_path}")
            else:
                print("PDF generation failed")
    else:
        print("Slide extraction failed.")


if __name__ == "__main__":
    main()
