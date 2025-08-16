#!/usr/bin/env python3
"""
Test runner script for AI Compare OpenTelemetry unit tests.

This script provides a convenient way to run the OpenTelemetry-specific
test suite with appropriate configuration and reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_pattern=None, verbose=False, coverage=False, html_report=False):
    """Run OpenTelemetry tests with specified options."""
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    test_dir = script_dir / "tests"
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory or specific pattern
    if test_pattern:
        if test_pattern.startswith("test_opentelemetry"):
            cmd.append(str(test_dir / f"{test_pattern}.py"))
        else:
            cmd.append(str(test_dir / f"test_opentelemetry_{test_pattern}.py"))
    else:
        # Run all OpenTelemetry tests
        cmd.extend([
            str(test_dir / "test_opentelemetry_initialization.py"),
            str(test_dir / "test_opentelemetry_instrumentation.py"), 
            str(test_dir / "test_opentelemetry_error_handling.py")
        ])
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=python_ollama_open_webui",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage.xml"
        ])
        
        if html_report:
            cmd.append("--cov-report=html:htmlcov")
    
    # Add HTML test report
    if html_report:
        cmd.append("--html=test_report.html")
        cmd.append("--self-contained-html")
    
    # Add JSON report for CI/CD
    cmd.extend([
        "--json-report",
        "--json-report-file=test_results.json"
    ])
    
    # Add test timeout
    cmd.append("--timeout=30")
    
    # Add markers for test categorization
    cmd.extend([
        "-m", "not slow",  # Skip slow tests by default
        "--tb=short"       # Shorter traceback format
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 70)
    
    # Set environment variables for testing
    test_env = os.environ.copy()
    test_env.update({
        "PYTHONPATH": str(script_dir),
        "TESTING": "true",
        # Disable actual OpenTelemetry initialization during tests
        "OTEL_SDK_DISABLED": "true",
    })
    
    try:
        result = subprocess.run(cmd, env=test_env, cwd=script_dir)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run AI Compare OpenTelemetry unit tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all OpenTelemetry tests
  %(prog)s initialization           # Run initialization tests only
  %(prog)s instrumentation          # Run instrumentation tests only
  %(prog)s error_handling            # Run error handling tests only
  %(prog)s -v --coverage --html      # Run with verbose output, coverage, and HTML reports
        """
    )
    
    parser.add_argument(
        "test_pattern",
        nargs="?",
        help="Test pattern to run (initialization, instrumentation, error_handling)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose test output"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true", 
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML test and coverage reports"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check if test dependencies are installed"
    )
    
    args = parser.parse_args()
    
    if args.check_deps:
        return check_dependencies()
    
    return run_tests(
        test_pattern=args.test_pattern,
        verbose=args.verbose,
        coverage=args.coverage,
        html_report=args.html
    )


def check_dependencies():
    """Check if required test dependencies are installed."""
    required_packages = [
        "pytest",
        "pytest-cov", 
        "pytest-mock",
        "pytest-asyncio",
        "pytest-timeout",
        "pytest-html",
        "pytest-json-report",
        "opentelemetry-api",
        "opentelemetry-sdk",
        "requests-mock"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required test packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return 1
    else:
        print("All required test dependencies are installed ✓")
        return 0


if __name__ == "__main__":
    sys.exit(main())