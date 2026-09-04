"""Ollama client for integrating local LLM models.

This module handles:
- Connection to locally-hosted Ollama instances
- Sending prompts and receiving responses
- Batch processing of flashcards
- Response parsing and formatting
- Error handling and retry logic
"""

import requests
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from loguru import logger
import yaml


@dataclass
class OllamaConfig:
    """Configuration for Ollama connection."""
    host: str = "http://localhost:11434"
    model: str = "mistral"
    timeout: int = 300
    temperature: float = 0.7
    top_p: float = 0.9
    retries: int = 3
    retry_delay: int = 2


class OllamaClient:
    """Client for interacting with Ollama LLM."""

    def __init__(self, config: Optional[OllamaConfig] = None, config_path: Optional[str] = None):
        """Initialize Ollama client.
        
        Args:
            config: OllamaConfig object (takes precedence over config_path)
            config_path: Path to YAML config file
        """
        if config:
            self.config = config
        elif config_path:
            self.config = self._load_config(config_path)
        else:
            self.config = OllamaConfig()
        
        self.session = requests.Session()
        self._verify_connection()
        logger.info(f"Ollama client initialized: {self.config.host} (model: {self.config.model})")

    def _load_config(self, config_path: str) -> OllamaConfig:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
                ollama_config = config_dict.get('ollama', {})
                return OllamaConfig(**ollama_config)
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}. Using defaults.")
            return OllamaConfig()

    def _verify_connection(self) -> bool:
        """Verify connection to Ollama."""
        try:
            response = self.session.get(f"{self.config.host}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to Ollama")
                return True
        except Exception as e:
            logger.warning(f"Could not connect to Ollama at {self.config.host}: {e}")
            return False

    def generate(self, prompt: str, stream: bool = False) -> str:
        """Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the model
            stream: Whether to stream the response
        
        Returns:
            Generated text response
        """
        for attempt in range(self.config.retries):
            try:
                payload = {
                    "model": self.config.model,
                    "prompt": prompt,
                    "stream": stream,
                    "options": {
                        "temperature": self.config.temperature,
                        "top_p": self.config.top_p
                    }
                }
                
                response = self.session.post(
                    f"{self.config.host}/api/generate",
                    json=payload,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    if stream:
                        return self._parse_stream(response)
                    else:
                        data = response.json()
                        return data.get('response', '').strip()
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    if attempt < self.config.retries - 1:
                        time.sleep(self.config.retry_delay)
                        continue
            
            except requests.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.config.retries}")
                if attempt < self.config.retries - 1:
                    time.sleep(self.config.retry_delay)
                    continue
            except Exception as e:
                logger.error(f"Error generating response (attempt {attempt + 1}): {e}")
                if attempt < self.config.retries - 1:
                    time.sleep(self.config.retry_delay)
                    continue
        
        logger.error(f"Failed to generate response after {self.config.retries} attempts")
        return ""

    def _parse_stream(self, response) -> str:
        """Parse streamed response from Ollama."""
        full_response = ""
        try:
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    full_response += data.get('response', '')
        except Exception as e:
            logger.error(f"Error parsing stream: {e}")
        return full_response.strip()

    def enhance_flashcard(self, question: str, answer: str) -> Tuple[str, str]:
        """Enhance a flashcard using the LLM.
        
        Improves clarity, conciseness, and correctness of Q&A pairs.
        
        Args:
            question: Original question
            answer: Original answer
        
        Returns:
            Tuple of (improved_question, improved_answer)
        """
        prompt = f"""Improve the following flashcard question and answer. Make them clear, concise, and educational.

Original Question: {question}
Original Answer: {answer}

Provide the improved version in JSON format:
{{
  "question": "improved question",
  "answer": "improved answer"
}}

Only respond with valid JSON, no other text."""
        
        try:
            response = self.generate(prompt)
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return data.get('question', question), data.get('answer', answer)
        except Exception as e:
            logger.warning(f"Error enhancing flashcard: {e}")
        
        return question, answer

    def generate_qa_pair(self, text: str) -> Optional[Dict[str, str]]:
        """Generate a Q&A pair from text using the LLM.
        
        Args:
            text: Source text to generate Q&A from
        
        Returns:
            Dict with 'question' and 'answer' keys, or None if failed
        """
        prompt = f"""Generate a single educational question and answer from the following text.
Focus on key concepts and facts.

Text: {text}

Respond in JSON format:
{{
  "question": "your question",
  "answer": "your answer"
}}

Only respond with valid JSON, no other text."""
        
        try:
            response = self.generate(prompt)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                if 'question' in data and 'answer' in data:
                    return data
        except Exception as e:
            logger.warning(f"Error generating QA pair: {e}")
        
        return None

    def categorize_card(self, question: str, answer: str,
                       categories: List[str]) -> str:
        """Categorize a flashcard using the LLM.
        
        Args:
            question: Flashcard question
            answer: Flashcard answer
            categories: List of possible categories
        
        Returns:
            Selected category
        """
        categories_str = ", ".join(categories)
        prompt = f"""Categorize the following flashcard into ONE of these categories: {categories_str}

Question: {question}
Answer: {answer}

Respond with ONLY the category name, nothing else."""
        
        try:
            response = self.generate(prompt).strip()
            if response in categories:
                return response
            # Try to find close match
            for cat in categories:
                if cat.lower() in response.lower():
                    return cat
        except Exception as e:
            logger.warning(f"Error categorizing card: {e}")
        
        return categories[0] if categories else "uncategorized"

    def assess_difficulty(self, question: str, answer: str) -> str:
        """Assess difficulty level of a flashcard.
        
        Args:
            question: Flashcard question
            answer: Flashcard answer
        
        Returns:
            Difficulty level: 'easy', 'medium', or 'hard'
        """
        prompt = f"""Assess the difficulty level of this flashcard.
Respond with ONLY one word: easy, medium, or hard.

Question: {question}
Answer: {answer}"""
        
        try:
            response = self.generate(prompt).strip().lower()
            if 'easy' in response:
                return 'easy'
            elif 'hard' in response:
                return 'hard'
            else:
                return 'medium'
        except Exception as e:
            logger.warning(f"Error assessing difficulty: {e}")
            return 'medium'

    def batch_enhance(self, flashcards: List[Dict], batch_size: int = 5) -> List[Dict]:
        """Enhance multiple flashcards with rate limiting.
        
        Args:
            flashcards: List of dicts with 'question' and 'answer'
            batch_size: Number of cards to process before delay
        
        Returns:
            List of enhanced flashcard dicts
        """
        enhanced = []
        
        for i, card in enumerate(flashcards):
            try:
                question, answer = self.enhance_flashcard(
                    card.get('question', ''),
                    card.get('answer', '')
                )
                
                enhanced_card = card.copy()
                enhanced_card['question'] = question
                enhanced_card['answer'] = answer
                enhanced.append(enhanced_card)
                
                # Rate limiting
                if (i + 1) % batch_size == 0:
                    logger.info(f"Processed {i + 1}/{len(flashcards)} cards")
                    time.sleep(1)  # Brief delay between batches
            
            except Exception as e:
                logger.warning(f"Error enhancing card {i}: {e}")
                enhanced.append(card)  # Keep original if enhancement fails
        
        return enhanced

    def get_available_models(self) -> List[str]:
        """Get list of available models on this Ollama instance.
        
        Returns:
            List of model names
        """
        try:
            response = self.session.get(f"{self.config.host}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [model['name'].split(':')[0] for model in data.get('models', [])]
                return list(set(models))
        except Exception as e:
            logger.error(f"Error getting models: {e}")
        
        return []

    def set_model(self, model: str) -> bool:
        """Change the active model.
        
        Args:
            model: Model name
        
        Returns:
            True if model exists and was set
        """
        available = self.get_available_models()
        if model in available:
            self.config.model = model
            logger.info(f"Model changed to: {model}")
            return True
        else:
            logger.error(f"Model {model} not found. Available: {available}")
            return False


if __name__ == '__main__':
    import sys
    
    # Example usage
    client = OllamaClient()
    
    # Check available models
    models = client.get_available_models()
    print(f"Available models: {models}")
    
    # Test generation
    prompt = "What is photosynthesis? Explain briefly."
    print(f"\nPrompt: {prompt}")
    response = client.generate(prompt)
    print(f"Response: {response}")
    
    # Test card enhancement
    print("\n--- Testing Card Enhancement ---")
    q = "What is photosynthesis?"
    a = "Process where plants convert light to energy."
    q_enhanced, a_enhanced = client.enhance_flashcard(q, a)
    print(f"Original Q: {q}")
    print(f"Enhanced Q: {q_enhanced}")
    print(f"Original A: {a}")
    print(f"Enhanced A: {a_enhanced}")
