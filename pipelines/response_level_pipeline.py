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
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"Response Level Pipeline initialized in {self.mode} mode")
        self.logger.info(f"Available levels: {[level['name'] for level in self.levels]}")

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
            Modified user message with response level instruction
        """
        try:
            # Get current level configuration
            current_level = self.get_current_level()
            
            # Log the pipeline action
            self.logger.info(f"Processing message with level: {current_level['name']}")
            self.logger.info(f"Original message: {user_message[:100]}...")
            
            # Modify message based on current level
            if current_level["modifier"]:
                modified_message = f"{user_message} {current_level['modifier']}"
            else:
                modified_message = user_message
            
            # Advance to next level for next request (auto-cycle mode)
            if self.mode == "auto-cycle":
                self.advance_level()
                next_level = self.levels[self.current_level_index]
                self.logger.info(f"Next level will be: {next_level['name']}")
            
            self.logger.info(f"Modified message: {modified_message[:150]}...")
            
            return modified_message
            
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}")
            # Return original message if pipeline fails
            return user_message

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