import gradio as gr
import requests
import json
import threading
import time
import os
import logging
import queue
from typing import Dict, List, Any

# Build trigger comment - automation runner visibility improvements

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
# --- End Logging Configuration ---

class ChatInterface:
    """
    Manages the application state and logic for the Gradio chat interface.
    """
    def __init__(self):
        self.config_path = 'config.json'
        self.config = self.load_or_create_config()

        # Initialize provider status with pre-drawn boxes (default offline)
        self.provider_status = {}
        for name, provider_info in self.config.get('providers', {}).items():
            if isinstance(provider_info, str):
                country = "🌍 Unknown"
                flag = "🌍"
            else:
                country = provider_info.get('country', '🌍 Unknown')
                flag = provider_info.get('flag', '🌍')
            
            self.provider_status[name] = {
                "status": "🔴",
                "response_time": "---ms",
                "country": country,
                "flag": flag,
                "status_code": "Loading"
            }
        
        # --- MODIFIED: Load URLs from environment variables for K8s ---
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.open_webui_base_url = os.getenv("OPEN_WEBUI_BASE_URL")
        
        if self.open_webui_base_url:
            self.config.setdefault('providers', {})['Open WebUI'] = self.open_webui_base_url
        
        if self.ollama_base_url.endswith('/'):
            self.ollama_base_url = self.ollama_base_url[:-1]

        self.ollama_models = []
        self.selected_model = ""

        # --- NEW: Automation Runner State ---
        # Read automation settings from environment variables
        self.automation_enabled = os.getenv("AUTOMATION_ENABLED", "false").lower() == "true"
        self.automation_interval = int(os.getenv("AUTOMATION_INTERVAL", "30"))
        self.automation_send_messages = os.getenv("AUTOMATION_SEND_MESSAGES", "true").lower() == "true"
        
        # Built-in rotating prompts for automation
        self.automation_prompts = [
            "Why is the sky blue?",
            "Why is the sky blue? Explain like I'm 5 years old.",
            "Why is the sky blue? Explain like I'm 12 years old.",
            "Why is the sky blue? Explain like I'm a college student.",
            "Why is the sky blue? Give me the scientific explanation."
        ]
        self.current_prompt_index = 0
        
        # Thread management for the runner
        self.automation_thread = None
        self.stop_event = threading.Event()
        self.results_queue = queue.Queue()

        logger.info(f"ChatInterface initialized. Ollama URL: {self.ollama_base_url}, Open WebUI URL: {self.open_webui_base_url}")
        if self.automation_enabled:
            logger.info(f"Automation enabled with interval {self.automation_interval}s and {len(self.automation_prompts)} rotating prompts")

    def load_or_create_config(self) -> Dict:
        """Loads configuration from config.json, or creates it with defaults if it doesn't exist."""
        default_config = {
            "providers": {
                "OpenAI": {"url": "https://help.openai.com", "country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Claude (Anthropic)": {"url": "https://anthropic.com", "country": "🇺🇸 USA", "flag": "🇺🇸"},
                "DeepSeek": {"url": "https://api.deepseek.com", "country": "🇨🇳 China", "flag": "🇨🇳"},
                "Google Gemini": {"url": "https://ai.google.dev", "country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Cohere": {"url": "https://cohere.com", "country": "🇨🇦 Canada", "flag": "🇨🇦"},
                "Mistral AI": {"url": "https://mistral.ai", "country": "🇫🇷 France", "flag": "🇫🇷"},
                "Perplexity": {"url": "https://www.perplexity.ai", "country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Together AI": {"url": "https://together.ai", "country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Groq": {"url": "https://groq.com", "country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Hugging Face": {"url": "https://huggingface.co", "country": "🇺🇸 USA", "flag": "🇺🇸"}
            }
        }
        
        # In K8s, the config is mounted at /app/config.json
        if os.path.exists(self.config_path):
            logger.info(f"Loading configuration from {self.config_path}")
            with open(self.config_path, 'r') as f:
                try:
                    config_data = json.load(f)
                    config_data.setdefault('providers', default_config['providers'])
                    return config_data
                except json.JSONDecodeError:
                    logger.error("Error decoding config.json, using default config.")
                    return default_config
        else:
            logger.info(f"Creating default configuration file at {self.config_path}")
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def get_ollama_models(self) -> List[str]:
        """Fetches the list of available models from the Ollama /api/tags endpoint."""
        logger.info(f"Attempting to fetch Ollama models from {self.ollama_base_url}/api/tags")
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            if not models:
                logger.warning("No Ollama models found at the endpoint.")
                return ["No models found at Ollama endpoint."]
            logger.info(f"Successfully fetched Ollama models: {models}")
            self.ollama_models = models
            return models
        except Exception as e:
            logger.error(f"Error fetching Ollama models: {str(e)}")
            return ["Connection Error - Is Ollama running?"]

    def chat_with_ollama(self, messages: List[Dict[str, str]], model: str) -> str:
        """Sends a conversation history to the Ollama /api/chat endpoint."""
        logger.info(f"Attempting to chat with Ollama model: {model}")
        try:
            payload = { "model": model, "messages": messages, "stream": False }
            response = requests.post(f"{self.ollama_base_url}/api/chat", json=payload, timeout=120)
            response.raise_for_status()
            response_data = response.json()
            return response_data.get('message', {}).get('content', 'Error: Unexpected response format from Ollama.')
        except Exception as e:
            return f"Error communicating with Ollama: {str(e)}"

    def chat_with_open_webui(self, messages: List[Dict[str, str]], model: str) -> str:
        """Sends a conversation history with pipeline-modified prompts for response level cycling."""
        # Educational levels that the pipeline cycles through
        pipeline_levels = [
            {"name": "🎯 Default", "modifier": ""},
            {"name": "🧒 Kid Mode", "modifier": "Explain like I'm 5 years old using simple words, fun examples, and easy-to-understand concepts."},
            {"name": "🔬 Young Scientist", "modifier": "Explain like I'm 12 years old with some science details but keep it understandable and engaging."},
            {"name": "🎓 College Student", "modifier": "Explain like I'm a college student with technical context, examples, and deeper analysis."},
            {"name": "⚗️ Scientific", "modifier": "Give me the full scientific explanation with precise terminology, detailed mechanisms, and technical accuracy."}
        ]
        
        # Calculate which level to use (cycling every 30 seconds)
        import time
        level_index = int(time.time() / 30) % len(pipeline_levels)
        current_level = pipeline_levels[level_index]
        
        # Apply pipeline level modification to the message
        modified_messages = messages.copy()
        if modified_messages and current_level["modifier"]:
            last_message = modified_messages[-1]
            if last_message["role"] == "user":
                modified_messages[-1] = {
                    "role": "user",
                    "content": f"{last_message['content']} {current_level['modifier']}"
                }
        
        # Try Open WebUI first if available
        if self.open_webui_base_url:
            api_url = f"{self.open_webui_base_url}/ollama/api/chat"
            payload = { "model": model, "messages": modified_messages, "stream": False }
            
            logger.info(f"Attempting Open WebUI with pipeline level: {current_level['name']}")
            try:
                response = requests.post(api_url, json=payload, timeout=120)
                if response.status_code == 200:
                    response_data = response.json()
                    content = response_data.get('message', {}).get('content', 'Error: Unexpected response format from Open WebUI.')
                    
                    # Add pipeline level header to the response - this IS the pipeline working
                    formatted_response = f"🔄 **Pipeline Mode**: {current_level['name']} (via Open WebUI)\n\n{content}"
                    logger.info(f"Open WebUI response successful with level: {current_level['name']}")
                    return formatted_response
                else:
                    logger.warning(f"Open WebUI failed ({response.status_code}), falling back to direct Ollama")
            except Exception as e:
                logger.warning(f"Open WebUI failed: {str(e)}, falling back to direct Ollama")
        else:
            logger.info("No Open WebUI URL configured, using direct Ollama")
        
        # Fallback to direct Ollama with pipeline-modified prompt - this is STILL pipeline working!
        logger.info(f"Using direct Ollama with pipeline level: {current_level['name']}")
        ollama_response = self.chat_with_ollama(modified_messages, model)
        
        # Add pipeline level header - this is still pipeline functionality
        formatted_response = f"🔄 **Pipeline Mode**: {current_level['name']} (via Direct Ollama)\n\n{ollama_response}"
        return formatted_response

    def check_provider_status(self, provider_name: str, provider_info) -> dict:
        """Checks the status of a single provider and returns detailed info."""
        import time
        start_time = time.time()
        
        # Handle both old string format and new dict format
        if isinstance(provider_info, str):
            url = provider_info
            country = "🌍 Unknown"
            flag = "🌍"
        else:
            url = provider_info.get('url', provider_info)
            country = provider_info.get('country', '🌍 Unknown')
            flag = provider_info.get('flag', '🌍')
            
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, timeout=5, headers=headers)
            response_time = int((time.time() - start_time) * 1000)
            # Show as online if we get ANY response (even 403, 404, etc.)
            status = "🟢"
            logger.info(f"Provider {provider_name}: {response.status_code} -> {status} ({response_time}ms)")
            
            return {
                "status": status,
                "response_time": f"{response_time}ms",
                "country": country,
                "flag": flag,
                "status_code": response.status_code
            }
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.warning(f"Provider {provider_name} failed: {str(e)} ({response_time}ms)")
            return {
                "status": "🔴",
                "response_time": f"{response_time}ms",
                "country": country,
                "flag": flag,
                "status_code": "Error",
                "error": str(e)
            }

    def update_all_provider_status(self) -> Dict:
        """Updates all provider statuses and returns the status dictionary."""
        logger.info("Updating all provider statuses.")
        updated_status = {}
        # Simple loop without threading for this use case
        for name, provider_info in self.config.get('providers', {}).items():
            updated_status[name] = self.check_provider_status(name, provider_info)
        self.provider_status = updated_status
        return updated_status

    def get_provider_status_html(self) -> str:
        """Generates compact provider cards with flags and status."""
        # Calculate statistics
        total_providers = len(self.provider_status)
        online_count = sum(1 for info in self.provider_status.values() if isinstance(info, dict) and info.get('status') == '🟢')
        offline_count = total_providers - online_count
        
        # Calculate average response time
        response_times = []
        for info in self.provider_status.values():
            if isinstance(info, dict) and 'response_time' in info:
                try:
                    rt_str = info['response_time']
                    if 'ms' in rt_str and rt_str != '---ms':
                        rt = int(rt_str.replace('ms', ''))
                        response_times.append(rt)
                except:
                    pass
        avg_rt = int(sum(response_times) / len(response_times)) if response_times else 0
        
        html_content = f"""
        <div style='background: linear-gradient(135deg, #0c322c 0%, #1a4a3a 100%); padding: 15px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);'>
            <h3 style='color: #30ba78; margin: 0 0 15px 0; font-size: 16px; text-align: center; font-weight: 600;'>🌐 Provider Status</h3>
            
            <!-- Compact Provider List -->
            <div style='margin-bottom: 15px;'>
        """
        
        for name, info in sorted(self.provider_status.items()):
            if isinstance(info, dict):
                status = info.get('status', '🔴')
                flag = info.get('flag', '🌍')
                response_time = info.get('response_time', '---ms')
                
                html_content += f"""
                <div style='display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; margin-bottom: 4px; background: rgba(255,255,255,0.05); border-radius: 12px; border-left: 3px solid {"#28a745" if status == "🟢" else "#dc3545"};'>
                    <div style='display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0;'>
                        <span style='font-size: 14px; width: 18px; text-align: center; flex-shrink: 0;'>{flag}</span>
                        <span style='color: #ffffff; font-size: 12px; font-weight: 500; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{name}</span>
                    </div>
                    <div style='display: flex; align-items: center; gap: 8px; flex-shrink: 0; min-width: 80px;'>
                        <span style='font-size: 14px; width: 16px; text-align: center;'>{status}</span>
                        <span style='color: #a0a0a0; font-size: 10px; text-align: right; min-width: 45px; font-family: monospace;'>{response_time}</span>
                    </div>
                </div>
                """
            else:
                # Fallback for old format
                html_content += f"""
                <div style='display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; margin-bottom: 4px; background: rgba(255,255,255,0.05); border-radius: 12px;'>
                    <span style='color: #ffffff; font-size: 12px; font-weight: 500;'>{name}</span>
                    <span style='font-size: 14px;'>{info}</span>
                </div>
                """
        
        html_content += f"""
            </div>
            
            <!-- Compact Statistics -->
            <div style='background: linear-gradient(135deg, rgba(48, 186, 120, 0.1) 0%, rgba(48, 186, 120, 0.05) 100%); border: 1px solid rgba(48, 186, 120, 0.2); border-radius: 12px; padding: 12px; text-align: center;'>
                <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 11px;'>
                    <div style='text-align: center;'>
                        <div style='color: #28a745; font-weight: 700; font-size: 16px;'>{online_count}</div>
                        <div style='color: #ffffff; opacity: 0.8; font-size: 9px;'>Online</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='color: #dc3545; font-weight: 700; font-size: 16px;'>{offline_count}</div>
                        <div style='color: #ffffff; opacity: 0.8; font-size: 9px;'>Offline</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='color: #ffc107; font-weight: 700; font-size: 16px;'>{avg_rt}ms</div>
                        <div style='color: #ffffff; opacity: 0.8; font-size: 9px;'>Avg RT</div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        return html_content

    def refresh_providers(self) -> gr.HTML:
        """Manually refreshes provider statuses and returns the HTML."""
        logger.info("Manual provider refresh triggered.")
        self.update_all_provider_status()
        return gr.HTML(value=self.get_provider_status_html())

    def refresh_ollama_models(self) -> gr.Dropdown:
        """Refreshes the dropdown with models from Ollama."""
        logger.info("Refreshing Ollama models dropdown.")
        self.ollama_models = self.get_ollama_models()
        current_value = self.selected_model if self.selected_model in self.ollama_models else (self.ollama_models[0] if self.ollama_models and "Error" not in self.ollama_models[0] else "")
        self.selected_model = current_value
        return gr.Dropdown(choices=self.ollama_models, label="🤖 Ollama Model", value=current_value, allow_custom_value=True)

    # --- NEW: Automation Runner Methods ---
    def _automation_loop(self, model: str, interval: int):
        """The main loop for the background automation thread."""
        logger.info("Automation thread started.")
        while not self.stop_event.is_set():
            # Get the current prompt and rotate to next
            current_prompt = self.automation_prompts[self.current_prompt_index]
            self.current_prompt_index = (self.current_prompt_index + 1) % len(self.automation_prompts)
            
            logger.info(f"Running automated task with prompt: '{current_prompt}' (send_messages: {self.automation_send_messages})")
            
            # Initialize response variables
            ollama_reply = "Message sending disabled"
            webui_reply = "Message sending disabled"
            
            # Send messages to models only if enabled
            if self.automation_send_messages:
                # 1. Send to Ollama
                ollama_reply = self.chat_with_ollama([{"role": "user", "content": current_prompt}], model)
                
                # 2. Send to Open WebUI
                webui_reply = self.chat_with_open_webui([{"role": "user", "content": current_prompt}], model)
            else:
                logger.info("Skipping message sending - automation_send_messages is disabled")
            
            # 3. Always check providers (this is the ping/monitoring functionality)
            provider_statuses = self.update_all_provider_status()

            # Create result package
            result = {
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "prompt": current_prompt if self.automation_send_messages else "Monitoring only",
                "ollama_response": ollama_reply,
                "open_webui_response": webui_reply,
                "provider_status": provider_statuses,
                "send_messages_enabled": self.automation_send_messages
            }
            # Put the result in the queue for the UI to pick up
            self.results_queue.put(result)
            
            # Wait for the next interval
            self.stop_event.wait(interval)
        logger.info("Automation thread stopped.")

    def start_automation(self, model: str, interval: int, send_messages: bool = None):
        """Starts the automation thread."""
        if self.automation_thread and self.automation_thread.is_alive():
            logger.warning("Automation is already running.")
            return gr.Button(interactive=False), gr.Button(interactive=True)

        if not model or "Error" in model or "No models" in model:
            logger.error("Cannot start automation without a valid model selected.")
            return gr.Button(interactive=True), gr.Button(interactive=False)

        # Update send messages setting if provided
        if send_messages is not None:
            self.automation_send_messages = send_messages
            logger.info(f"Automation send messages setting updated to: {send_messages}")

        self.stop_event.clear()
        self.automation_thread = threading.Thread(
            target=self._automation_loop,
            args=(model, interval),
            daemon=True
        )
        self.automation_thread.start()
        logger.info(f"Automation started with interval {interval}s, send_messages: {self.automation_send_messages}")
        # UI update to show it's running
        return gr.Button(interactive=False), gr.Button(interactive=True)

    def stop_automation(self):
        """Stops the automation thread."""
        if self.automation_thread and self.automation_thread.is_alive():
            self.stop_event.set()
        logger.info("Automation stopping.")
        return gr.Button(interactive=True), gr.Button(interactive=False)

def create_interface():
    logger.info("Creating Gradio interface.")
    chat_instance = ChatInterface()
    
    css = """
    .gradio-container { 
        background: linear-gradient(135deg, #0a2f26 0%, #0c322c 50%, #0f3a2f 100%); 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        color: #efefef; 
        min-height: 100vh;
    }
    .main-header { 
        background: linear-gradient(135deg, #30ba78 0%, #28a745 100%); 
        border: 1px solid #30ba78; 
        border-radius: 15px; 
        box-shadow: 0 8px 32px rgba(48, 186, 120, 0.3); 
        padding: 25px; 
        margin-bottom: 25px; 
    }
    .control-panel, .chat-container { 
        background: rgba(255, 255, 255, 0.05); 
        border: 1px solid rgba(48, 186, 120, 0.2); 
        border-radius: 15px; 
        padding: 20px; 
        backdrop-filter: blur(10px);
    }
    h1, h2, h3, h4 { color: #ffffff; font-weight: 600; }
    .gr-button { 
        background: #73ba25; 
        color: #ffffff; 
        border: none; 
        border-radius: 6px; 
        box-shadow: 0 2px 8px rgba(115, 186, 37, 0.3); 
        font-weight: 600; 
        transition: all 0.3s ease;
    }
    .gr-button:hover { 
        background: #5a9e1c; 
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(115, 186, 37, 0.4);
    }
    .refresh-btn { 
        background: linear-gradient(135deg, #2453ff 0%, #4f75ff 100%); 
    } 
    .refresh-btn:hover { 
        background: linear-gradient(135deg, #4f75ff 0%, #6c8cff 100%); 
    }
    .stop-btn { 
        background: linear-gradient(135deg, #dc3545 0%, #e04f5e 100%); 
    } 
    .stop-btn:hover { 
        background: linear-gradient(135deg, #e04f5e 0%, #e8606f 100%); 
    }
    .gr-textbox { 
        background: #ffffff; 
        border: 2px solid #73ba25; 
        border-radius: 8px; 
        color: #000000;
        box-shadow: 0 2px 8px rgba(115, 186, 37, 0.2);
    }
    .gr-textbox:focus { 
        border-color: #73ba25; 
        box-shadow: 0 0 12px rgba(115, 186, 37, 0.4); 
        background: #ffffff;
    }
    .gr-textbox textarea, .gr-textbox input {
        background: #ffffff !important;
        color: #000000 !important;
        font-size: 14px;
        line-height: 1.5;
    }
    .gr-textbox textarea::placeholder, .gr-textbox input::placeholder {
        color: #666666 !important;
        font-style: italic;
    }
    .gr-dropdown { 
        background: #ffffff; 
        border: 2px solid #73ba25; 
        border-radius: 8px; 
        box-shadow: 0 2px 8px rgba(115, 186, 37, 0.2);
    }
    .gr-dropdown:focus-within {
        border-color: #73ba25;
        box-shadow: 0 0 12px rgba(115, 186, 37, 0.4);
    }
    .gr-group {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.08) 100%);
        border: 2px solid rgba(48, 186, 120, 0.2);
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(15px);
        position: relative;
        overflow: hidden;
    }
    .gr-group::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(48, 186, 120, 0.5), transparent);
    }
    /* Modern AI Response boxes with consistent rounded styling */
    .ollama-response .gr-textbox {
        background: linear-gradient(145deg, #f8fffe 0%, #f1f8e9 100%);
        border: 2px solid #4CAF50;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(76, 175, 80, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.6);
        position: relative;
        overflow: hidden;
    }
    .ollama-response .gr-textbox::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #4CAF50, transparent);
        z-index: 1;
    }
    .ollama-response .gr-textbox textarea {
        background: transparent !important;
        color: #1b5e20 !important;
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        line-height: 1.6 !important;
        font-size: 14px !important;
        letter-spacing: 0.2px;
        font-weight: 400;
        padding: 16px !important;
        border: none !important;
        resize: none !important;
    }
    .webui-response .gr-textbox {
        background: linear-gradient(145deg, #fafbff 0%, #e3f2fd 100%);
        border: 2px solid #2196F3;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(33, 150, 243, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.6);
        position: relative;
        overflow: hidden;
    }
    .webui-response .gr-textbox::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #2196F3, transparent);
        z-index: 1;
    }
    .webui-response .gr-textbox textarea {
        background: transparent !important;
        color: #0d47a1 !important;
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        line-height: 1.6 !important;
        font-size: 14px !important;
        letter-spacing: 0.2px;
        font-weight: 400;
        padding: 16px !important;
        border: none !important;
        resize: none !important;
    }
    /* Consistent rounded styling for all other textboxes */
    .gr-textbox {
        border-radius: 12px !important;
    }
    .gr-button {
        border-radius: 10px !important;
    }
    .gr-dropdown {
        border-radius: 12px !important;
    }
    """
    
    with gr.Blocks(css=css, title="SUSE AI Chat") as interface:
        # Simple header without complex graphics
        gr.HTML("""
        <div style='text-align: center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #0c322c 0%, #1a4a3a 100%); border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);'>
            <h1 style='color: #30ba78; margin: 0; font-size: 1.8em; font-weight: 600;'>AI Chat Dashboard</h1>
            <p style='color: #ffffff; margin: 10px 0 0 0; opacity: 0.8; font-size: 1em;'>Compare AI responses: Direct Ollama vs Open WebUI</p>
        </div>
        """)
        
        with gr.Row():
            # LEFT PANEL - Compact Provider Status (30%)
            with gr.Column(scale=3):
                # Initialize with pre-drawn provider status boxes
                initial_status_html = chat_instance.get_provider_status_html()
                provider_status_html = gr.HTML(value=initial_status_html)
                refresh_providers_btn = gr.Button("🔄 Refresh", elem_classes="refresh-btn", size="sm")

            # CENTER PANEL - Chat Interface in Grouped Container (70%) 
            with gr.Column(scale=7):
                with gr.Group():
                    # Header with automation controls and config
                    gr.HTML("""
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 10px; background: linear-gradient(135deg, rgba(115, 186, 37, 0.1) 0%, rgba(115, 186, 37, 0.05) 100%); border-radius: 10px; border: 1px solid rgba(115, 186, 37, 0.2);'>
                        <h2 style='color: #73ba25; margin: 0; font-size: 1.3em; font-weight: 600;'>🔄 AI Response Comparison</h2>
                    </div>
                    """)
                    
                    # Automation and Config Controls Row
                    with gr.Row():
                        with gr.Column(scale=1):
                            # Automation buttons moved to config panel for better organization
                            pass
                        with gr.Column(scale=1):
                            config_btn = gr.Button("⚙️ Config", size="sm")
                    
                    # Input section
                    with gr.Row():
                        with gr.Column(scale=5):
                            msg_input = gr.Textbox(
                                label="", 
                                placeholder="💭 Ask a question to compare responses...", 
                                lines=2, 
                                show_label=False,
                                container=False
                            )
                        with gr.Column(scale=1, min_width=80):
                            send_btn = gr.Button("Send ❯", variant="primary", size="lg")
                    
                    # Response comparison panels with enhanced styling
                    with gr.Row():
                        with gr.Column():
                            gr.HTML("""
                            <div style='background: linear-gradient(135deg, #1e3a2e 0%, #2d5a3d 100%); padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #4CAF50; box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);'>
                                <h4 style='text-align: center; color: #4CAF50; margin: 0; font-size: 1.1em; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,0.3);'>🤖 Direct Ollama Response</h4>
                                <p style='text-align: center; color: #a5d6a7; margin: 5px 0 0 0; font-size: 0.85em; opacity: 0.9;'>Local AI Model • Direct Connection</p>
                            </div>
                            """)
                            ollama_output = gr.Textbox(
                                label="", 
                                lines=18, 
                                show_label=False, 
                                interactive=False, 
                                placeholder="Direct Ollama response will appear here...",
                                container=True,
                                elem_classes="ollama-response"
                            )
                        
                        with gr.Column():
                            gr.HTML("""
                            <div style='background: linear-gradient(135deg, #1a2f3a 0%, #2d4a5a 100%); padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #2196F3; box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);'>
                                <h4 style='text-align: center; color: #2196F3; margin: 0; font-size: 1.1em; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,0.3);'>🌐 Open WebUI Response</h4>
                                <p style='text-align: center; color: #90caf9; margin: 5px 0 0 0; font-size: 0.85em; opacity: 0.9;'>Web Interface • Enhanced Features</p>
                            </div>
                            """)
                            webui_output = gr.Textbox(
                                label="", 
                                lines=18, 
                                show_label=False, 
                                interactive=False, 
                                placeholder="Open WebUI response will appear here...",
                                container=True,
                                elem_classes="webui-response"
                            )
                    
                    clear_btn = gr.Button("🗑️ Clear All", variant="secondary", size="sm")

        # Configuration Modal (initially hidden)
        with gr.Column(visible=False) as config_panel:
            with gr.Row():
                gr.HTML("<h3 style='color: #73ba25; text-align: center;'>⚙️ Configuration</h3>")
                close_config_btn = gr.Button("✕", variant="secondary", size="sm", elem_classes="close-btn")
            
            # Model selection
            model_dropdown = gr.Dropdown(
                choices=["Loading..."], 
                label="🤖 Active Model", 
                value="", 
                allow_custom_value=True
            )
            
            # Automation settings
            if chat_instance.automation_enabled:
                gr.HTML("<h4 style='color: #73ba25; margin: 15px 0 10px 0;'>🤖 Automation Settings</h4>")
                
                with gr.Row():
                    automation_interval_input = gr.Number(
                        label="Interval (seconds)", 
                        value=chat_instance.automation_interval, 
                        precision=0,
                        minimum=5,
                        maximum=300
                    )
                    automation_send_messages_input = gr.Checkbox(
                        label="Send test messages to models", 
                        value=chat_instance.automation_send_messages,
                        info="When enabled, sends test questions to Ollama and Open WebUI"
                    )
                
                with gr.Row():
                    start_auto_btn = gr.Button("▶️ Start Automation", variant="primary", size="sm")
                    stop_auto_btn = gr.Button("⏹️ Stop Automation", variant="secondary", size="sm", interactive=False)
                
                # Automation results display (visible to show requests and responses)
                gr.HTML("""
                <div style='background: linear-gradient(135deg, rgba(115, 186, 37, 0.1) 0%, rgba(115, 186, 37, 0.05) 100%); border: 1px solid rgba(115, 186, 37, 0.2); border-radius: 12px; padding: 12px; margin: 10px 0;'>
                    <h4 style='color: #73ba25; margin: 0 0 8px 0; font-size: 1.1em; font-weight: 600;'>🔄 Automation Test Results</h4>
                    <p style='color: #ffffff; margin: 0; font-size: 0.9em; opacity: 0.8;'>Live results from automated provider testing and AI responses</p>
                </div>
                """)
                automation_results_display = gr.JSON(label="Latest Test Results", visible=True, show_label=True)
            

        # --- Event Handlers ---
        
        def handle_send_message(message: str, model: str):
            if not message.strip(): 
                return "", "", ""
            if not model or any(err in model for err in ["Error", "No models"]):
                error_msg = "⚠️ Please select a valid Ollama model first."
                return error_msg, error_msg, ""
            
            # Show "Thinking..." in both outputs
            yield "🤔 Thinking...", "🤔 Thinking...", ""

            messages_for_api = [{"role": "user", "content": message}]
            
            ollama_reply = chat_instance.chat_with_ollama(messages_for_api, model)
            open_webui_reply = chat_instance.chat_with_open_webui(messages_for_api, model)

            yield ollama_reply, open_webui_reply, ""

        def show_config_panel():
            """Show the configuration panel."""
            return gr.Column(visible=True)
        
        def hide_config_panel():
            """Hide the configuration panel."""
            return gr.Column(visible=False)

        send_btn.click(handle_send_message, inputs=[msg_input, model_dropdown], outputs=[ollama_output, webui_output, msg_input])
        msg_input.submit(handle_send_message, inputs=[msg_input, model_dropdown], outputs=[ollama_output, webui_output, msg_input])
        clear_btn.click(lambda: ("", "", ""), outputs=[ollama_output, webui_output, msg_input])
        
        refresh_providers_btn.click(chat_instance.refresh_providers, outputs=[provider_status_html])
        config_btn.click(show_config_panel, outputs=[config_panel])
        close_config_btn.click(hide_config_panel, outputs=[config_panel])

        def initial_load():
            """Loads initial data when the UI starts."""
            chat_instance.update_all_provider_status()
            status_html = chat_instance.get_provider_status_html()
            models_dd = chat_instance.refresh_ollama_models()
            return status_html, models_dd
        
        interface.load(initial_load, outputs=[provider_status_html, model_dropdown])

        # Add a simple auto-refresh for provider status every 10 seconds
        def refresh_provider_status():
            """Refresh provider status display."""
            chat_instance.update_all_provider_status()
            return gr.HTML(value=chat_instance.get_provider_status_html())
            
        # Only set up UI refresh mechanism - no background pinging unless automation is running
        logger.info("UI refresh mechanism ready - background processes controlled by automation state")

        # --- NEW: Automation Event Handlers ---
        if chat_instance.automation_enabled:
            start_auto_btn.click(
                chat_instance.start_automation,
                inputs=[model_dropdown, automation_interval_input, automation_send_messages_input],
                outputs=[start_auto_btn, stop_auto_btn]
            )
            stop_auto_btn.click(
                chat_instance.stop_automation,
                outputs=[start_auto_btn, stop_auto_btn]
            )

            # Auto-update UI every 2 seconds to check for automation results
            def update_ui_from_queue():
                """Checks the queue and updates the results and provider status display."""
                try:
                    latest_result = chat_instance.results_queue.get_nowait()
                    status_html = chat_instance.get_provider_status_html()
                    return gr.JSON(value=latest_result, visible=True), gr.HTML(value=status_html)
                except queue.Empty:
                    # No new results, keep previous results visible
                    status_html = chat_instance.get_provider_status_html()
                    return gr.JSON(visible=True), gr.HTML(value=status_html)

            # Add hidden button for auto-refresh trigger
            auto_refresh_btn = gr.Button("Auto Refresh", visible=False)
            auto_refresh_btn.click(
                update_ui_from_queue,
                outputs=[automation_results_display, provider_status_html]
            )
            
            # Removed JavaScript auto-refresh - all updates handled by automation loop
            
            # Auto-refresh every 5 seconds when automation is running
            # Removed periodic refresh - provider status updates are handled by automation loop
            
            # Auto-start automation in background thread (delayed start to allow interface to load)
            if chat_instance.automation_enabled:
                def delayed_auto_start():
                    import time
                    time.sleep(3)  # Wait for interface to fully load
                    models = chat_instance.get_ollama_models()
                    if models and len(models) > 0:
                        model = models[0]
                        logger.info(f"Auto-starting automation with model: {model}")
                        chat_instance.start_automation(model, chat_instance.automation_interval)
                    else:
                        logger.warning("Automation enabled but no models available for auto-start")
                
                # Start auto-start in background thread
                import threading
                auto_start_thread = threading.Thread(target=delayed_auto_start, daemon=True)
                auto_start_thread.start()

    return interface

if __name__ == "__main__":
    logger.info("Starting Chat Interface application.")
    app_interface = create_interface()
    # In K8s, we bind to 0.0.0.0 to be accessible from outside the container
    app_interface.launch(server_name="0.0.0.0", server_port=7860, show_error=True)
# Added a comment to trigger a new build