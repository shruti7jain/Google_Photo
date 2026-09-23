import os
import json
import time
from typing import Type, TypeVar, Any
from pydantic import BaseModel, ValidationError
from loguru import logger
from groq import Groq

T = TypeVar('T', bound=BaseModel)

class PromptRunner:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        self.client = Groq(api_key=api_key)
        self.model = "openai/gpt-oss-20b"
        self.max_retries = 3

    def load_prompt(self, template_path: str, **kwargs) -> str:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        return template.format(**kwargs)

    def run_prompt(self, prompt: str, schema_class: Type[T]) -> T:
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from LLM")
                    
                parsed_json = json.loads(content)
                return schema_class(**parsed_json)
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Attempt {attempt+1}/{self.max_retries} failed to parse/validate output: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2)
            except Exception as e:
                logger.error(f"API Error: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(5)
