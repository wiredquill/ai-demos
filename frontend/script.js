// AI Compare End User Interface JavaScript

class AICompareClient {
    constructor() {
        this.apiBaseUrl = '/api';  // Proxied through NGINX to backend
        this.isLoading = false;
        this.availabilityDemoState = false;
        
        this.initializeElements();
        this.attachEventListeners();
        this.initializeState();
        this.generateTraffic();
    }
    
    initializeElements() {
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.ollamaResponse = document.getElementById('ollamaResponse');
        this.webuiResponse = document.getElementById('webuiResponse');
        this.dataLeakBtn = document.getElementById('dataLeakBtn');
        this.availabilityBtn = document.getElementById('availabilityBtn');
        this.demoStatus = document.getElementById('demoStatus');
        this.loadingOverlay = document.getElementById('loadingOverlay');
    }
    
    attachEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key in textarea
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Demo buttons
        this.dataLeakBtn.addEventListener('click', () => this.runDataLeakDemo());
        this.availabilityBtn.addEventListener('click', () => this.toggleAvailabilityDemo());
    }
    
    async initializeState() {
        try {
            // Check initial availability demo state
            const response = await this.makeRequest('GET', '/health');
            
            // Check if service is currently in failure state
            if (response.status === 'FAILING') {
                this.availabilityDemoState = true;
            } else {
                this.availabilityDemoState = false;
            }
            
            this.updateAvailabilityButton();
            console.log('🔄 Initial demo state loaded:', this.availabilityDemoState ? 'ON' : 'OFF');
            
        } catch (error) {
            console.log('⚠️ Could not load initial demo state:', error.message);
            // Default to OFF state if we can't determine current state
            this.availabilityDemoState = false;
            this.updateAvailabilityButton();
        }
    }
    
    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message || this.isLoading) return;
        
        this.setLoading(true);
        this.updateResponsePlaceholders('Thinking...', 'Processing...');
        
        try {
            const response = await this.makeRequest('POST', '/chat', {
                message: message,
                model: 'tinyllama:latest'
            });
            
            if (response.status === 'success') {
                this.updateResponses(response.ollama_response, response.webui_response);
            } else {
                throw new Error(response.error || 'Unknown error');
            }
            
        } catch (error) {
            console.error('Chat request failed:', error);
            this.updateResponses(
                `❌ Error: ${error.message}`,
                `❌ Error: ${error.message}`
            );
            this.showDemoStatus(`Request failed: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    async runDataLeakDemo() {
        if (this.isLoading) return;
        
        this.setButtonLoading(this.dataLeakBtn, true);
        
        try {
            const response = await this.makeRequest('POST', '/data-leak-demo');
            this.showDemoStatus(response.message, response.status);
            
        } catch (error) {
            console.error('Data leak demo failed:', error);
            this.showDemoStatus(`Demo failed: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(this.dataLeakBtn, false);
        }
    }
    
    async toggleAvailabilityDemo() {
        if (this.isLoading) return;
        
        this.setButtonLoading(this.availabilityBtn, true);
        
        try {
            const response = await this.makeRequest('POST', '/availability-demo/toggle');
            
            // Update button state
            this.availabilityDemoState = response.service_failure_active;
            this.updateAvailabilityButton();
            
            this.showDemoStatus(response.message, response.status);
            
        } catch (error) {
            console.error('Availability demo failed:', error);
            this.showDemoStatus(`Demo failed: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(this.availabilityBtn, false);
        }
    }
    
    updateAvailabilityButton() {
        if (this.availabilityDemoState) {
            this.availabilityBtn.textContent = '🔴 Availability Demo: ON (FAILING)';
            this.availabilityBtn.setAttribute('data-state', 'on');
            this.availabilityBtn.classList.add('active');
            this.availabilityBtn.title = 'Service is currently failing - click to restore health';
        } else {
            this.availabilityBtn.textContent = '🟢 Availability Demo: OFF (HEALTHY)';
            this.availabilityBtn.setAttribute('data-state', 'off');
            this.availabilityBtn.classList.remove('active');
            this.availabilityBtn.title = 'Service is healthy - click to simulate failure';
        }
    }
    
    updateResponses(ollamaText, webuiText) {
        this.ollamaResponse.innerHTML = `<div class="response-text">${this.escapeHtml(ollamaText)}</div>`;
        this.webuiResponse.innerHTML = `<div class="response-text">${this.escapeHtml(webuiText)}</div>`;
    }
    
    updateResponsePlaceholders(ollamaText, webuiText) {
        this.ollamaResponse.innerHTML = `<div class="placeholder">${ollamaText}</div>`;
        this.webuiResponse.innerHTML = `<div class="placeholder">${webuiText}</div>`;
    }
    
    showDemoStatus(message, type) {
        this.demoStatus.textContent = message;
        this.demoStatus.className = `demo-status show ${type}`;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.demoStatus.classList.remove('show');
        }, 5000);
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.sendButton.disabled = loading;
        this.userInput.disabled = loading;
        
        if (loading) {
            this.loadingOverlay.classList.add('show');
            this.sendButton.textContent = 'Sending...';
        } else {
            this.loadingOverlay.classList.remove('show');
            this.sendButton.textContent = 'Ask AI';
        }
    }
    
    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.style.opacity = '0.6';
        } else {
            button.disabled = false;
            button.style.opacity = '1';
        }
    }
    
    async makeRequest(method, endpoint, data = null) {
        const url = `${this.apiBaseUrl}${endpoint}`;
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        console.log(`🌐 Making ${method} request to ${url}`);
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    // Generate continuous HTTP traffic for observability
    generateTraffic() {
        // Health check every 30 seconds
        setInterval(async () => {
            try {
                await fetch('/health');
                console.log('🟢 Health check - OK');
            } catch (error) {
                console.log('🔴 Health check - Failed:', error.message);
            }
        }, 30000);
        
        // Metrics check every 60 seconds  
        setInterval(async () => {
            try {
                const response = await fetch('/api/metrics');
                const metrics = await response.json();
                console.log('📊 Metrics:', metrics);
            } catch (error) {
                console.log('📊 Metrics check failed:', error.message);
            }
        }, 60000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 AI Compare End User Interface loaded');
    window.aiCompare = new AICompareClient();
});

// Add visual feedback for all buttons
document.addEventListener('click', (e) => {
    if (e.target.tagName === 'BUTTON') {
        // Visual click feedback
        e.target.style.transform = 'scale(0.95)';
        setTimeout(() => {
            e.target.style.transform = '';
        }, 150);
    }
});