#!/bin/bash

# Python Test Runner for AI Compare Application  
# Usage: ./scripts/run-python-tests.sh [test-type] [options]

set -e

TEST_TYPE="${1:-all}"
APP_DIR="app"
COVERAGE_MIN="80"

echo "========================================"
echo "🐍 AI Compare Python Test Runner"
echo "========================================"
echo "Test Type: $TEST_TYPE"
echo "App Directory: $APP_DIR"
echo "Coverage Minimum: $COVERAGE_MIN%"
echo ""

# Check if we're in the right directory
if [ ! -d "$APP_DIR" ]; then
    echo "❌ App directory not found: $APP_DIR"
    echo "Please run this script from the repository root"
    exit 1
fi

# Check if Python tests exist
if [ ! -d "$APP_DIR/tests" ]; then
    echo "❌ Tests directory not found: $APP_DIR/tests"
    exit 1
fi

# Change to app directory
cd "$APP_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q -r test-requirements.txt

# Function to run specific test types
run_tests() {
    local test_pattern="$1"
    local test_name="$2"
    
    echo ""
    echo "🧪 Running $test_name tests..."
    echo "----------------------------------------"
    
    if [ "$test_pattern" = "all" ]; then
        pytest tests/ -v \
            --cov=. \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --cov-fail-under="$COVERAGE_MIN" \
            --tb=short \
            --junit-xml=test-results.xml
    else
        pytest "tests/$test_pattern" -v \
            --tb=short
    fi
}

# Function to run linting
run_linting() {
    echo ""
    echo "🔍 Running code quality checks..."
    echo "----------------------------------------"
    
    # Install linting tools if not present
    pip install -q flake8 black isort mypy
    
    # Run black (code formatting check)
    echo "📝 Checking code formatting with black..."
    black --check --diff . || echo "⚠️ Code formatting issues found (run 'black .' to fix)"
    
    # Run isort (import sorting check)
    echo "📂 Checking import sorting with isort..."
    isort --check-only --diff . || echo "⚠️ Import sorting issues found (run 'isort .' to fix)"
    
    # Run flake8 (style and error checking)
    echo "🔍 Checking code style with flake8..."
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    # Run mypy (type checking)
    echo "🔢 Running type checking with mypy..."
    mypy python-ollama-open-webui.py --ignore-missing-imports || echo "⚠️ Type checking completed with warnings"
}

# Run tests based on type
case "$TEST_TYPE" in
    "all")
        run_tests "all" "All"
        ;;
    "unit")
        run_tests "test_*.py" "Unit"
        ;;
    "chat")
        run_tests "test_chat_interface.py" "Chat Interface"
        ;;
    "automation")
        run_tests "test_automation.py" "Automation"
        ;;
    "config")
        run_tests "test_config_management.py" "Configuration Management"
        ;;
    "security")
        echo "🧪 Running Security Demo tests..."
        pytest tests/test_chat_interface.py::TestSecurityDemos -v
        ;;
    "lint")
        run_linting
        exit 0
        ;;
    "coverage")
        echo "📊 Generating detailed coverage report..."
        pytest tests/ --cov=. --cov-report=html:htmlcov --cov-report=term
        echo ""
        echo "📈 Coverage report generated in htmlcov/index.html"
        exit 0
        ;;
    *)
        echo "❌ Unknown test type: $TEST_TYPE"
        echo ""
        echo "Available test types:"
        echo "  all        - Run all tests with coverage"
        echo "  unit       - Run unit tests only"
        echo "  chat       - Run chat interface tests"
        echo "  automation - Run automation tests"
        echo "  config     - Run configuration tests"
        echo "  security   - Run security demo tests"
        echo "  lint       - Run code quality checks"
        echo "  coverage   - Generate coverage report"
        echo ""
        echo "Examples:"
        echo "  ./scripts/run-python-tests.sh all"
        echo "  ./scripts/run-python-tests.sh security"
        echo "  ./scripts/run-python-tests.sh lint"
        exit 1
        ;;
esac

echo ""
echo "✅ Python tests completed successfully!"

# Show coverage summary if available
if [ -f "htmlcov/index.html" ]; then
    echo ""
    echo "📊 Coverage report available at: app/htmlcov/index.html"
fi

# Show test results if available
if [ -f "test-results.xml" ]; then
    echo "📋 JUnit test results: app/test-results.xml"
fi

echo ""
echo "🧹 To cleanup test artifacts:"
echo "   rm -rf app/venv app/htmlcov app/test-results.xml app/.coverage"