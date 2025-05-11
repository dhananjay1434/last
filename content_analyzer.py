import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
from collections import Counter, defaultdict
import string
import math
import numpy as np
import os
import json
import logging

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
        logging.FileHandler("content_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ContentAnalyzer")

# Download required NLTK resources
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception as e:
    logger.warning(f"Failed to download NLTK resources: {e}")

class ContentAnalyzer:
    """
    Advanced content analysis for educational slides.

    This class provides methods for:
    1. Extracting key concepts from slide text
    2. Identifying important terms and definitions
    3. Recognizing educational patterns (formulas, theorems, etc.)
    4. Generating topic hierarchies and relationships
    5. Creating semantic metadata for better search and organization
    """

    def __init__(self, language='english'):
        """
        Initialize the ContentAnalyzer.

        Args:
            language: Language for text processing (default: 'english')
        """
        self.language = language
        self.lemmatizer = WordNetLemmatizer()

        # Load stopwords for the specified language
        try:
            self.stop_words = set(stopwords.words(language))
        except:
            logger.warning(f"Stopwords not available for {language}, using empty set")
            self.stop_words = set()

        # Add custom academic stopwords
        self.stop_words.update(['example', 'slide', 'page', 'figure', 'table', 'chapter'])

        # Patterns for identifying educational content
        self.definition_patterns = [
            r'(?i)(?:is defined as|is|refers to|means|is called)\s+(?:a|an|the)?\s*(.+?)(?:\.|$)',
            r'(?i)(?:definition of|definition:)\s+(.+?)(?:\.|$)',
            r'(?i)(.+?)(?:\s+is|\s+are|\s+refers to|\s+means)\s+(.+?)(?:\.|$)'
        ]

        self.formula_patterns = [
            r'(?i)(?:formula|equation):\s*(.+?)(?:\.|$)',
            r'(?i)(.+?)\s*=\s*(.+?)(?:\.|$)',
            r'(?i)\\begin\{equation\}(.+?)\\end\{equation\}'
        ]

        self.theorem_patterns = [
            r'(?i)(?:theorem|lemma|corollary|proposition):\s*(.+?)(?:\.|$)',
            r'(?i)(?:theorem|lemma|corollary|proposition)\s+(?:\d+|[A-Za-z]+):\s*(.+?)(?:\.|$)'
        ]

        # Domain-specific vocabulary for different subjects
        self.domain_vocabulary = {
            'math': ['theorem', 'proof', 'equation', 'formula', 'function', 'derivative', 'integral'],
            'computer_science': ['algorithm', 'complexity', 'function', 'class', 'object', 'method', 'variable'],
            'physics': ['force', 'energy', 'momentum', 'velocity', 'acceleration', 'mass', 'gravity'],
            'chemistry': ['reaction', 'molecule', 'atom', 'compound', 'element', 'bond', 'solution'],
            'biology': ['cell', 'organism', 'gene', 'protein', 'tissue', 'system', 'evolution']
        }

        # Initialize concept graph
        self.concept_graph = defaultdict(set)

        # Syllabus mapping data
        self.syllabus_topics = {}
        self.topic_keywords = defaultdict(list)

    def analyze_slide_content(self, text, slide_type=None, ocr_data=None):
        """
        Perform comprehensive analysis of slide content with enhanced OCR handling.

        Args:
            text: The text content of the slide (may include transcription)
            slide_type: Type of slide if known (title, content, code, etc.)
            ocr_data: Optional dictionary with enhanced OCR data

        Returns:
            Dictionary with analysis results
        """
        if not text or len(text.strip()) < 10:
            return {
                'key_concepts': [],
                'definitions': [],
                'formulas': [],
                'theorems': [],
                'domain': None,
                'complexity': 'low',
                'summary': '',
                'keywords': [],
                'has_transcription': False,
                'ocr_quality': 'unknown'
            }

        # Use enhanced OCR data if available
        if ocr_data and isinstance(ocr_data, dict):
            has_transcription = ocr_data.get('has_transcription', False)
            ocr_quality = ocr_data.get('quality', 'unknown')
            slide_content = ocr_data.get('text', text)
            transcription = ocr_data.get('transcription', '')
            combined_text = ocr_data.get('combined_text', text)
        else:
            # Check if text contains transcription
            has_transcription = 'Transcription:' in text

            # Split content and transcription for targeted analysis
            slide_content = text
            transcription = ""

            if has_transcription:
                parts = text.split('Transcription:', 1)
                slide_content = parts[0].strip()
                transcription = parts[1].strip() if len(parts) > 1 else ""

            # Process context if available
            context = ""
            if 'Context:' in text:
                context_parts = text.split('Context:', 1)
                context = context_parts[1].strip() if len(context_parts) > 1 else ""

            # Assess OCR quality
            ocr_quality = self._assess_ocr_quality(slide_content)

            # Combine slide content and transcription for comprehensive analysis
            combined_text = slide_content

        # If OCR quality is poor, rely more on transcription if available
        if ocr_quality == 'poor' and transcription:
            # Use transcription as the primary source of information
            combined_text = transcription
            # Look for mathematical formulas in the slide content
            potential_formulas = self._extract_potential_formulas(slide_content)

            # For regular analysis, still use combined text
            if transcription:
                combined_text = slide_content + "\n\n" + transcription
        else:
            # For good quality OCR, use both slide content and transcription
            if transcription:
                combined_text = slide_content + "\n\n" + transcription
            potential_formulas = []

        # Extract key concepts (from combined text for broader coverage)
        key_concepts = self.extract_key_concepts(combined_text)

        # Extract definitions (prioritize slide content, but check transcription if none found)
        definitions = self.extract_definitions(slide_content)
        if not definitions and transcription:
            definitions = self.extract_definitions(transcription)

        # Extract formulas (prioritize slide content as it's more likely to have formatted formulas)
        formulas = self.extract_formulas(slide_content)

        # If OCR quality is poor, try to extract potential formulas using more aggressive pattern matching
        potential_formulas = []
        if ocr_quality == 'poor' or ocr_quality == 'medium':
            potential_formulas = self._extract_potential_formulas(slide_content)
            # Add any potential formulas to the regular formulas list
            if potential_formulas:
                formulas.extend([f for f in potential_formulas if f not in formulas])

        # If still no formulas and transcription is available, check transcription
        if not formulas and transcription:
            # Check transcription for verbally described formulas
            formulas = self.extract_formulas(transcription)

        # Extract theorems (check both sources)
        theorems = self.extract_theorems(combined_text)

        # Determine subject domain (use combined text for better context)
        domain = self.determine_domain(combined_text)

        # Assess content complexity (use combined text)
        complexity = self.assess_complexity(combined_text)

        # Generate concise summary (prioritize transcription if available as it often explains the slide)
        summary = self.generate_summary(transcription if transcription else combined_text)

        # Extract keywords (from combined text for better coverage)
        keywords = self.extract_keywords(combined_text)

        # Map to syllabus topics if available (use combined text)
        syllabus_topics = self.map_to_syllabus_topics(combined_text, key_concepts, keywords)

        # Update concept graph
        self._update_concept_graph(key_concepts, combined_text)

        return {
            'key_concepts': key_concepts,
            'definitions': definitions,
            'formulas': formulas,
            'theorems': theorems,
            'domain': domain,
            'complexity': complexity,
            'summary': summary,
            'keywords': keywords,
            'syllabus_topics': syllabus_topics,
            'has_transcription': has_transcription,
            'transcription': transcription if has_transcription else "",
            'ocr_quality': ocr_quality,
            'potential_formulas': potential_formulas
        }

    def extract_key_concepts(self, text, max_concepts=5):
        """
        Extract key concepts from text using TF-IDF like approach.

        Args:
            text: Text to analyze
            max_concepts: Maximum number of concepts to extract

        Returns:
            List of key concepts
        """
        # Tokenize and clean text
        tokens = self._preprocess_text(text)

        # Count term frequencies
        term_freq = Counter(tokens)

        # Filter out common words and single characters
        filtered_terms = {term: freq for term, freq in term_freq.items()
                         if term not in self.stop_words and len(term) > 1}

        # Extract noun phrases (simple approach)
        noun_phrases = self._extract_noun_phrases(text)

        # Combine single terms and noun phrases with weights
        combined_concepts = {}
        for term, freq in filtered_terms.items():
            combined_concepts[term] = freq * (1 + 0.2 * len(term))  # Longer terms get slight boost

        for phrase in noun_phrases:
            if phrase in combined_concepts:
                combined_concepts[phrase] *= 1.5  # Boost noun phrases
            else:
                combined_concepts[phrase] = 2  # Default weight for noun phrases

        # Sort by score and return top concepts
        sorted_concepts = sorted(combined_concepts.items(), key=lambda x: x[1], reverse=True)
        return [concept for concept, _ in sorted_concepts[:max_concepts]]

    def extract_definitions(self, text):
        """
        Extract definitions from text using regex patterns.

        Args:
            text: Text to analyze

        Returns:
            List of dictionaries with term and definition
        """
        definitions = []
        sentences = sent_tokenize(text)

        for sentence in sentences:
            for pattern in self.definition_patterns:
                matches = re.findall(pattern, sentence)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple) and len(match) >= 2:
                            # Pattern with term and definition groups
                            term = match[0].strip()
                            definition = match[1].strip()
                            if term and definition and len(term) < 50:
                                definitions.append({
                                    'term': term,
                                    'definition': definition
                                })
                        elif isinstance(match, str):
                            # Pattern with just definition
                            definition = match.strip()
                            # Try to extract term from context
                            words = sentence.split()
                            if len(words) > 2 and definition:
                                potential_term = words[0]
                                if potential_term.lower() not in self.stop_words and len(potential_term) > 2:
                                    definitions.append({
                                        'term': potential_term,
                                        'definition': definition
                                    })

        # Remove duplicates while preserving order
        unique_definitions = []
        seen_terms = set()
        for d in definitions:
            if d['term'].lower() not in seen_terms:
                seen_terms.add(d['term'].lower())
                unique_definitions.append(d)

        return unique_definitions

    def extract_formulas(self, text):
        """
        Extract mathematical formulas from text.

        Args:
            text: Text to analyze

        Returns:
            List of extracted formulas
        """
        formulas = []
        sentences = sent_tokenize(text)

        for sentence in sentences:
            for pattern in self.formula_patterns:
                matches = re.findall(pattern, sentence)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple) and len(match) >= 2:
                            # Pattern with left and right side of equation
                            left = match[0].strip()
                            right = match[1].strip()
                            formula = f"{left} = {right}"
                            formulas.append(formula)
                        elif isinstance(match, str):
                            # Pattern with full formula
                            formula = match.strip()
                            if formula:
                                formulas.append(formula)

        # Remove duplicates while preserving order
        unique_formulas = []
        seen = set()
        for f in formulas:
            if f not in seen:
                seen.add(f)
                unique_formulas.append(f)

        return unique_formulas

    def extract_theorems(self, text):
        """
        Extract theorems, lemmas, and other mathematical statements.

        Args:
            text: Text to analyze

        Returns:
            List of extracted theorems
        """
        theorems = []
        sentences = sent_tokenize(text)

        for sentence in sentences:
            for pattern in self.theorem_patterns:
                matches = re.findall(pattern, sentence)
                if matches:
                    for match in matches:
                        if isinstance(match, str):
                            theorem = match.strip()
                            if theorem:
                                theorems.append(theorem)

        # Remove duplicates while preserving order
        unique_theorems = []
        seen = set()
        for t in theorems:
            if t not in seen:
                seen.add(t)
                unique_theorems.append(t)

        return unique_theorems

    def determine_domain(self, text):
        """
        Determine the subject domain of the content.

        Args:
            text: Text to analyze

        Returns:
            Most likely domain or None
        """
        text_lower = text.lower()
        domain_scores = {}

        # Score each domain based on vocabulary matches
        for domain, keywords in self.domain_vocabulary.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            domain_scores[domain] = score

        # Return the domain with the highest score, if any
        if domain_scores:
            max_domain = max(domain_scores.items(), key=lambda x: x[1])
            if max_domain[1] > 0:
                return max_domain[0]

        return None

    def assess_complexity(self, text):
        """
        Assess the complexity level of the content.

        Args:
            text: Text to analyze

        Returns:
            Complexity level: 'low', 'medium', or 'high'
        """
        # Simple heuristics for complexity assessment
        sentences = sent_tokenize(text)
        words = word_tokenize(text)

        # Average sentence length
        avg_sentence_length = len(words) / max(1, len(sentences))

        # Average word length
        avg_word_length = sum(len(word) for word in words) / max(1, len(words))

        # Count complex words (more than 3 syllables)
        complex_words = sum(1 for word in words if self._count_syllables(word) > 3)
        complex_word_ratio = complex_words / max(1, len(words))

        # Count technical terms
        technical_terms = sum(1 for domain_terms in self.domain_vocabulary.values()
                             for term in domain_terms if term in text.lower())

        # Calculate complexity score
        complexity_score = (
            0.3 * (avg_sentence_length / 15) +  # Normalize to ~0-1 range
            0.2 * (avg_word_length / 6) +       # Normalize to ~0-1 range
            0.3 * complex_word_ratio +          # Already 0-1
            0.2 * (technical_terms / 10)        # Normalize to ~0-1 range
        )

        # Map score to complexity level
        if complexity_score < 0.3:
            return 'low'
        elif complexity_score < 0.6:
            return 'medium'
        else:
            return 'high'

    def generate_summary(self, text, max_length=150):
        """
        Generate a concise summary of the slide content.

        Args:
            text: Text to summarize
            max_length: Maximum summary length in characters

        Returns:
            Summary text
        """
        # Simple extractive summarization
        sentences = sent_tokenize(text)

        if not sentences:
            return ""

        # For very short text, just return it
        if len(text) <= max_length:
            return text

        # Score sentences based on position and keyword presence
        sentence_scores = {}
        keywords = self.extract_keywords(text)

        for i, sentence in enumerate(sentences):
            # Position score - first and last sentences are important
            position_score = 1.0
            if i == 0:
                position_score = 2.0  # First sentence bonus
            elif i == len(sentences) - 1:
                position_score = 1.5  # Last sentence bonus
            else:
                position_score = 1.0 / (i + 1)  # Decreasing importance

            # Keyword score
            keyword_score = sum(1 for keyword in keywords if keyword.lower() in sentence.lower())

            # Length penalty for very long sentences
            length_penalty = min(1.0, 20 / max(10, len(sentence.split())))

            # Combined score
            sentence_scores[i] = (position_score + keyword_score) * length_penalty

        # Select top sentences
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)

        # Build summary by adding sentences until we reach max_length
        summary = ""
        for i, _ in top_sentences:
            if len(summary) + len(sentences[i]) <= max_length:
                summary += sentences[i] + " "
            else:
                break

        return summary.strip()

    def extract_keywords(self, text, max_keywords=10):
        """
        Extract important keywords from text.

        Args:
            text: Text to analyze
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keywords
        """
        # Tokenize and clean text
        tokens = self._preprocess_text(text)

        # Count term frequencies
        term_freq = Counter(tokens)

        # Filter out common words and single characters
        filtered_terms = {term: freq for term, freq in term_freq.items()
                         if term not in self.stop_words and len(term) > 1}

        # Apply TF-IDF like weighting
        weighted_terms = {}
        for term, freq in filtered_terms.items():
            # Longer terms are more likely to be important
            length_boost = 1 + 0.1 * min(10, len(term))

            # Terms with capital letters are more likely to be important
            capital_boost = 1.5 if any(c.isupper() for c in term) else 1.0

            # Combined weight
            weighted_terms[term] = freq * length_boost * capital_boost

        # Sort by weight and return top keywords
        sorted_terms = sorted(weighted_terms.items(), key=lambda x: x[1], reverse=True)
        return [term for term, _ in sorted_terms[:max_keywords]]

    def map_to_syllabus_topics(self, text, concepts=None, keywords=None):
        """
        Map slide content to syllabus topics.

        Args:
            text: Slide text content
            concepts: Extracted key concepts (optional)
            keywords: Extracted keywords (optional)

        Returns:
            List of matching syllabus topics with confidence scores
        """
        if not self.syllabus_topics:
            return []

        if concepts is None:
            concepts = self.extract_key_concepts(text)

        if keywords is None:
            keywords = self.extract_keywords(text)

        # Combine concepts and keywords
        all_terms = set(concepts + keywords)

        # Calculate match scores for each topic
        topic_scores = {}
        for topic_id, topic_data in self.syllabus_topics.items():
            topic_keywords = set(self.topic_keywords.get(topic_id, []))
            topic_title = topic_data.get('title', '').lower()

            # Count matching terms
            matching_terms = all_terms.intersection(topic_keywords)

            # Check if any concept appears in the topic title
            title_match = any(concept.lower() in topic_title for concept in concepts)

            # Calculate score
            score = len(matching_terms) / max(1, len(topic_keywords))
            if title_match:
                score += 0.3  # Bonus for title match

            if score > 0:
                topic_scores[topic_id] = {
                    'topic_id': topic_id,
                    'title': topic_data.get('title', ''),
                    'confidence': min(1.0, score),
                    'matching_terms': list(matching_terms)
                }

        # Sort by confidence and return
        sorted_topics = sorted(topic_scores.values(), key=lambda x: x['confidence'], reverse=True)
        return sorted_topics

    def _preprocess_text(self, text):
        """
        Preprocess text for analysis: tokenize, lowercase, lemmatize.

        Args:
            text: Input text

        Returns:
            List of preprocessed tokens
        """
        # Lowercase and tokenize
        tokens = word_tokenize(text.lower())

        # Remove punctuation and numbers
        tokens = [token for token in tokens if token not in string.punctuation and not token.isdigit()]

        # Lemmatize
        lemmatized = [self.lemmatizer.lemmatize(token) for token in tokens]

        return lemmatized

    def _extract_noun_phrases(self, text, max_length=4):
        """
        Extract potential noun phrases from text.

        Args:
            text: Input text
            max_length: Maximum number of words in a phrase

        Returns:
            List of noun phrases
        """
        # Simple noun phrase extraction without POS tagging
        words = word_tokenize(text)
        phrases = []

        # Extract all possible n-grams up to max_length
        for n in range(2, min(max_length + 1, len(words))):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                # Filter out phrases with punctuation or stopwords at boundaries
                if (words[i] not in string.punctuation and
                    words[i] not in self.stop_words and
                    words[i+n-1] not in string.punctuation and
                    words[i+n-1] not in self.stop_words):
                    phrases.append(phrase.lower())

        return phrases

    def _count_syllables(self, word):
        """
        Count the number of syllables in a word.

        Args:
            word: Input word

        Returns:
            Estimated number of syllables
        """
        # Simple syllable counting heuristic
        word = word.lower()

        # Remove non-alpha characters
        word = ''.join(c for c in word if c.isalpha())

        if not word:
            return 0

        # Count vowel groups
        vowels = "aeiouy"
        count = 0
        prev_is_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_is_vowel:
                count += 1
            prev_is_vowel = is_vowel

        # Adjust for silent e at the end
        if word.endswith('e') and len(word) > 2 and word[-2] not in vowels:
            count -= 1

        # Ensure at least one syllable
        return max(1, count)

    def _assess_ocr_quality(self, text):
        """
        Assess the quality of OCR text to determine if it's usable or mostly gibberish.

        Args:
            text: OCR text to assess

        Returns:
            String indicating quality: 'good', 'medium', or 'poor'
        """
        if not text:
            return 'poor'

        # Split into words
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())

        if not words:
            return 'poor'

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
        has_educational_patterns = bool(
            re.search(r'fig(ure)?\.?\s*\d+', text, re.IGNORECASE) or
            re.search(r'eq(uation)?\.?\s*\d+', text, re.IGNORECASE) or
            re.search(r'table\s*\d+', text, re.IGNORECASE) or
            re.search(r'chapter\s*\d+', text, re.IGNORECASE) or
            re.search(r'section\s*\d+', text, re.IGNORECASE)
        )

        # Check for mathematical symbols
        has_math_symbols = bool(
            re.search(r'[+\-*/=<>≤≥≈≠∑∏∫√∂∆πα-ωΑ-Ω]', text) or
            re.search(r'\b[xyz]\b', text)  # Common variable names
        )

        # Calculate ratio of valid words to total words
        valid_ratio = valid_words / len(words) if words else 0

        # Determine quality based on valid word ratio and patterns
        if valid_ratio > 0.3 or has_educational_patterns or has_math_symbols:
            if valid_ratio > 0.5:
                return 'good'
            else:
                return 'medium'
        else:
            return 'poor'

    def _extract_potential_formulas(self, text):
        """
        Extract potential mathematical formulas from text, even if the OCR is poor.
        This method is more aggressive in finding formula-like patterns.

        Args:
            text: Text to analyze

        Returns:
            List of potential formulas
        """
        potential_formulas = []

        # Look for equation-like patterns
        # Pattern 1: Anything with = sign
        eq_matches = re.findall(r'[^=]+=[^=]+', text)
        for match in eq_matches:
            potential_formulas.append(match.strip())

        # Pattern 2: Sequences of mathematical symbols
        math_matches = re.findall(r'[a-zA-Z0-9]+[\+\-\*/=<>≤≥≈≠∑∏∫√∂∆πα-ωΑ-Ω]+[a-zA-Z0-9]+', text)
        for match in math_matches:
            if match not in potential_formulas:
                potential_formulas.append(match.strip())

        # Pattern 3: Common formula structures (e.g., "f(x) = ...")
        func_matches = re.findall(r'[a-zA-Z]+\([a-zA-Z0-9,\s]+\)[\s=]+[^\n]+', text)
        for match in func_matches:
            if match not in potential_formulas:
                potential_formulas.append(match.strip())

        # Remove duplicates while preserving order
        unique_formulas = []
        seen = set()
        for formula in potential_formulas:
            if formula not in seen:
                seen.add(formula)
                unique_formulas.append(formula)

        return unique_formulas

    def _update_concept_graph(self, concepts, text):
        """
        Update the concept graph with relationships between concepts.

        Args:
            concepts: List of concepts
            text: Original text
        """
        # Add connections between concepts that appear in the same text
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                self.concept_graph[concept1].add(concept2)
                self.concept_graph[concept2].add(concept1)

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

            # Process syllabus data
            self.syllabus_topics = {}
            self.topic_keywords = defaultdict(list)

            # Extract topics and keywords
            for topic in syllabus_data.get('topics', []):
                topic_id = topic.get('id')
                if not topic_id:
                    continue

                self.syllabus_topics[topic_id] = {
                    'title': topic.get('title', ''),
                    'description': topic.get('description', ''),
                    'parent': topic.get('parent', None)
                }

                # Extract keywords from title and description
                title_words = self._preprocess_text(topic.get('title', ''))
                desc_words = self._preprocess_text(topic.get('description', ''))

                # Add explicit keywords if provided
                keywords = topic.get('keywords', [])
                if keywords:
                    self.topic_keywords[topic_id].extend(keywords)

                # Add important words from title and description
                for word in title_words:
                    if word not in self.stop_words and len(word) > 2:
                        self.topic_keywords[topic_id].append(word)

                for word in desc_words:
                    if word not in self.stop_words and len(word) > 2 and word not in self.topic_keywords[topic_id]:
                        self.topic_keywords[topic_id].append(word)

            logger.info(f"Loaded syllabus with {len(self.syllabus_topics)} topics")
            return True

        except Exception as e:
            logger.error(f"Error loading syllabus: {e}")
            return False

    def get_concept_relationships(self, concept, max_related=5):
        """
        Get related concepts for a given concept.

        Args:
            concept: The concept to find relationships for
            max_related: Maximum number of related concepts to return

        Returns:
            List of related concepts
        """
        if concept not in self.concept_graph:
            return []

        related = list(self.concept_graph[concept])

        # Sort by connection strength (frequency of co-occurrence)
        related.sort(key=lambda x: len(self.concept_graph[x].intersection(self.concept_graph[concept])), reverse=True)

        return related[:max_related]

    def generate_study_guide(self, slides_metadata, output_file=None, additional_info=""):
        """
        Generate a comprehensive study guide from analyzed slides.

        Args:
            slides_metadata: Dictionary of slide metadata with analysis results
            output_file: Path to save the study guide (optional)
            additional_info: Additional information to include at the beginning of the guide (optional)

        Returns:
            Study guide content as string
        """
        if not slides_metadata:
            return "No slide data available for study guide generation."

        # Collect all concepts, definitions, and formulas
        all_concepts = set()
        all_definitions = {}
        all_formulas = set()
        all_theorems = set()

        # Track topics and summaries by slide
        topics_by_slide = {}
        slide_summaries = {}

        # Track transcription availability
        has_transcription = False

        # Process all slides
        for slide_id, metadata in slides_metadata.items():
            # Skip slides without content analysis
            if 'content_analysis' not in metadata:
                continue

            analysis = metadata['content_analysis']

            # Check if any slide has transcription
            if analysis.get('has_transcription', False):
                has_transcription = True

            # Collect concepts
            for concept in analysis.get('key_concepts', []):
                all_concepts.add(concept)

            # Collect definitions
            for definition in analysis.get('definitions', []):
                term = definition.get('term', '').lower()
                if term and term not in all_definitions:
                    all_definitions[term] = definition.get('definition', '')

            # Collect formulas
            all_formulas.update(analysis.get('formulas', []))

            # Collect theorems
            all_theorems.update(analysis.get('theorems', []))

            # Track topics
            topics_by_slide[slide_id] = analysis.get('syllabus_topics', [])

            # Store slide summary
            if analysis.get('summary'):
                slide_summaries[slide_id] = {
                    'summary': analysis.get('summary', ''),
                    'timestamp': metadata.get('timestamp', 0),
                    'key_concepts': analysis.get('key_concepts', []),
                    'has_transcription': analysis.get('has_transcription', False)
                }

        # Generate study guide content
        content = []

        # Title
        content.append("# Comprehensive Study Guide\n")

        # Additional information (e.g., language)
        if additional_info:
            content.append(additional_info)

        # Overview
        content.append("## Overview\n")
        overview_text = f"This study guide covers {len(slides_metadata)} slides with {len(all_concepts)} key concepts."
        if has_transcription:
            overview_text += " Audio transcription has been integrated to provide more comprehensive explanations."
        content.append(overview_text + "\n")

        # Key Concepts
        content.append("\n## Key Concepts\n")
        for concept in sorted(all_concepts):
            content.append(f"- {concept}")

        # Definitions
        if all_definitions:
            content.append("\n## Important Definitions\n")
            for term, definition in sorted(all_definitions.items()):
                content.append(f"- **{term}**: {definition}")

        # Formulas
        if all_formulas:
            content.append("\n## Formulas\n")
            for formula in sorted(all_formulas):
                content.append(f"- {formula}")

        # Theorems
        if all_theorems:
            content.append("\n## Theorems and Principles\n")
            for theorem in sorted(all_theorems):
                content.append(f"- {theorem}")

        # Slide Summaries with Timestamps
        if slide_summaries:
            content.append("\n## Slide Summaries\n")

            # Sort slides by timestamp (convert to seconds first)
            sorted_slides = sorted(
                slide_summaries.items(),
                key=lambda x: convert_timestamp_to_seconds(x[1]['timestamp'])
            )

            for slide_id, data in sorted_slides:
                # Format timestamp as MM:SS
                timestamp = data['timestamp']

                # Convert timestamp to seconds if it's a string
                if isinstance(timestamp, str):
                    try:
                        # Try to use our utility function if available
                        if 'convert_timestamp_to_seconds' in globals():
                            timestamp = convert_timestamp_to_seconds(timestamp)
                        else:
                            # Simple conversion for common formats
                            if ':' in timestamp:
                                parts = timestamp.split(':')
                                if len(parts) == 3:  # H:MM:SS
                                    timestamp = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                                elif len(parts) == 2:  # MM:SS
                                    timestamp = int(parts[0]) * 60 + int(parts[1])
                                else:
                                    timestamp = 0
                            else:
                                timestamp = float(timestamp)
                    except Exception as e:
                        logger.error(f"Error converting timestamp '{timestamp}': {e}")
                        timestamp = 0

                # Format as MM:SS
                try:
                    minutes, seconds = divmod(int(float(timestamp)), 60)
                    timestamp_str = f"{minutes:02d}:{seconds:02d}"
                except Exception as e:
                    logger.error(f"Error formatting timestamp '{timestamp}': {e}")
                    timestamp_str = "00:00"

                # Add slide header with timestamp
                content.append(f"\n### Slide {slide_id} (Time: {timestamp_str})\n")

                # Add summary
                content.append(f"{data['summary']}\n")

                # Add key concepts for this slide
                if data['key_concepts']:
                    content.append("**Key points:**")
                    for concept in data['key_concepts']:
                        content.append(f"- {concept}")
                    content.append("")

        # Topics by Slide
        if any(topics_by_slide.values()):
            content.append("\n## Topics by Slide\n")
            for slide_id, topics in sorted(topics_by_slide.items()):
                if topics:
                    content.append(f"\n### Slide {slide_id}\n")
                    for topic in topics:
                        confidence = topic.get('confidence', 0) * 100
                        content.append(f"- {topic.get('title', '')} (Confidence: {confidence:.0f}%)")

                        # Add matching terms if available
                        matching_terms = topic.get('matching_terms', [])
                        if matching_terms:
                            content.append(f"  - Related terms: {', '.join(matching_terms)}")

        # Combine content
        study_guide = "\n".join(content)

        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(study_guide)
                logger.info(f"Study guide saved to {output_file}")
            except Exception as e:
                logger.error(f"Error saving study guide: {e}")

        return study_guide
