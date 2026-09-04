"""Prompt templates for LLM-based flashcard generation and enhancement.

This module provides:
- Reusable prompt templates for different tasks
- Prompt builders for customization
- Few-shot examples for better LLM performance
- Response parsing utilities
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json


class TaskType(Enum):
    """Types of tasks for prompt templates."""
    ENHANCE_CARD = "enhance_card"
    GENERATE_QA = "generate_qa"
    CATEGORIZE = "categorize"
    ASSESS_DIFFICULTY = "assess_difficulty"
    EXTRACT_KEY_POINTS = "extract_key_points"
    GENERATE_RELATED = "generate_related"
    VALIDATE_ANSWER = "validate_answer"


@dataclass
class PromptTemplate:
    """A reusable prompt template."""
    name: str
    task_type: TaskType
    template: str
    examples: List[Dict[str, str]] = None
    system_prompt: str = None
    response_format: str = "text"  # 'text', 'json', 'list'

    def format(self, **kwargs) -> str:
        """Format the template with provided arguments."""
        return self.template.format(**kwargs)


class PromptTemplates:
    """Collection of prompt templates for various flashcard tasks."""

    # ============= ENHANCEMENT TEMPLATES =============

    ENHANCE_CARD = PromptTemplate(
        name="enhance_card",
        task_type=TaskType.ENHANCE_CARD,
        system_prompt="You are an expert educator. Improve flashcards to be clear, accurate, and pedagogically sound.",
        template="""Improve the following flashcard question and answer. 
Make them clear, concise, accurate, and pedagogically effective.
Ensure the question tests understanding of key concepts.
Ensure the answer is complete but concise (max 2-3 sentences).

Original Question: {question}
Original Answer: {answer}

