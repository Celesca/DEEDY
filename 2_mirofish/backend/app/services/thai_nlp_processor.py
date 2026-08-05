import re
from typing import List, Dict, Any, Tuple
from pythainlp.util import normalize
from pythainlp.tokenize import word_tokenize, sent_tokenize
from pythainlp.tag import pos_tag
from pythainlp.spell import correct

try:
    from pythainlp.tag.named_entity import NER
    ner_engine = NER("thainer")
except Exception as e:
    ner_engine = None

class ThaiNLPProcessor:
    """
    A processor for handling Thai language nuances in the DEEDY framework.
    Provides text normalization, segmentation, BE to CE date conversion,
    and named entity recognition.
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize Thai text (remove redundant spaces, correct characters)."""
        return normalize(text)

    @staticmethod
    def tokenize_words(text: str) -> List[str]:
        """Tokenize Thai text into words."""
        return word_tokenize(text, engine="newmm")

    @staticmethod
    def tokenize_sentences(text: str) -> List[str]:
        """Tokenize Thai text into sentences."""
        return sent_tokenize(text, engine="crfcut")

    @staticmethod
    def extract_entities(text: str) -> List[Tuple[str, str]]:
        """
        Extract named entities from Thai text.
        Returns a list of tuples: (entity_text, entity_label)
        """
        if ner_engine is None:
            return []
        
        try:
            tokens_with_tags = ner_engine.tag(text)
            entities = []
            current_entity = ""
            current_tag = ""
            
            for word, pos, tag in tokens_with_tags:
                if tag.startswith("B-"):
                    if current_entity:
                        entities.append((current_entity, current_tag))
                    current_entity = word
                    current_tag = tag[2:]
                elif tag.startswith("I-") and current_tag == tag[2:]:
                    current_entity += word
                else:
                    if current_entity:
                        entities.append((current_entity, current_tag))
                        current_entity = ""
                        current_tag = ""
            
            if current_entity:
                entities.append((current_entity, current_tag))
                
            return entities
        except Exception:
            return []

    @staticmethod
    def convert_be_to_ce(text: str) -> str:
        """
        Detect and convert Buddhist Era (BE) years to Common Era (CE) years.
        Thai BE is generally CE + 543.
        Simple heuristic: looks for numbers 25xx or 24xx in the text.
        """
        def replace_year(match):
            year_be = int(match.group(0))
            # Assume BE years relevant are roughly between 2400 (1857 CE) and 2600 (2057 CE)
            if 2400 <= year_be <= 2600:
                year_ce = year_be - 543
                return str(year_ce)
            return str(year_be)

        # Look for 4-digit numbers that could be BE years
        pattern = r'\b(24\d{2}|25\d{2}|26\d{2})\b'
        return re.sub(pattern, replace_year, text)

    @staticmethod
    def tag_expressive_spellings(words: List[str]) -> List[Dict[str, Any]]:
        """
        Tag expressive or misspelled words and provide corrections.
        """
        tagged = []
        for word in words:
            # Skip non-Thai or short words
            if not re.search(r'[\u0E00-\u0E7F]', word):
                continue
            
            correction = correct(word)
            if correction != word:
                tagged.append({
                    "original": word,
                    "correction": correction,
                    "is_expressive": True
                })
        return tagged

    @classmethod
    def process_document(cls, text: str) -> Dict[str, Any]:
        """
        Process a full document, apply all Thai NLP steps.
        """
        normalized = cls.normalize_text(text)
        converted_dates = cls.convert_be_to_ce(normalized)
        sentences = cls.tokenize_sentences(converted_dates)
        
        all_words = []
        for sent in sentences:
            all_words.extend(cls.tokenize_words(sent))
            
        entities = cls.extract_entities(converted_dates)
        expressive_tags = cls.tag_expressive_spellings(all_words)
        
        return {
            "processed_text": converted_dates,
            "sentences": sentences,
            "tokens": all_words,
            "entities": entities,
            "expressive_tags": expressive_tags
        }
