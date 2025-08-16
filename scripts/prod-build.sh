#!/bin/bash
# AI Compare Production Build Script
# Multi-architecture builds with comprehensive registry caching and security scanning

set -e

# Configuration
BUILDKIT_HOST="tcp://10.0.10.120:1234"
REGISTRY="ghcr.io/wiredquill"
PROJECT="ai-demos-suse"
DOCKERFILE="app/Dockerfile.suse"

# Build platforms
PLATFORMS="linux/amd64,linux/arm64"
SINGLE_PLATFORM="linux/amd64"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log() { echo -e "${BLUE}[PROD-BUILD]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

# Function to validate version format
validate_version() {
    local version="$1"
    if [[ $version =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
        return 0
    else
        error "Invalid version format: $version"
        error "Expected format: v1.2.3 or 1.2.3 (with optional suffix like -rc1)"
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if we're in the right directory
    if [[ ! -f "$DOCKERFILE" ]]; then
        error "Dockerfile not found: $DOCKERFILE"
        error "Please run this script from the repository root"
        return 1
    fi
    
    # Check git status
    if ! git diff-index --quiet HEAD --; then
        warning "Working directory has uncommitted changes"
        echo "Uncommitted files:"
        git diff-index --name-only HEAD --
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Aborted by user"
            return 1
        fi
    fi
    
    # Check BuildKit connectivity
    if nc -z 10.0.10.120 1234 >/dev/null 2>&1; then
        success "BuildKit server is accessible"
        export BUILDKIT_HOST="$BUILDKIT_HOST"
    else
        error "BuildKit server not accessible - production builds require remote server"
        return 1
    fi
    
    # Check registry authentication
    if ! docker pull ghcr.io/wiredquill/k8s-tmux:latest >/dev/null 2>&1; then
        warning "Registry authentication may be required"
        info "Please ensure you're logged in: echo \$GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin"
    fi
    
    success "Prerequisites check passed"
    return 0
}

# Function to get next version
get_version() {
    local version_type="$1"
    
    if [[ "$version_type" == "manual" ]]; then
        read -p "Enter version (e.g., v1.2.3): " VERSION
        if ! validate_version "$VERSION"; then
            return 1
        fi
    else
        # Get latest tag and increment
        local latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
        
        # Remove 'v' prefix for calculation
        local version_num=${latest_tag#v}
        IFS='.' read -r major minor patch <<< "$version_num"
        
        case "$version_type" in
            "patch")
                patch=$((patch + 1))
                ;;
            "minor")
                minor=$((minor + 1))
                patch=0
                ;;
            "major")
                major=$((major + 1))
                minor=0
                patch=0
                ;;
            *)
                error "Invalid version type: $version_type"
                return 1
                ;;
        esac
        
        VERSION="v$major.$minor.$patch"
        info "Next $version_type version: $VERSION"
        read -p "Use this version? (Y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            read -p "Enter version manually: " VERSION
            if ! validate_version "$VERSION"; then
                return 1
            fi
        fi
    fi
    
    # Ensure v prefix
    if [[ ! $VERSION =~ ^v ]]; then
        VERSION="v$VERSION"
    fi
    
    info "Using version: $VERSION"
    return 0
}

# Function to perform production build
production_build() {
    local version="$1"
    local multiarch="$2"
    
    # Create build timestamp
    local build_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local commit_sha=$(git rev-parse HEAD)
    local commit_short=$(git rev-parse --short HEAD)
    
    # Determine platforms
    local platforms="$SINGLE_PLATFORM"
    if [[ "$multiarch" == "true" ]]; then
        platforms="$PLATFORMS"
        log "Building multi-architecture images: $platforms"
    else
        log "Building single architecture: $platforms"
    fi
    
    log "Starting production build"
    info "Version: $version"
    info "Commit: $commit_short"
    info "Build Date: $build_date"
    info "Platforms: $platforms"
    
    # Build arguments for metadata
    local build_args=(
        "--opt" "build-arg:VERSION=$version"
        "--opt" "build-arg:BUILD_DATE=$build_date"
        "--opt" "build-arg:COMMIT_SHA=$commit_sha"
    )
    
    # Build the image with comprehensive tagging
    buildctl build \
        --frontend dockerfile.v0 \
        --local context=. \
        --local dockerfile=. \
        --opt filename="$DOCKERFILE" \
        --opt platform="$platforms" \
        "${build_args[@]}" \
        --output type=image,name="$REGISTRY/$PROJECT:$version",push=true \
        --output type=image,name="$REGISTRY/$PROJECT:latest",push=true \
        --output type=image,name="$REGISTRY/$PROJECT:prod-$commit_short",push=true \
        --export-cache type=registry,ref="$REGISTRY/$PROJECT:buildcache",mode=max \
        --import-cache type=registry,ref="$REGISTRY/$PROJECT:buildcache" \
        --import-cache type=registry,ref="$REGISTRY/$PROJECT:buildcache-dev" \
        --progress=auto \
        --metadata-file /tmp/build-metadata.json
    
    success "Production build completed successfully!"
    
    # Display build information
    echo ""
    echo "Images pushed:"
    echo "  $REGISTRY/$PROJECT:$version"
    echo "  $REGISTRY/$PROJECT:latest"
    echo "  $REGISTRY/$PROJECT:prod-$commit_short"
    echo ""
    
    # Create git tag
    if git tag -a "$version" -m "Release $version - Built $(date)"; then
        success "Created git tag: $version"
        info "Push tag with: git push origin $version"
    else
        warning "Could not create git tag (may already exist)"
    fi
    
    # Show build metadata if available
    if [[ -f /tmp/build-metadata.json ]]; then
        info "Build metadata:"
        cat /tmp/build-metadata.json | jq -r '."containerimage.digest"' 2>/dev/null | while read digest; do
            echo "  Digest: $digest"
        done
    fi
    
    # Notify completion
    if command -v curl >/dev/null 2>&1; then
        curl -d "AI Compare production build completed: $version" https://ntfy.sh/wq_task >/dev/null 2>&1 || true
    fi
    
    return 0
}