Provide the improved version in JSON format:
{{
  "question": "improved question",
  "answer": "improved answer",
  "reasoning": "brief explanation of improvements"
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    ENHANCE_CARD_CONTEXT = PromptTemplate(
        name="enhance_card_with_context",
        task_type=TaskType.ENHANCE_CARD,
        system_prompt="You are an expert educator specializing in creating effective study materials.",
        template="""Improve the following flashcard for a {subject} course.
Context: This card is from {source_material}

Original Question: {question}
Original Answer: {answer}

Provide improvements that:
1. Make the question more specific and testable
2. Make the answer more complete and accurate
3. Align with typical learning objectives for {subject}

Respond in JSON format:
{{
  "question": "improved question",
  "answer": "improved answer",
  "difficulty": "easy|medium|hard",
  "learning_objective": "brief description"
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    # ============= GENERATION TEMPLATES =============

    GENERATE_QA = PromptTemplate(
        name="generate_qa",
        task_type=TaskType.GENERATE_QA,
        system_prompt="You are an expert educational content creator. Generate clear, focused study questions and answers.",
        template="""Generate a single focused educational question and answer from the following text.
Focus on key concepts, important facts, and understanding rather than trivial details.
The question should be specific and testable.
The answer should be accurate, complete, and concise (1-3 sentences).

Text: {text}

Respond in JSON format:
{{
  "question": "your focused question",
  "answer": "your comprehensive answer",
  "key_concept": "the main concept being tested"
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    GENERATE_QA_MULTIPLE = PromptTemplate(
        name="generate_qa_multiple",
        task_type=TaskType.GENERATE_QA,
        system_prompt="You are an expert at creating diverse, high-quality study materials.",
        template="""Generate {count} distinct educational questions and answers from the following text.
Each question should test different aspects of understanding.
Questions should range from factual recall to conceptual understanding.
Answers should be accurate and concise.

Text: {text}

Respond in JSON format:
{{
  "cards": [
    {{
      "question": "question 1",
      "answer": "answer 1",
      "type": "recall|comprehension|application"
    }},
    ...
  ]
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    # ============= CATEGORIZATION TEMPLATES =============

    CATEGORIZE_CARD = PromptTemplate(
        name="categorize_card",
        task_type=TaskType.CATEGORIZE,
        system_prompt="You are an expert at organizing educational content into meaningful categories.",
        template="""Categorize the following flashcard into the most appropriate category from the provided list.

Question: {question}
Answer: {answer}

Available categories: {categories}

Respond with ONLY the category name that best fits this card, nothing else.""",
        response_format="text"
    )

    CATEGORIZE_WITH_REASONING = PromptTemplate(
        name="categorize_with_reasoning",
        task_type=TaskType.CATEGORIZE,
        template="""Categorize the flashcard and provide reasoning.

Question: {question}
Answer: {answer}

Available categories: {categories}

Respond in JSON format:
{{
  "category": "selected category",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    # ============= DIFFICULTY ASSESSMENT TEMPLATES =============

    ASSESS_DIFFICULTY = PromptTemplate(
        name="assess_difficulty",
        task_type=TaskType.ASSESS_DIFFICULTY,
        system_prompt="You are an expert at assessing the cognitive difficulty of study materials.",
        template="""Assess the difficulty level of this flashcard.
Consider: vocabulary complexity, concept abstractness, required background knowledge.

Question: {question}
Answer: {answer}

Respond with ONLY one of: easy, medium, hard""",
        response_format="text"
    )

    ASSESS_DIFFICULTY_DETAILED = PromptTemplate(
        name="assess_difficulty_detailed",
        task_type=TaskType.ASSESS_DIFFICULTY,
        template="""Assess the difficulty of this flashcard in detail.

Question: {question}
Answer: {answer}

Respond in JSON format:
{{
  "difficulty": "easy|medium|hard",
  "cognitive_level": "remember|understand|apply|analyze|evaluate|create",
  "required_prior_knowledge": "list of prerequisite concepts",
  "reasoning": "explanation of difficulty assessment"
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    # ============= KEY POINTS EXTRACTION TEMPLATES =============

    EXTRACT_KEY_POINTS = PromptTemplate(
        name="extract_key_points",
        task_type=TaskType.EXTRACT_KEY_POINTS,
        system_prompt="You are skilled at identifying and extracting the most important ideas from educational materials.",
        template="""Extract the key points and main concepts from the following text that would be suitable for flashcards.
Prioritize important facts, definitions, and conceptual relationships.

Text: {text}

Respond in JSON format:
{{
  "key_points": [
    "key point 1",
    "key point 2",
    ...
  ],
  "main_concepts": ["concept1", "concept2", ...],
  "relationships": ["concept1 relates to concept2 because..."]
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    # ============= RELATED CONTENT TEMPLATES =============

    GENERATE_RELATED = PromptTemplate(
        name="generate_related_questions",
        task_type=TaskType.GENERATE_RELATED,
        system_prompt="You are skilled at creating related study questions that reinforce learning.",
        template="""Given this flashcard, generate {count} related questions that test different angles of understanding.

Original Question: {question}
Original Answer: {answer}

Generate questions that:
1. Test related concepts
2. Require application of the knowledge
3. Explore connections to other topics

Respond in JSON format:
{{
  "related_questions": [
    {{
      "question": "related question 1",
      "relationship": "how it relates to original"
    }},
    ...
  ]
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    # ============= VALIDATION TEMPLATES =============

    VALIDATE_ANSWER = PromptTemplate(
        name="validate_answer",
        task_type=TaskType.VALIDATE_ANSWER,
        system_prompt="You are an expert fact-checker and educator. Validate answers for accuracy and completeness.",
        template="""Validate if the following answer correctly and completely answers the question.

Question: {question}
Answer: {answer}

Respond in JSON format:
{{
  "valid": true|false,
  "accuracy": "fully_accurate|mostly_accurate|partially_accurate|inaccurate",
  "completeness": "complete|mostly_complete|incomplete",
  "issues": ["issue1", "issue2"],
  "suggestions": "suggestions for improvement if needed"
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    # ============= BATCH PROCESSING TEMPLATES =============

    BATCH_ENHANCE = PromptTemplate(
        name="batch_enhance",
        task_type=TaskType.ENHANCE_CARD,
        template="""Improve the following {count} flashcards. Make them clear, accurate, and concise.

{cards_text}

Respond in JSON format with an array of improved cards:
{{
  "enhanced_cards": [
    {{
      "original_question": "...",
      "improved_question": "...",
      "improved_answer": "..."
    }},
    ...
  ]
}}

Respond with ONLY valid JSON.""",
        response_format="json"
    )

    @classmethod
    def get_template(cls, task_type: TaskType) -> Optional[PromptTemplate]:
        """Get the default template for a task type."""
        template_map = {
            TaskType.ENHANCE_CARD: cls.ENHANCE_CARD,
            TaskType.GENERATE_QA: cls.GENERATE_QA,
            TaskType.CATEGORIZE: cls.CATEGORIZE_CARD,
            TaskType.ASSESS_DIFFICULTY: cls.ASSESS_DIFFICULTY,
            TaskType.EXTRACT_KEY_POINTS: cls.EXTRACT_KEY_POINTS,
            TaskType.GENERATE_RELATED: cls.GENERATE_RELATED,
            TaskType.VALIDATE_ANSWER: cls.VALIDATE_ANSWER,
        }
        return template_map.get(task_type)

    @classmethod
    def get_all_templates(cls) -> Dict[str, PromptTemplate]:
        """Get all available templates."""
        return {
            "enhance_card": cls.ENHANCE_CARD,
            "enhance_card_context": cls.ENHANCE_CARD_CONTEXT,
            "generate_qa": cls.GENERATE_QA,
            "generate_qa_multiple": cls.GENERATE_QA_MULTIPLE,
            "categorize_card": cls.CATEGORIZE_CARD,
            "categorize_with_reasoning": cls.CATEGORIZE_WITH_REASONING,
            "assess_difficulty": cls.ASSESS_DIFFICULTY,
            "assess_difficulty_detailed": cls.ASSESS_DIFFICULTY_DETAILED,
            "extract_key_points": cls.EXTRACT_KEY_POINTS,
            "generate_related": cls.GENERATE_RELATED,
            "validate_answer": cls.VALIDATE_ANSWER,
            "batch_enhance": cls.BATCH_ENHANCE,
        }


class PromptBuilder:
    """Builder for creating custom prompts with advanced features."""

    def __init__(self, base_template: str):
        """Initialize with a base template."""
        self.base_template = base_template
        self.examples = []
        self.system_prompt = None
        self.constraints = []

    def add_example(self, input_text: str, output_text: str) -> 'PromptBuilder':
        """Add a few-shot example."""
        self.examples.append({"input": input_text, "output": output_text})
        return self

    def set_system_prompt(self, system_prompt: str) -> 'PromptBuilder':
        """Set the system prompt."""
        self.system_prompt = system_prompt
        return self

    def add_constraint(self, constraint: str) -> 'PromptBuilder':
        """Add a constraint or instruction."""
        self.constraints.append(constraint)
        return self

    def build(self, **format_args) -> str:
        """Build the final prompt."""
        prompt_parts = []

        if self.system_prompt:
            prompt_parts.append(f"System: {self.system_prompt}\n")

        if self.examples:
            prompt_parts.append("Examples:")
            for i, example in enumerate(self.examples, 1):
                prompt_parts.append(f"\nExample {i}:")
                prompt_parts.append(f"Input: {example['input']}")
                prompt_parts.append(f"Output: {example['output']}")
            prompt_parts.append("\n---\n")

        prompt_parts.append(self.base_template.format(**format_args))

        if self.constraints:
            prompt_parts.append("\nConstraints:")
            for constraint in self.constraints:
                prompt_parts.append(f"- {constraint}")

        return "\n".join(prompt_parts)


if __name__ == '__main__':
    # Example usage
    print("Available Prompt Templates:\n")
    
    for name, template in PromptTemplates.get_all_templates().items():
        print(f"✓ {name}")
        print(f"  Task: {template.task_type.value}")
        print(f"  Format: {template.response_format}")
        print()
    
    # Example: format a template
    print("\nExample - Enhance Card Prompt:")
    prompt = PromptTemplates.ENHANCE_CARD.format(
        question="What is photosynthesis?",
        answer="Process where plants make energy from sunlight."
    )
    print(prompt)
    
    # Example: use PromptBuilder
    print("\n\nExample - Custom Prompt with Examples:")
    builder = PromptBuilder(
        "Create a flashcard question from this text: {text}"
    )
    builder.set_system_prompt("You are an expert educator.")
    builder.add_example(
        "Plants use sunlight for energy",
        "Q: What do plants use for energy? A: Sunlight"
    )
    builder.add_constraint("Keep questions concise (under 20 words)")
    builder.add_constraint("Make answers complete but brief")
    
    custom_prompt = builder.build(text="Photosynthesis is the process by which plants convert light energy into chemical energy.")
    print(custom_prompt)
