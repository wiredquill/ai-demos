#!/usr/bin/env python3
"""
HTTP Load Simulator for AI Compare
Generates predictable HTTP traffic patterns for SUSE Observability monitoring.
Replaces the Gradio automation functionality with dedicated external load generation.
"""

import json
import logging
import os
import random
import time
from typing import List, Dict
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class LoadSimulator:
    """HTTP load simulator for AI Compare observability."""
    
    def __init__(self):
        # Configuration from environment variables
        self.target_url = os.getenv("TARGET_URL", "http://ai-compare-app-service:8080")
        self.interval_seconds = int(os.getenv("INTERVAL_SECONDS", "30"))
        self.enabled = os.getenv("LOAD_SIMULATOR_ENABLED", "true").lower() == "true"
        
        # HTTP timeouts
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        
        # Load simulation configuration
        self.prompts = self._load_prompts()
        self.current_prompt_index = 0
        
        logger.info(f"Load Simulator initialized:")
        logger.info(f"  Target URL: {self.target_url}")
        logger.info(f"  Interval: {self.interval_seconds} seconds")
        logger.info(f"  Enabled: {self.enabled}")
        logger.info(f"  Prompts loaded: {len(self.prompts)}")
    
    def _load_prompts(self) -> List[str]:
        """Load prompts from environment or use defaults."""
        # Try to load from environment variable (JSON array)
        prompts_env = os.getenv("LOAD_PROMPTS")
        if prompts_env:
            try:
                return json.loads(prompts_env)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LOAD_PROMPTS JSON: {e}")
        
        # Default prompts for load generation
        return [
            "Why is the sky blue? Please explain in simple terms.",
            "What is artificial intelligence and how does it work?",
            "Explain the difference between machine learning and deep learning.",
            "How do large language models generate text?",
            "What are the benefits of using containers in software development?",
            "Describe the importance of observability in modern applications.",
            "What is Kubernetes and why is it useful?",
            "Explain the concept of microservices architecture.",
            "How does HTTPS encryption work?",
            "What are the advantages of using SUSE Linux Enterprise?",
        ]
    
    def _get_next_prompt(self) -> str:
        """Get the next prompt in rotation."""
        prompt = self.prompts[self.current_prompt_index]
        self.current_prompt_index = (self.current_prompt_index + 1) % len(self.prompts)
        return prompt
    
    def _send_chat_request(self, prompt: str) -> Dict:
        """Send a chat request to the AI Compare API."""
        url = f"{self.target_url}/api/chat"
        payload = {
            "message": prompt,
            "model": "tinyllama:latest"
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LoadSimulator/1.0"
        }
        
        try:
            logger.info(f"Sending chat request: '{prompt[:50]}...'")
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=self.request_timeout
            )
            
            result = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                "prompt": prompt
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["response_data"] = data
                    logger.info(f"Chat request successful ({result['response_time_ms']}ms)")
                except json.JSONDecodeError:
                    result["error"] = "Invalid JSON response"
                    logger.warning("Chat request returned invalid JSON")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(f"Chat request failed: {result['error']}")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Chat request timed out after {self.request_timeout}s")
            return {
                "status_code": 0,
                "success": False,
                "error": f"Request timed out after {self.request_timeout}s",
                "prompt": prompt
            }
        except Exception as e:
            logger.error(f"Chat request failed: {e}")
            return {
                "status_code": 0,
                "success": False,
                "error": str(e),
                "prompt": prompt
            }
    
    def _send_health_check(self) -> Dict:
        """Send a health check request."""
        url = f"{self.target_url}/health"
        
        try:
            response = requests.get(url, timeout=5)
            result = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000)
            }
            
            if response.status_code == 200:
                logger.debug(f"Health check successful ({result['response_time_ms']}ms)")
            else:
                logger.warning(f"Health check failed: HTTP {response.status_code}")
            
            return result
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return {
                "status_code": 0,
                "success": False,
                "error": str(e)
            }
    
    def _send_metrics_request(self) -> Dict:
        """Send a metrics request."""
        url = f"{self.target_url}/api/metrics"
        
        try:
            response = requests.get(url, timeout=10)
            result = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000)
            }
            
            if response.status_code == 200:
                logger.debug(f"Metrics request successful ({result['response_time_ms']}ms)")
            else:
                logger.warning(f"Metrics request failed: HTTP {response.status_code}")
            
            return result
            
        except Exception as e:
            logger.warning(f"Metrics request failed: {e}")
            return {
                "status_code": 0,
                "success": False,
                "error": str(e)
            }
    
    def run_load_cycle(self) -> Dict:
        """Run one complete load simulation cycle."""
        cycle_start = time.time()
        
        # 1. Health check
        health_result = self._send_health_check()
        
        # 2. Chat request with rotating prompt
        prompt = self._get_next_prompt()
        chat_result = self._send_chat_request(prompt)
        
        # 3. Metrics request (every 3rd cycle to reduce noise)
        metrics_result = None
        if self.current_prompt_index % 3 == 0:
            metrics_result = self._send_metrics_request()
        
        cycle_time = time.time() - cycle_start
        
        cycle_summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cycle_time_ms": int(cycle_time * 1000),
            "health_check": health_result,
            "chat_request": chat_result,
            "metrics_request": metrics_result
        }
        
        # Log cycle summary
        health_status = "✅" if health_result["success"] else "❌"
        chat_status = "✅" if chat_result["success"] else "❌"
        
        logger.info(f"Load cycle completed: {health_status} Health, {chat_status} Chat ({cycle_time:.1f}s)")
        
        return cycle_summary
    
    def run(self):
        """Main load simulation loop."""
        if not self.enabled:
            logger.info("Load simulator is disabled. Set LOAD_SIMULATOR_ENABLED=true to enable.")
            # Keep container running but idle
            while True:
                time.sleep(60)
                logger.debug("Load simulator disabled, sleeping...")
            return
        
        logger.info("Starting load simulation...")
        logger.info(f"Will send requests every {self.interval_seconds} seconds")
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                logger.info(f"--- Load Cycle #{cycle_count} ---")
                
                # Run load cycle
                cycle_result = self.run_load_cycle()
                
                # Wait for next interval
                logger.info(f"Waiting {self.interval_seconds} seconds until next cycle...")
                time.sleep(self.interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Load simulator stopped by user")
        except Exception as e:
            logger.error(f"Load simulator crashed: {e}")
            raise


def main():
    """Main entry point."""
    simulator = LoadSimulator()
    simulator.run()


if __name__ == "__main__":
    main()