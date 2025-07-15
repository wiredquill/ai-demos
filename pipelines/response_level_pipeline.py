"""
Response Level Pipeline for Open WebUI
Automatically cycles through different response complexity levels.

This pipeline modifies user messages to request responses at different complexity levels:
- Default: No modification
- Kid Mode (5-year-old): Simple explanations with fun examples
- Young Scientist (12-year-old): Age-appropriate science details
- College Student: Technical context with examples
- Scientific: Full technical detail and precise terminology

The pipeline cycles through levels automatically for testing purposes.
"""

from typing import List, Optional
import os
import json
import logging
import requests

class Pipeline:
    """Open WebUI Pipeline for Response Level Management"""
    
    def __init__(self):
        # Pipeline metadata required by Open WebUI
        self.name = "Response Level Pipeline"
        self.id = "response_level"
        self.description = "Cycles through different response complexity levels automatically"
        self.version = "1.0.0"
        
        # Response level configurations
        self.levels = [
            {
                "name": "Default",
                "modifier": "",
                "description": "Standard response without modification"
            },
            {
                "name": "Kid Mode", 
                "modifier": "Explain like I'm 5 years old using simple words, fun examples, and easy-to-understand concepts.",
                "description": "Simple explanations perfect for young children"
            },
            {
                "name": "Young Scientist",
                "modifier": "Explain like I'm 12 years old with some science details but keep it understandable and engaging.",
                "description": "Age-appropriate science explanations for curious pre-teens"
            },
            {
                "name": "College Student", 
                "modifier": "Explain like I'm a college student with technical context, examples, and deeper analysis.",
                "description": "Detailed technical explanations with educational context"
            },
            {
                "name": "Scientific",
                "modifier": "Give me the full scientific explanation with precise terminology, detailed mechanisms, and technical accuracy.",
                "description": "Complete technical detail for scientific understanding"
            }
        ]
        
        # Initialize cycling state
        self.current_level_index = 0
        self.mode = os.getenv("PIPELINE_MODE", "auto-cycle")  # "auto-cycle" or "manual"
        self.selected_level = 0  # For manual mode
        
        # Ollama connection configuration
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama-service:11434")
        if self.ollama_base_url.endswith('/'):
            self.ollama_base_url = self.ollama_base_url[:-1]
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"Response Level Pipeline initialized in {self.mode} mode")
        self.logger.info(f"Available levels: {[level['name'] for level in self.levels]}")
        self.logger.info(f"Ollama backend URL: {self.ollama_base_url}")

    def get_current_level(self):
        """Get the current response level configuration"""
        if self.mode == "auto-cycle":
            return self.levels[self.current_level_index]
        else:
            return self.levels[self.selected_level]

    def advance_level(self):
        """Advance to the next level (auto-cycle mode)"""
        if self.mode == "auto-cycle":
            self.current_level_index = (self.current_level_index + 1) % len(self.levels)

    def set_level(self, level_index: int):
        """Set specific level (manual mode)"""
        if 0 <= level_index < len(self.levels):
            self.selected_level = level_index
            self.logger.info(f"Level set to: {self.levels[level_index]['name']}")

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> str:
        """
        Main pipeline function called by Open WebUI
        
        Args:
            user_message: The user's input message
            model_id: The selected model identifier  
            messages: List of conversation messages
            body: Request body from Open WebUI
            
        Returns:
            AI response from Ollama with modified prompt
        """
        try:
            # Get current level configuration
            current_level = self.get_current_level()
            
            # Log the pipeline action
            self.logger.info(f"Processing message with level: {current_level['name']}")
            self.logger.info(f"Original message: {user_message[:100]}...")
            
            # Modify the last user message based on current level
            modified_messages = messages.copy()
            if current_level["modifier"] and modified_messages:
                # Find the last user message and modify it
                for i in range(len(modified_messages) - 1, -1, -1):
                    if modified_messages[i].get("role") == "user":
                        original_content = modified_messages[i]["content"]
                        modified_messages[i]["content"] = f"{original_content} {current_level['modifier']}"
                        break
            elif current_level["modifier"]:
                # If no messages, create a new modified message
                modified_messages = [{"role": "user", "content": f"{user_message} {current_level['modifier']}"}]
            
            # Advance to next level for next request (auto-cycle mode)
            if self.mode == "auto-cycle":
                self.advance_level()
                next_level = self.levels[self.current_level_index]
                self.logger.info(f"Next level will be: {next_level['name']}")
            
            self.logger.info(f"Modified message: {modified_messages[-1]['content'][:150] if modified_messages else 'No messages'}...")
            
            # Forward the modified request to Ollama
            try:
                ollama_response = self._forward_to_ollama(model_id, modified_messages)
                self.logger.info(f"Ollama response received: {ollama_response[:100] if ollama_response else 'Empty'}...")
                return ollama_response
            except Exception as ollama_error:
                self.logger.error(f"Ollama forwarding failed: {str(ollama_error)}")
                return f"Pipeline processed the request with level '{current_level['name']}', but failed to get AI response: {str(ollama_error)}"
            
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}")
            return f"Pipeline error: {str(e)}"

    def _forward_to_ollama(self, model_id: str, messages: List[dict]) -> str:
        """Forward the modified request to Ollama and return the response"""
        try:
            # Prepare the request payload for Ollama
            payload = {
                "model": model_id,
                "messages": messages,
                "stream": False
            }
            
            # Make the request to Ollama
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            content = response_data.get('message', {}).get('content', '')
            
            if content:
                return content
            else:
                return "No response content received from Ollama"
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to Ollama: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing Ollama response: {str(e)}")

    def get_info(self) -> dict:
        """Return pipeline information for Open WebUI"""
        return {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "version": self.version,
            "mode": self.mode,
            "current_level": self.get_current_level()["name"],
            "available_levels": [level["name"] for level in self.levels]
        }

    def get_status(self) -> dict:
        """Return current pipeline status"""
        current_level = self.get_current_level()
        return {
            "active": True,
            "mode": self.mode,
            "current_level": current_level["name"],
            "current_index": self.current_level_index if self.mode == "auto-cycle" else self.selected_level,
            "total_levels": len(self.levels),
            "description": current_level["description"]
        }


# Required for Open WebUI pipeline loading
def load_pipeline():
    """Factory function required by Open WebUI"""
    return Pipeline()


# For testing the pipeline independently
if __name__ == "__main__":
    # Test the pipeline
    pipeline = Pipeline()
    
    test_message = "Why is the sky blue?"
    print(f"Testing pipeline with message: '{test_message}'")
    print()
    
    # Test all levels
    for i in range(len(pipeline.levels)):
        current_status = pipeline.get_status()
        print(f"Level {i+1}: {current_status['current_level']}")
        result = pipeline.pipe(test_message, "test-model", [], {})
        next_status = pipeline.get_status()
        print(f"Result: {result}")
        print(f"Next: {next_status['current_level']}")
        print("-" * 80)