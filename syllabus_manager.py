import os
import json
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("syllabus_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SyllabusManager")

class SyllabusManager:
    """
    Manages syllabus data and provides mapping between course content and syllabus topics.
    
    This class enables:
    1. Loading and parsing syllabus data from various formats
    2. Creating structured topic hierarchies
    3. Mapping content to syllabus topics
    4. Generating study plans based on syllabus coverage
    """
    
    def __init__(self):
        """Initialize the SyllabusManager."""
        self.topics = {}  # Topic ID -> Topic data
        self.topic_hierarchy = defaultdict(list)  # Parent ID -> List of child IDs
        self.topic_keywords = defaultdict(list)  # Topic ID -> List of keywords
        self.topic_resources = defaultdict(list)  # Topic ID -> List of resources
        
    def load_syllabus(self, syllabus_file):
        """
        Load syllabus data from a JSON file.
        
        Args:
            syllabus_file: Path to syllabus JSON file
            
        Returns:
            Boolean indicating success
        """
        try:
            if not os.path.exists(syllabus_file):
                logger.error(f"Syllabus file not found: {syllabus_file}")
                return False
                
            with open(syllabus_file, 'r', encoding='utf-8') as f:
                syllabus_data = json.load(f)
                
            # Reset data structures
            self.topics = {}
            self.topic_hierarchy = defaultdict(list)
            self.topic_keywords = defaultdict(list)
            self.topic_resources = defaultdict(list)
            
            # Process topics
            for topic in syllabus_data.get('topics', []):
                topic_id = topic.get('id')
                if not topic_id:
                    continue
                    
                # Store topic data
                self.topics[topic_id] = {
                    'id': topic_id,
                    'title': topic.get('title', ''),
                    'description': topic.get('description', ''),
                    'weight': topic.get('weight', 1.0),
                    'parent': topic.get('parent', None)
                }
                
                # Update hierarchy
                parent_id = topic.get('parent')
                if parent_id:
                    self.topic_hierarchy[parent_id].append(topic_id)
                    
                # Store keywords
                keywords = topic.get('keywords', [])
                if keywords:
                    self.topic_keywords[topic_id].extend(keywords)
                    
                # Store resources
                resources = topic.get('resources', [])
                if resources:
                    self.topic_resources[topic_id].extend(resources)
                    
            logger.info(f"Loaded syllabus with {len(self.topics)} topics")
            return True
            
        except Exception as e:
            logger.error(f"Error loading syllabus: {e}")
            return False
            
    def create_empty_syllabus(self, course_name, course_code=None, description=None):
        """
        Create a new empty syllabus structure.
        
        Args:
            course_name: Name of the course
            course_code: Course code (optional)
            description: Course description (optional)
            
        Returns:
            Dictionary with basic syllabus structure
        """
        syllabus = {
            'course_name': course_name,
            'course_code': course_code,
            'description': description,
            'topics': []
        }
        return syllabus
        
    def add_topic(self, title, description=None, parent=None, keywords=None, weight=1.0):
        """
        Add a new topic to the syllabus.
        
        Args:
            title: Topic title
            description: Topic description (optional)
            parent: Parent topic ID (optional)
            keywords: List of keywords (optional)
            weight: Topic importance weight (optional)
            
        Returns:
            ID of the new topic
        """
        # Generate a unique ID
        topic_id = f"topic_{len(self.topics) + 1}"
        
        # Create topic data
        self.topics[topic_id] = {
            'id': topic_id,
            'title': title,
            'description': description or '',
            'weight': weight,
            'parent': parent
        }
        
        # Update hierarchy
        if parent:
            self.topic_hierarchy[parent].append(topic_id)
            
        # Store keywords
        if keywords:
            self.topic_keywords[topic_id].extend(keywords)
            
        logger.info(f"Added topic: {title} (ID: {topic_id})")
        return topic_id
        
    def save_syllabus(self, output_file):
        """
        Save the current syllabus to a JSON file.
        
        Args:
            output_file: Path to save the syllabus
            
        Returns:
            Boolean indicating success
        """
        try:
            # Convert to serializable format
            syllabus_data = {
                'topics': []
            }
            
            for topic_id, topic_data in self.topics.items():
                topic_entry = topic_data.copy()
                
                # Add keywords and resources
                topic_entry['keywords'] = self.topic_keywords.get(topic_id, [])
                topic_entry['resources'] = self.topic_resources.get(topic_id, [])
                
                syllabus_data['topics'].append(topic_entry)
                
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(syllabus_data, f, indent=2)
                
            logger.info(f"Saved syllabus to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving syllabus: {e}")
            return False
            
    def get_topic_tree(self, root_id=None):
        """
        Get a hierarchical representation of the syllabus.
        
        Args:
            root_id: ID of the root topic (optional)
            
        Returns:
            Dictionary with hierarchical topic structure
        """
        def build_tree(topic_id):
            topic = self.topics.get(topic_id, {})
            children = self.topic_hierarchy.get(topic_id, [])
            
            return {
                'id': topic_id,
                'title': topic.get('title', ''),
                'children': [build_tree(child_id) for child_id in children]
            }
            
        # If no root specified, find all top-level topics
        if root_id is None:
            top_level = [tid for tid, data in self.topics.items() 
                        if not data.get('parent')]
            return [build_tree(tid) for tid in top_level]
        else:
            return build_tree(root_id)
            
    def map_content_to_topics(self, content, keywords=None):
        """
        Map content to syllabus topics based on keyword matching.
        
        Args:
            content: Text content to map
            keywords: Pre-extracted keywords (optional)
            
        Returns:
            List of matching topics with confidence scores
        """
        if not self.topics:
            return []
            
        content_lower = content.lower()
        
        # Use provided keywords or extract from content
        if keywords is None:
            # Simple keyword extraction
            words = content_lower.split()
            keywords = [word for word in words if len(word) > 3]
            
        # Calculate match scores for each topic
        topic_scores = {}
        
        for topic_id, topic_keywords in self.topic_keywords.items():
            if not topic_keywords:
                continue
                
            # Count matching keywords
            matches = sum(1 for kw in topic_keywords if kw.lower() in content_lower)
            
            # Calculate confidence score
            if matches > 0:
                confidence = matches / len(topic_keywords)
                
                # Add title match bonus
                title = self.topics[topic_id].get('title', '').lower()
                if any(kw in title for kw in keywords):
                    confidence += 0.2
                    
                topic_scores[topic_id] = {
                    'topic_id': topic_id,
                    'title': self.topics[topic_id].get('title', ''),
                    'confidence': min(1.0, confidence),
                    'matching_keywords': matches
                }
                
        # Sort by confidence
        sorted_matches = sorted(topic_scores.values(), key=lambda x: x['confidence'], reverse=True)
        return sorted_matches
