"""Flashcard generator for converting extracted EPUB content into flashcards.

This module handles:
- Converting extracted content into flashcard Q&A format
- Splitting text into meaningful chunks
- Generating questions and answers
- Organizing cards by category/chapter
- Exporting to JSON format
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger
from epub_parser import ContentItem, EPUBMetadata


@dataclass
class Flashcard:
    """Represents a single flashcard."""
    id: str
    question: str
    answer: str
    category: str
    source_chapter: str
    difficulty: str = "medium"  # easy, medium, hard
    tags: List[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class FlashcardGenerator:
    """Generates flashcards from extracted EPUB content."""

    def __init__(self, metadata: EPUBMetadata, content_items: List[ContentItem]):
        """Initialize the flashcard generator.
        
        Args:
            metadata: EPUB metadata
            content_items: List of extracted content items
        """
        self.metadata = metadata
        self.content_items = content_items
        self.flashcards: List[Flashcard] = []
        self.card_id_counter = 0

    def generate(self, strategy: str = "definition") -> List[Flashcard]:
        """Generate flashcards from content.
        
        Args:
            strategy: Generation strategy ('definition', 'summary', 'qa', 'mixed')
        
        Returns:
            List of generated flashcards
        """
        self.flashcards = []
        
        for item in self.content_items:
            if strategy == "definition":
                cards = self._generate_from_definitions(item)
            elif strategy == "summary":
                cards = self._generate_from_summary(item)
            elif strategy == "qa":
                cards = self._generate_from_qa(item)
            elif strategy == "mixed":
                cards = self._generate_mixed(item)
            else:
                logger.warning(f"Unknown strategy: {strategy}, using definition")
                cards = self._generate_from_definitions(item)
            
            self.flashcards.extend(cards)
        
        logger.info(f"Generated {len(self.flashcards)} flashcards")
        return self.flashcards

    def _generate_from_definitions(self, item: ContentItem) -> List[Flashcard]:
        """Generate cards by finding definitions in the text.
        
        Looks for patterns like "X is..." or "X: definition"
        """
        cards = []
        text = item.text
        
        # Pattern 1: "Term is definition" or "Term are definitions"
        pattern1 = r'([A-Z][a-z\s]+(?:[A-Z][a-z]+)*?)\s+(?:is|are|refers to|means)\s+([^.!?]*[.!?])'
        
        for match in re.finditer(pattern1, text):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            
            # Filter out common false positives
            if self._is_valid_term(term) and len(definition) > 20:
                card = self._create_card(
                    question=f"What is {term}?",
                    answer=definition,
                    category=item.title,
                    source_chapter=item.title
                )
                cards.append(card)
        
        # Pattern 2: "Term: definition" format
        pattern2 = r'^([A-Za-z][^:]{5,50}):\s+([^.!?]*[.!?])'
        
        for line in text.split('.'):
            match = re.match(pattern2, line)
            if match:
                term = match.group(1).strip()
                definition = match.group(2).strip()
                
                if self._is_valid_term(term) and len(definition) > 15:
                    card = self._create_card(
                        question=f"Define: {term}",
                        answer=definition,
                        category=item.title,
                        source_chapter=item.title,
                        difficulty="easy"
                    )
                    cards.append(card)
        
        return cards[:20]  # Limit cards per chapter

    def _generate_from_summary(self, item: ContentItem) -> List[Flashcard]:
        """Generate cards by creating questions from the text.
        
        Splits text into chunks and generates fact-based questions.
        """
        cards = []
        sentences = self._split_into_sentences(item.text)
        
        for i, sentence in enumerate(sentences[:10]):  # Limit sentences
            if len(sentence.split()) > 5:  # Only meaningful sentences
                # Extract key entities and create questions
                card = self._create_card(
                    question=self._generate_question_from_sentence(sentence),
                    answer=sentence,
                    category=item.title,
                    source_chapter=item.title,
                    difficulty="medium"
                )
                cards.append(card)
        
        return cards

    def _generate_from_qa(self, item: ContentItem) -> List[Flashcard]:
        """Generate cards from Q&A sections in the content.
        
        Looks for question/answer pairs marked with "Q:" and "A:"
        """
        cards = []
        text = item.text
        
        # Find Q: ... A: ... patterns
        qa_pattern = r'Q:\s*([^\n]+)\s*A:\s*([^\n]+(?:\n(?!Q:)[^\n]+)*)'
        
        for match in re.finditer(qa_pattern, text, re.MULTILINE):
            question = match.group(1).strip()
            answer = match.group(2).strip()
            
            if len(question) > 10 and len(answer) > 15:
                card = self._create_card(
                    question=question,
                    answer=answer,
                    category=item.title,
                    source_chapter=item.title
                )
                cards.append(card)
        
        return cards

    def _generate_mixed(self, item: ContentItem) -> List[Flashcard]:
        """Generate cards using multiple strategies."""
        cards = []
        
        # Try all strategies and combine results
        for strategy in ["definition", "summary", "qa"]:
            if strategy == "definition":
                cards.extend(self._generate_from_definitions(item)[:5])
            elif strategy == "summary":
                cards.extend(self._generate_from_summary(item)[:5])
            elif strategy == "qa":
                cards.extend(self._generate_from_qa(item)[:5])
        
        return cards[:15]  # Limit total cards per chapter

    def _create_card(self, question: str, answer: str, category: str,
                     source_chapter: str, difficulty: str = "medium") -> Flashcard:
        """Create a flashcard with a unique ID."""
        self.card_id_counter += 1
        
        return Flashcard(
            id=f"{category.replace(' ', '_').lower()}_{self.card_id_counter}",
            question=question,
            answer=answer,
            category=category,
            source_chapter=source_chapter,
            difficulty=difficulty,
            tags=[category.lower()],
            metadata={
                "created_from": "automated_extraction",
                "book": self.metadata.title
            }
        )

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter using common punctuation
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _generate_question_from_sentence(self, sentence: str) -> str:
        """Generate a question from a sentence.
        
        Simple heuristic: convert "X does Y" to "What does X do?"
        """
        words = sentence.split()
        
        # Try to find subject and verb
        if len(words) > 3:
            # Simple patterns
            if " is " in sentence.lower():
                subject = sentence.split(" is ")[0].strip()
                return f"What is {subject}?"
            elif " has " in sentence.lower():
                subject = sentence.split(" has ")[0].strip()
                return f"What does {subject} have?"
            elif " are " in sentence.lower():
                subject = sentence.split(" are ")[0].strip()
                return f"What are {subject}?"
        
        # Fallback
        return f"Explain: {sentence[:50]}...?"

    def _is_valid_term(self, term: str) -> bool:
        """Check if a term is valid (not too short, not common words)."""
        if len(term) < 3 or len(term) > 100:
            return False
        
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        if term.lower() in common_words:
            return False
        
        return True

    def export_json(self, output_path: str, pretty: bool = True) -> str:
        """Export flashcards to JSON format.
        
        Args:
            output_path: Path to save JSON file
            pretty: Whether to pretty-print JSON
        
        Returns:
            Path to saved file
        """
        output = {
            "metadata": {
                "book_title": self.metadata.title,
                "book_author": self.metadata.author,
                "book_language": self.metadata.language,
                "total_cards": len(self.flashcards),
                "categories": list(set(card.category for card in self.flashcards))
            },
            "flashcards": [asdict(card) for card in self.flashcards]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(output, f, indent=2, ensure_ascii=False)
            else:
                json.dump(output, f, ensure_ascii=False)
        
        logger.info(f"Exported {len(self.flashcards)} flashcards to {output_path}")
        return output_path

    def export_csv(self, output_path: str) -> str:
        """Export flashcards to CSV format.
        
        Args:
            output_path: Path to save CSV file
        
        Returns:
            Path to saved file
        """
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'question', 'answer', 'category', 'difficulty', 'tags']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for card in self.flashcards:
                writer.writerow({
                    'id': card.id,
                    'question': card.question,
                    'answer': card.answer,
                    'category': card.category,
                    'difficulty': card.difficulty,
                    'tags': ','.join(card.tags)
                })
        
        logger.info(f"Exported {len(self.flashcards)} flashcards to {output_path}")
        return output_path

    def get_statistics(self) -> Dict:
        """Get statistics about generated flashcards."""
        difficulties = {}
        categories = {}
        
        for card in self.flashcards:
            difficulties[card.difficulty] = difficulties.get(card.difficulty, 0) + 1
            categories[card.category] = categories.get(card.category, 0) + 1
        
        return {
            "total_cards": len(self.flashcards),
            "by_difficulty": difficulties,
            "by_category": categories,
            "avg_question_length": sum(len(card.question) for card in self.flashcards) / len(self.flashcards) if self.flashcards else 0,
            "avg_answer_length": sum(len(card.answer) for card in self.flashcards) / len(self.flashcards) if self.flashcards else 0
        }


if __name__ == '__main__':
    import sys
    from epub_parser import EPUBParser
    
    if len(sys.argv) < 2:
        print("Usage: python flashcard_generator.py <epub_file> [output_file] [strategy]")
        print("Strategies: definition, summary, qa, mixed (default: mixed)")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "flashcards.json"
    strategy = sys.argv[3] if len(sys.argv) > 3 else "mixed"
    
    # Parse EPUB
    parser = EPUBParser(epub_file)
    metadata, content = parser.parse()
    
    # Generate flashcards
    generator = FlashcardGenerator(metadata, content)
    cards = generator.generate(strategy=strategy)
    
    # Export
    generator.export_json(output_file)
    
    # Print statistics
    stats = generator.get_statistics()
    print(f"\nFlashcard Generation Statistics:")
    print(f"Total cards: {stats['total_cards']}")
    print(f"By difficulty: {stats['by_difficulty']}")
    print(f"By category: {stats['by_category']}")
    print(f"Avg question length: {stats['avg_question_length']:.0f} chars")
    print(f"Avg answer length: {stats['avg_answer_length']:.0f} chars")
