#!/bin/bash
# AI Compare Emergency Build Script
# Fallback procedures for when remote BuildKit server is unavailable

set -e

# Configuration
REGISTRY="ghcr.io/wiredquill"
PROJECT="ai-demos-suse"
DOCKERFILE="app/Dockerfile.suse"

# Emergency registries (in order of preference)
EMERGENCY_REGISTRIES=(
    "ghcr.io/wiredquill"
    "localhost:5000"
    "docker.io/wiredquill"
)

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Logging functions
log() { echo -e "${MAGENTA}[EMERGENCY]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

# Function to check system resources
check_system_resources() {
    log "Checking system resources for local build..."
    
    # Check available disk space (need at least 5GB)
    local available_space=$(df . | tail -1 | awk '{print $4}')
    local available_gb=$((available_space / 1024 / 1024))
    
    if [[ $available_gb -lt 5 ]]; then
        error "Insufficient disk space: ${available_gb}GB available (need 5GB minimum)"
        return 1
    fi
    
    # Check available memory (need at least 2GB)
    local available_mem=$(free -m | awk 'NR==2{print $7}')
    if [[ $available_mem -lt 2048 ]]; then
        warning "Low memory: ${available_mem}MB available (recommended: 2GB+)"
    fi
    
    success "System resources check passed (${available_gb}GB disk, ${available_mem}MB memory)"
    return 0
}

# Function to test registry connectivity
test_registry() {
    local registry="$1"
    
    info "Testing registry: $registry"
    
    # Test with a simple image pull
    if timeout 30 docker pull hello-world >/dev/null 2>&1; then
        # Test push capability with tag
        local test_tag="$registry/$PROJECT:connectivity-test"
        if docker tag hello-world "$test_tag" >/dev/null 2>&1 && \
           timeout 60 docker push "$test_tag" >/dev/null 2>&1; then
            # Clean up test image
            docker rmi "$test_tag" >/dev/null 2>&1 || true
            success "Registry $registry is accessible and writable"
            return 0
        fi
    fi
    
    warning "Registry $registry is not accessible or not writable"
    return 1
}

# Function to find working registry
find_working_registry() {
    log "Finding available emergency registry..."
    
    for registry in "${EMERGENCY_REGISTRIES[@]}"; do
        if test_registry "$registry"; then
            WORKING_REGISTRY="$registry"
            success "Using registry: $WORKING_REGISTRY"
            return 0
        fi
    done
    
    error "No working registries found"
    return 1
}

# Function to perform emergency Docker build
emergency_docker_build() {
    local tag="$1"
    local registry="$2"
    
    log "Starting emergency Docker build..."
    warning "Using local Docker daemon - build may be slower"
    
    # Ensure Docker buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        error "Docker buildx not available - cannot perform emergency build"
        return 1
    fi
    
    # Create timestamp for emergency tag
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local emergency_tag="emergency-$timestamp"
    local commit_short=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    info "Building emergency image..."
    info "Registry: $registry"
    info "Tag: $emergency_tag"
    info "Commit: $commit_short"
    
    # Perform build with minimal optimization (speed over efficiency)
    docker buildx build \
        --platform linux/amd64 \
        --file "$DOCKERFILE" \
        --tag "$registry/$PROJECT:$emergency_tag" \
        --tag "$registry/$PROJECT:emergency-latest" \
        --push \
        --build-arg VERSION="emergency-$timestamp" \
        --build-arg COMMIT_SHA="$commit_short" \
        --progress=plain \
        . || {
            error "Emergency Docker build failed"
            return 1
        }
    
    success "Emergency build completed!"
    echo ""
    echo "Emergency images:"
    echo "  $registry/$PROJECT:$emergency_tag"
    echo "  $registry/$PROJECT:emergency-latest"
    echo ""
    
    # Store emergency image info for recovery
    cat > emergency-build-info.txt << EOF
Emergency Build Information
===========================
Timestamp: $(date)
Registry: $registry
Tag: $emergency_tag
Commit: $commit_short
Images:
  - $registry/$PROJECT:$emergency_tag
  - $registry/$PROJECT:emergency-latest

Recovery Commands:
  docker pull $registry/$PROJECT:$emergency_tag
  kubectl set image deployment/ai-compare-app ai-compare=$registry/$PROJECT:$emergency_tag -n ai-compare
EOF
    
    success "Emergency build info saved to: emergency-build-info.txt"
    return 0
}

# Function to perform GitHub Actions trigger
trigger_github_actions() {
    log "Attempting to trigger GitHub Actions build..."
    
    # Check if gh CLI is available
    if ! command -v gh >/dev/null 2>&1; then
        warning "GitHub CLI not available - cannot trigger Actions build"
        return 1
    fi
    
    # Trigger workflow dispatch
    if gh workflow run ci-cd.yaml >/dev/null 2>&1; then
        success "GitHub Actions build triggered"
        info "Monitor at: https://github.com/wiredquill/ai-demos/actions"
        return 0
    else
        warning "Failed to trigger GitHub Actions"
        return 1
    fi
}

# Function to perform local buildah build (if available)
emergency_buildah_build() {
    local tag="$1"
    local registry="$2"
    
    # Check if buildah is available
    if ! command -v buildah >/dev/null 2>&1; then
        warning "Buildah not available - skipping buildah emergency build"
        return 1
    fi
    
    log "Starting emergency Buildah build..."
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local buildah_tag="buildah-emergency-$timestamp"
    
    # Create a new container
    local container=$(buildah from registry.suse.com/bci/python:3.11)
    
    # Mount the container filesystem
    local mnt=$(buildah mount "$container")
    
    # Copy application files
    cp -r app/* "$mnt/app/" 2>/dev/null || {
        buildah umount "$container"
        buildah rm "$container"
        error "Failed to copy application files"
        return 1
    }
    
    # Configure the container
    buildah config --workingdir /app "$container"
    buildah config --port 7860 --port 8080 "$container"
    buildah config --cmd '["python3", "-u", "python-ollama-open-webui.py"]' "$container"
    
    # Commit and push
    buildah commit "$container" "$registry/$PROJECT:$buildah_tag"
    buildah push "$registry/$PROJECT:$buildah_tag"
    
    # Cleanup
    buildah umount "$container"
    buildah rm "$container"
    
    success "Buildah emergency build completed: $registry/$PROJECT:$buildah_tag"
    return 0
}

# Function to create minimal emergency image
create_minimal_emergency() {
    local registry="$1"
    
    log "Creating minimal emergency image..."
    
    # Create a minimal Dockerfile for emergency
    cat > Dockerfile.emergency << 'EOF'
FROM registry.suse.com/bci/python:3.11

# Install minimal dependencies
RUN zypper refresh && zypper install -y ca-certificates curl && zypper clean -a

# Install Python dependencies
COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application
WORKDIR /app
COPY app/python-ollama-open-webui.py .
COPY frontend ./frontend/

EXPOSE 7860 8080
CMD ["python3", "-u", "python-ollama-open-webui.py"]
EOF
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local minimal_tag="minimal-emergency-$timestamp"
    
    # Build minimal image
    docker build \
        -f Dockerfile.emergency \
        -t "$registry/$PROJECT:$minimal_tag" \
        -t "$registry/$PROJECT:minimal-emergency" \
        . && \
    docker push "$registry/$PROJECT:$minimal_tag" && \
    docker push "$registry/$PROJECT:minimal-emergency"
    
    # Cleanup
    rm -f Dockerfile.emergency
    
    if [[ $? -eq 0 ]]; then
        success "Minimal emergency image created: $registry/$PROJECT:$minimal_tag"
        return 0
    else
        error "Failed to create minimal emergency image"
        return 1
    fi
}

# Function to show emergency recovery options
show_recovery_options() {
    echo ""
    log "Emergency Recovery Options"
    echo "=========================="
    echo ""
    echo "1. Wait for BuildKit server recovery:"
    echo "   ./scripts/dev-build.sh check"
    echo ""
    echo "2. Use GitHub Actions (if available):"
    echo "   gh workflow run ci-cd.yaml"
    echo "   # Monitor: https://github.com/wiredquill/ai-demos/actions"
    echo ""
    echo "3. Deploy emergency image:"
    echo "   kubectl set image deployment/ai-compare-app \\"
    echo "     ai-compare=$WORKING_REGISTRY/$PROJECT:emergency-latest \\"
    echo "     -n ai-compare"
    echo ""
    echo "4. Local testing:"
    echo "   docker run --rm -p 7860:7860 -p 8080:8080 \\"
    echo "     $WORKING_REGISTRY/$PROJECT:emergency-latest"
    echo ""
}

# Main emergency build function
emergency_build() {
    local build_type="${1:-auto}"
    
    log "Starting emergency build procedure..."
    warning "BuildKit server unavailable - using fallback methods"
    
    # Check system resources
    if ! check_system_resources; then
        error "System resources insufficient for emergency build"
        return 1
    fi
    
    # Find working registry
    if ! find_working_registry; then
        error "No accessible registries - cannot proceed with emergency build"
        return 1
    fi
    
    case "$build_type" in
        "docker"|"auto")
            if emergency_docker_build "emergency" "$WORKING_REGISTRY"; then
                show_recovery_options
                return 0
            fi
            ;;
        "minimal")
            if create_minimal_emergency "$WORKING_REGISTRY"; then
                show_recovery_options
                return 0
            fi
            ;;
        "buildah")
            if emergency_buildah_build "emergency" "$WORKING_REGISTRY"; then
                show_recovery_options
                return 0
            fi
            ;;
        "github")
            if trigger_github_actions; then
                info "GitHub Actions build in progress"
                return 0
            fi
            ;;
        *)
            error "Invalid build type: $build_type"
            return 1
            ;;
    esac
    
    error "All emergency build methods failed"
    return 1
}

# Main script logic
case "${1:-auto}" in
    "auto"|"docker"|"minimal"|"buildah"|"github")
        emergency_build "$1"
        ;;
    "test")
        check_system_resources
        find_working_registry
        ;;
    "help"|"--help"|"-h")
        echo "Emergency Build Script for AI Compare"
        echo "Usage: $0 [method]"
        echo ""
        echo "Methods:"
        echo "  auto     - Try docker build (default)"
        echo "  docker   - Use Docker buildx"
        echo "  minimal  - Create minimal emergency image"
        echo "  buildah  - Use Buildah (if available)"
        echo "  github   - Trigger GitHub Actions"
        echo "  test     - Test system and registries"
        echo ""
        echo "Emergency build creates images tagged as:"
        echo "  emergency-TIMESTAMP"
        echo "  emergency-latest"
        echo ""
        exit 0
        ;;
    *)
        error "Invalid option: $1"
        error "Use '$0 help' for usage information"
        exit 1
        ;;
esac