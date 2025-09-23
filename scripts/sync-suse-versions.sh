#!/bin/bash
# SUSE Application Collection Version Synchronization Wrapper Script
#
# This script provides a convenient wrapper around the Python synchronization agent
# with common options and pre-flight checks.
#
# Usage:
#   ./sync-suse-versions.sh [options]
#
# Options:
#   --dry-run, -n    Show what would be changed without making changes
#   --verbose, -v    Enable verbose logging
#   --config FILE    Use custom configuration file
#   --help, -h       Show this help message

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default configuration
CONFIG_FILE="${SCRIPT_DIR}/suse-sync-config.yaml"
PYTHON_SCRIPT="${SCRIPT_DIR}/suse-app-collection-sync.py"
DRY_RUN=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

print_info() {
    print_color "$BLUE" "[INFO] $*"
}

print_success() {
    print_color "$GREEN" "[SUCCESS] $*"
}

print_warning() {
    print_color "$YELLOW" "[WARNING] $*"
}

print_error() {
    print_color "$RED" "[ERROR] $*"
}

# Function to show help
show_help() {
    cat << EOF
SUSE Application Collection Version Synchronization

This script synchronizes container versions between SUSE Application Collection
charts and local application Helm charts.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --dry-run, -n     Show what would be changed without making changes
    --verbose, -v     Enable verbose logging and debug output
    --config FILE     Use custom configuration file (default: ${CONFIG_FILE})
    --help, -h        Show this help message

EXAMPLES:
    # Basic synchronization (live update)
    $0

    # Dry run to see what would be changed
    $0 --dry-run

    # Verbose dry run
    $0 --dry-run --verbose

    # Use custom configuration
    $0 --config custom-sync-config.yaml

    # Quick check of versions
    $0 --dry-run | grep -E "(Updated|No changes needed)"

CONFIGURATION:
    The default configuration file is located at:
    ${CONFIG_FILE}

    Edit this file to customize:
    - Source charts to pull from SUSE Application Collection
    - Target charts to update in your repository
    - Image mapping configurations
    - Registry path transformations

REQUIREMENTS:
    - Helm 3.x installed and in PATH
    - Python 3.7+ with required packages (see requirements.txt)
    - Access to SUSE Application Collection registry
    - Write permissions to target chart directories

For more information, see the documentation in the scripts/ directory.
EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if Helm is installed
    if ! command -v helm &> /dev/null; then
        print_error "Helm is not installed or not in PATH"
        print_error "Please install Helm 3.x from https://helm.sh/docs/intro/install/"
        exit 1
    fi

    # Check Helm version
    local helm_version
    helm_version=$(helm version --short 2>/dev/null || echo "unknown")
    print_info "Found Helm: $helm_version"

    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi

    # Check Python version
    local python_version
    python_version=$(python3 --version 2>/dev/null || echo "unknown")
    print_info "Found Python: $python_version"

    # Check if the Python script exists
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        print_error "Python synchronization script not found: $PYTHON_SCRIPT"
        exit 1
    fi

    # Check if configuration file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        print_error "Please create a configuration file or use --config to specify an existing one"
        exit 1
    fi

    # Check if target chart directories exist
    print_info "Checking target chart directories..."
    local charts_dir="${PROJECT_ROOT}/charts"
    if [[ ! -d "$charts_dir" ]]; then
        print_warning "Charts directory not found: $charts_dir"
    else
        local chart_count
        chart_count=$(find "$charts_dir" -name "Chart.yaml" | wc -l)
        print_info "Found $chart_count Helm charts in $charts_dir"
    fi
}

# Function to check for uncommitted changes
check_git_status() {
    if [[ -d "${PROJECT_ROOT}/.git" ]]; then
        print_info "Checking Git status..."

        cd "$PROJECT_ROOT"

        # Check for uncommitted changes
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            print_warning "There are uncommitted changes in the repository"
            print_warning "Consider committing or stashing changes before synchronization"

            if [[ "$DRY_RUN" = false ]]; then
                read -p "Continue anyway? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    print_info "Synchronization cancelled"
                    exit 0
                fi
            fi
        else
            print_success "Working directory is clean"
        fi

        # Show current branch
        local current_branch
        current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
        print_info "Current branch: $current_branch"
    fi
}

# Function to install Python dependencies
install_dependencies() {
    local requirements_file="${SCRIPT_DIR}/requirements.txt"

    if [[ -f "$requirements_file" ]]; then
        print_info "Installing Python dependencies..."
        if python3 -m pip install -r "$requirements_file" --quiet; then
            print_success "Dependencies installed successfully"
        else
            print_warning "Failed to install some dependencies, continuing anyway..."
        fi
    else
        print_warning "requirements.txt not found, assuming dependencies are installed"
    fi
}

# Function to create summary report
create_summary() {
    local exit_code=$1

    echo
    print_info "=========================================="
    if [[ $exit_code -eq 0 ]]; then
        print_success "SYNCHRONIZATION COMPLETED SUCCESSFULLY"
    else
        print_error "SYNCHRONIZATION FAILED"
    fi
    print_info "=========================================="

    if [[ "$DRY_RUN" = true ]]; then
        print_info "This was a dry run - no changes were made"
        print_info "Run without --dry-run to apply the changes"
    else
        print_info "Changes have been applied to the target charts"
        print_info "Consider reviewing changes and committing them"
    fi

    # Show recent log files
    local log_files
    log_files=$(find . -name "suse-sync.log" -o -name "sync-summary-*.txt" 2>/dev/null | head -3)
    if [[ -n "$log_files" ]]; then
        print_info "Report files generated:"
        echo "$log_files" | while IFS= read -r file; do
            print_info "  - $file"
        done
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            print_error "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_info "Starting SUSE Application Collection synchronization..."
    print_info "Working directory: $PROJECT_ROOT"
    print_info "Configuration: $CONFIG_FILE"

    if [[ "$DRY_RUN" = true ]]; then
        print_warning "DRY RUN MODE - No changes will be made"
    fi

    # Pre-flight checks
    check_prerequisites
    check_git_status
    install_dependencies

    print_info "All checks passed, starting synchronization..."
    echo

    # Build Python command
    local python_args=("$PYTHON_SCRIPT" "--config" "$CONFIG_FILE")

    if [[ "$DRY_RUN" = true ]]; then
        python_args+=("--dry-run")
    fi

    if [[ "$VERBOSE" = true ]]; then
        python_args+=("--verbose")
    fi

    # Change to project root for execution
    cd "$PROJECT_ROOT"

    # Run the synchronization
    local exit_code=0
    if python3 "${python_args[@]}"; then
        exit_code=0
    else
        exit_code=$?
    fi

    # Generate summary
    create_summary $exit_code

    exit $exit_code
}

# Handle script interruption
trap 'print_error "Script interrupted"; exit 130' INT TERM

# Run main function
main "$@"
