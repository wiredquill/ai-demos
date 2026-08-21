# SUSE BCI Migration - Builder Stage
FROM registry.suse.com/bci/python:3.11 AS builder

# Install git using zypper (SUSE package manager)
RUN zypper -n install git

# Install poetry
RUN pip install poetry==1.8.4

# Poetry configuration
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# The RAG apps (apps/rag101.py, rag102.py) use local-file Milvus
# (MilvusClient("./rag101.db")) which requires the milvus-lite embedded server.
# It is deliberately kept OUT of pyproject.toml/poetry.lock (it drags in
# faiss-cpu + pyarrow and slows every lock regen) and pinned here instead.
RUN /app/.venv/bin/pip install milvus-lite

# SUSE BCI Migration - Runtime Stage
FROM registry.suse.com/bci/python:3.11 AS runtime

# Environment variables for virtual environment
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Container metadata
LABEL org.opencontainers.image.source=https://github.com/wiredquill/llm-experiments
LABEL org.opencontainers.image.description="GenAI Demo Application with LLM experiments (SUSE BCI)"
LABEL org.opencontainers.image.title="GenAI Demo - SUSE BCI"
LABEL org.opencontainers.image.base.name="registry.suse.com/bci/python:3.11"

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Copy application files
COPY main.py ./main.py
COPY pricing.json ./pricing.json
COPY apps ./apps
COPY patch ./patch
COPY hr-documents ./hr-documents

# Application entrypoint
ENTRYPOINT ["fastapi", "run", "main.py"]

# HR Documents are included in the image for RAG applications