# Function to perform security scan
security_scan() {
    local version="$1"
    
    log "Performing security scan..."
    
    # Check if docker scout is available
    if command -v docker >/dev/null 2>&1 && docker scout version >/dev/null 2>&1; then
        info "Running Docker Scout security scan..."
        docker scout cves "$REGISTRY/$PROJECT:$version" || warning "Security scan failed"
    else
        warning "Docker Scout not available - skipping security scan"
        info "Install Docker Scout for security scanning: https://docs.docker.com/scout/"
    fi
}

# Function to validate deployment
validate_deployment() {
    local version="$1"
    
    log "Validating production image..."
    
    # Test image pull
    if docker pull "$REGISTRY/$PROJECT:$version" >/dev/null 2>&1; then
        success "Image pull successful"
    else
        error "Failed to pull image: $REGISTRY/$PROJECT:$version"
        return 1
    fi
    
    # Test basic functionality (if possible)
    info "Testing basic container functionality..."
    if timeout 30 docker run --rm "$REGISTRY/$PROJECT:$version" python3 -c "import gradio, requests, ollama; print('Dependencies OK')" 2>/dev/null; then
        success "Basic functionality test passed"
    else
        warning "Basic functionality test failed or timed out"
    fi
    
    return 0
}

# Function to show deployment commands
show_deployment_commands() {
    local version="$1"
    
    echo ""
    log "Deployment commands:"
    echo "===================="
    echo ""
    echo "Helm deployment:"
    echo "  helm upgrade ai-compare charts/ai-compare-suse \\"
    echo "    --set aiCompare.image.tag=$version \\"
    echo "    --namespace ai-compare"
    echo ""
    echo "Direct Kubernetes deployment:"
    echo "  kubectl set image deployment/ai-compare-app \\"
    echo "    ai-compare=$REGISTRY/$PROJECT:$version \\"
    echo "    -n ai-compare"
    echo ""
    echo "Local testing:"
    echo "  docker run --rm -p 7860:7860 -p 8080:8080 \\"
    echo "    $REGISTRY/$PROJECT:$version"
    echo ""
}

# Main script logic
main() {
    local version_type="${1:-patch}"
    local multiarch="${2:-false}"
    local scan="${3:-true}"
    
    case "$version_type" in
        "patch"|"minor"|"major"|"manual")
            ;;
        "help"|"--help"|"-h")
            echo "Usage: $0 [version_type] [multiarch] [scan]"
            echo ""
            echo "Arguments:"
            echo "  version_type: patch|minor|major|manual (default: patch)"
            echo "  multiarch:    true|false (default: false)"
            echo "  scan:         true|false (default: true)"
            echo ""
            echo "Examples:"
            echo "  $0 patch                    # Patch version, single arch, with scan"
            echo "  $0 minor true               # Minor version, multi-arch, with scan"
            echo "  $0 major false false        # Major version, single arch, no scan"
            echo "  $0 manual true              # Manual version, multi-arch, with scan"
            exit 0
            ;;
        *)
            error "Invalid version type: $version_type"
            error "Use: patch, minor, major, or manual"
            exit 1
            ;;
    esac
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Get version
    if ! get_version "$version_type"; then
        exit 1
    fi
    
    # Perform production build
    if ! production_build "$VERSION" "$multiarch"; then
        exit 1
    fi
    
    # Security scan
    if [[ "$scan" == "true" ]]; then
        security_scan "$VERSION"
    fi
    
    # Validate deployment
    validate_deployment "$VERSION"
    
    # Show deployment commands
    show_deployment_commands "$VERSION"
    
    success "Production build pipeline completed!"
    success "Version $VERSION is ready for deployment"
}

# Run main function with all arguments
main "$@"