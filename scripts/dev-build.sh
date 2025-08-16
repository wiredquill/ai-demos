#!/bin/bash
# AI Compare Development Build Script
# Optimized for remote BuildKit server with fast iteration capabilities

set -e

# Configuration
BUILDKIT_HOST="tcp://10.0.10.120:1234"
REGISTRY="ghcr.io/wiredquill"
PROJECT="ai-demos-suse"
DOCKERFILE="app/Dockerfile.suse"

# Color output for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log() {
    echo -e "${BLUE}[BUILD]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check BuildKit server connectivity
check_buildkit() {
    log "Checking BuildKit server connectivity..."
    if nc -z 10.0.10.120 1234 >/dev/null 2>&1; then
        success "BuildKit server is accessible"
        export BUILDKIT_HOST="$BUILDKIT_HOST"
        return 0
    else
        error "BuildKit server is not accessible"
        return 1
    fi
}

# Function to fallback to local Docker daemon
fallback_build() {
    warning "Falling back to local Docker daemon"
    unset BUILDKIT_HOST
    
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    TAG="dev-fallback-$TIMESTAMP"
    
    log "Building with local Docker daemon: $REGISTRY/$PROJECT:$TAG"
    
    docker buildx build \
        --platform linux/amd64 \
        --file "$DOCKERFILE" \
        --tag "$REGISTRY/$PROJECT:$TAG" \
        --tag "$REGISTRY/$PROJECT:dev-latest" \
        --push \
        --cache-from type=gha \
        --cache-to type=gha,mode=max \
        .
    
    success "Fallback build completed: $REGISTRY/$PROJECT:$TAG"
    echo "$REGISTRY/$PROJECT:$TAG"
}

# Function to perform development build
dev_build() {
    log "Starting development build with remote BuildKit server"
    
    # Generate development tag
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    COMMIT_SHORT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    BRANCH=$(git branch --show-current 2>/dev/null | tr '/' '-' || echo "unknown")
    TAG="dev-${BRANCH}-${COMMIT_SHORT}-${TIMESTAMP}"
    
    log "Building AI Compare SUSE edition"
    log "Tag: $TAG"
    log "Dockerfile: $DOCKERFILE"
    log "Registry: $REGISTRY/$PROJECT"
    
    # Use buildctl for optimized remote building
    buildctl build \
        --frontend dockerfile.v0 \
        --local context=. \
        --local dockerfile=. \
        --opt filename="$DOCKERFILE" \
        --output type=image,name="$REGISTRY/$PROJECT:$TAG",push=true \
        --output type=image,name="$REGISTRY/$PROJECT:dev-latest",push=true \
        --export-cache type=registry,ref="$REGISTRY/$PROJECT:buildcache-dev",mode=max \
        --import-cache type=registry,ref="$REGISTRY/$PROJECT:buildcache-dev" \
        --import-cache type=registry,ref="$REGISTRY/$PROJECT:buildcache" \
        --progress=auto
    
    success "Development build completed successfully!"
    echo ""
    echo "Images pushed:"
    echo "  $REGISTRY/$PROJECT:$TAG"
    echo "  $REGISTRY/$PROJECT:dev-latest"
    echo ""
    echo "To test locally:"
    echo "  docker run --rm -p 7860:7860 -p 8080:8080 $REGISTRY/$PROJECT:$TAG"
    echo ""
    echo "To update Helm deployment:"
    echo "  helm upgrade ai-compare charts/ai-compare-suse --set aiCompare.image.tag=$TAG"
    
    # Notify completion (if ntfy is available)
    if command -v curl >/dev/null 2>&1; then
        curl -d "AI Compare dev build completed: $TAG" https://ntfy.sh/wq_task >/dev/null 2>&1 || true
    fi
    
    return 0
}

# Function to perform quick rebuild (skip cache layers)
quick_build() {
    log "Starting quick development build (no cache import)"
    
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    TAG="quick-$TIMESTAMP"
    
    buildctl build \
        --frontend dockerfile.v0 \
        --local context=. \
        --local dockerfile=. \
        --opt filename="$DOCKERFILE" \
        --output type=image,name="$REGISTRY/$PROJECT:$TAG",push=true \
        --export-cache type=inline \
        --progress=plain
    
    success "Quick build completed: $REGISTRY/$PROJECT:$TAG"
    echo "$REGISTRY/$PROJECT:$TAG"
}

# Function to show build info
show_info() {
    echo ""
    log "BuildKit Development Build Information"
    echo "======================================"
    echo "Remote BuildKit: $BUILDKIT_HOST"
    echo "Registry: $REGISTRY"
    echo "Project: $PROJECT"
    echo "Dockerfile: $DOCKERFILE"
    echo ""
    
    if [ "$BUILDKIT_HOST" ]; then
        log "Checking BuildKit server status..."
        buildctl debug info 2>/dev/null || warning "Could not get BuildKit info"
    fi
    
    echo ""
    log "Recent images:"
    docker images "$REGISTRY/$PROJECT" --format "table {{.Tag}}\t{{.CreatedAt}}\t{{.Size}}" 2>/dev/null | head -6 || true
}

# Main script logic
case "${1:-build}" in
    "build")
        if check_buildkit; then
            dev_build
        else
            fallback_build
        fi
        ;;
    "quick")
        if check_buildkit; then
            quick_build
        else
            error "Quick build requires BuildKit server - use 'build' for fallback"
            exit 1
        fi
        ;;
    "info")
        show_info
        ;;
    "check")
        check_buildkit
        ;;
    *)
        echo "Usage: $0 [build|quick|info|check]"
        echo ""
        echo "Commands:"
        echo "  build (default) - Full development build with caching"
        echo "  quick          - Quick build without cache import"
        echo "  info           - Show build configuration and status"
        echo "  check          - Check BuildKit server connectivity"
        echo ""
        echo "Examples:"
        echo "  $0              # Standard development build"
        echo "  $0 quick        # Quick iteration build"
        echo "  $0 info         # Show build information"
        exit 1
        ;;
esac