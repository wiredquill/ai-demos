# HTTP Load Simulator for AI Compare
FROM python:3.11-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir requests

# Copy load simulator script
COPY load_simulator.py .

# Create non-root user
RUN useradd --create-home --shell /bin/bash simulator
USER simulator

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run the load simulator
CMD ["python", "-u", "load_simulator.py"]