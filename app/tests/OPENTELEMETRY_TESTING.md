# OpenTelemetry Testing Guide

This document describes the comprehensive unit test suite for the AI Compare application's OpenTelemetry implementation.

## Overview

The test suite provides comprehensive coverage of:

1. **OpenTelemetry Initialization** - Setup, configuration, and resource attribute handling
2. **GenAI Instrumentation** - Manual instrumentation for Ollama calls with semantic conventions
3. **Error Handling & Timeout Protection** - Robust error scenarios and network resilience
4. **Configuration Validation** - Environment variable handling and edge cases

## Test Structure

### Core Test Files

- **`test_opentelemetry_initialization.py`** - Tests for OpenTelemetry setup and configuration
- **`test_opentelemetry_instrumentation.py`** - Tests for GenAI and HTTP instrumentation  
- **`test_opentelemetry_error_handling.py`** - Tests for error scenarios and timeout protection
- **`conftest.py`** - Shared fixtures and mocks for all tests

### Test Categories

#### 1. Initialization Tests (`test_opentelemetry_initialization.py`)

**Key Test Cases:**
- ✅ Observability disabled by default in production
- ✅ Observability enabled with `DEV_MODE=true` or `OBSERVABILITY_ENABLED=true`
- ✅ OTLP endpoint connectivity testing with timeout protection
- ✅ Service name and namespace configuration from environment variables
- ✅ Resource attributes with GenAI semantic conventions
- ✅ Enhanced GenAI observability features configuration
- ✅ GenAI tracer creation for manual instrumentation
- ✅ Kubernetes environment variable detection
- ✅ Graceful handling of initialization failures

**Environment Variables Tested:**
```bash
OBSERVABILITY_ENABLED=true|false
DEV_MODE=true|false
OTLP_ENDPOINT=http://collector:4318
COLLECT_GPU_STATS=true|false
OTEL_SERVICE_NAME=ai-compare
OTEL_SERVICE_NAMESPACE=ai-compare
TOKEN_TRACKING_ENABLED=true|false
COST_TRACKING_ENABLED=true|false
MODEL_METRICS_ENABLED=true|false
TRACE_REQUESTS_ENABLED=true|false
HOSTNAME=pod-name
K8S_POD_UID=pod-uid
K8S_NODE_NAME=node-name
```

#### 2. Instrumentation Tests (`test_opentelemetry_instrumentation.py`)

**Key Test Cases:**
- ✅ Ollama chat calls with OpenTelemetry GenAI instrumentation
- ✅ Span attribute setting with GenAI semantic conventions
- ✅ Response metadata extraction and recording
- ✅ Fallback behavior when OpenTelemetry is unavailable
- ✅ Thread-safe timeout protection mechanism
- ✅ Exception propagation through threading queues
- ✅ Error status recording in spans
- ✅ Multiple model support with correct attributes

**GenAI Semantic Conventions:**
```python
span.set_attribute("gen_ai.system", "ollama")
span.set_attribute("gen_ai.operation.name", "chat")
span.set_attribute("gen_ai.request.model", model)
span.set_attribute("gen_ai.application.name", "ai-compare")
span.set_attribute("ai.model.provider", "meta")
span.set_attribute("ai.workload.type", "inference")
span.set_attribute("gen_ai.response.finish_reason", "stop")
span.set_attribute("gen_ai.response.length", content_length)
```

#### 3. Error Handling Tests (`test_opentelemetry_error_handling.py`)

**Key Test Cases:**
- ✅ Socket connection timeouts and failures
- ✅ Network interface errors (DNS, connection refused, etc.)
- ✅ OpenLit initialization exceptions
- ✅ OpenTelemetry tracer creation failures
- ✅ Resource creation failures
- ✅ Timeout protection in Ollama calls
- ✅ Thread exception propagation
- ✅ Span error status recording
- ✅ Malformed OTLP endpoint URLs
- ✅ Invalid environment variable values
- ✅ Concurrent initialization calls
- ✅ Memory pressure handling
- ✅ Configuration validation edge cases

## Running Tests

### Quick Start

```bash
# Run all OpenTelemetry tests
cd /Users/erquill/Documents/GitHub/ai-demos/app
python run_otel_tests.py

# Run specific test categories
python run_otel_tests.py initialization
python run_otel_tests.py instrumentation  
python run_otel_tests.py error_handling

# Run with verbose output and coverage
python run_otel_tests.py -v --coverage --html
```

### Manual pytest Commands

```bash
# Run all OpenTelemetry tests
pytest tests/test_opentelemetry_*.py -v

# Run specific test file
pytest tests/test_opentelemetry_initialization.py -v

# Run with coverage
pytest tests/test_opentelemetry_*.py --cov=python_ollama_open_webui --cov-report=html

# Run with markers
pytest tests/test_opentelemetry_*.py -m "not slow" -v
```

### Dependencies

Install test dependencies:

```bash
pip install -r test-requirements.txt
```

Check dependencies:

```bash
python run_otel_tests.py --check-deps
```

## Test Fixtures and Mocks

### Key Fixtures (from `conftest.py`)

- **`opentelemetry_environment`** - Mock environment variables for OTel testing
- **`disabled_opentelemetry_environment`** - Environment with OTel disabled
- **`mock_opentelemetry_span`** - Mock OTel span with all methods
- **`mock_opentelemetry_tracer`** - Mock OTel tracer for instrumentation testing
- **`mock_opentelemetry_resource`** - Mock OTel resource with GenAI attributes
- **`mock_socket_success/failure`** - Mock socket connectivity tests
- **`mock_ollama_client`** - Mock Ollama client with responses
- **`mock_openlit`** - Mock OpenLit initialization
- **`observability_test_data`** - Test data for various scenarios

### Module Mocking Strategy

The test suite uses comprehensive mocking to isolate the OpenTelemetry logic:

```python
# OpenTelemetry modules mocked in conftest.py
sys.modules["opentelemetry"] = opentelemetry_mock
sys.modules["opentelemetry.trace"] = opentelemetry_mock.trace
sys.modules["opentelemetry.sdk.resources"] = opentelemetry_mock.sdk.resources
sys.modules["ollama"] = MagicMock()
sys.modules["openlit"] = MagicMock()
```

## Test Coverage Areas

### ✅ Positive Test Cases
- Successful OpenTelemetry initialization with all features enabled
- Proper GenAI instrumentation with semantic conventions
- Correct resource attribute configuration
- Successful Ollama calls with tracing

### ✅ Negative Test Cases  
- Network connectivity failures
- OpenLit initialization errors
- OpenTelemetry import errors
- Malformed configuration values
- Timeout scenarios

### ✅ Edge Cases
- Concurrent initialization calls
- Memory pressure during initialization
- Invalid environment variable formats
- Missing Kubernetes environment variables
- URL parsing edge cases

### ✅ Integration Scenarios
- Manual instrumentation alongside auto-instrumentation
- Fallback behavior when OTel unavailable
- Thread-safe timeout protection
- Exception propagation through queues

## CI/CD Integration

The test suite is designed for CI/CD integration:

```bash
# Generate reports for CI
python run_otel_tests.py --coverage --html
# Produces: coverage.xml, htmlcov/, test_report.html, test_results.json
```

### Test Outputs
- **XML Coverage**: `coverage.xml` for CI consumption
- **HTML Coverage**: `htmlcov/index.html` for detailed coverage review
- **Test Report**: `test_report.html` for test result visualization
- **JSON Results**: `test_results.json` for programmatic analysis

## Best Practices

### Writing New Tests

1. **Use Existing Fixtures**: Leverage shared fixtures from `conftest.py`
2. **Mock Dependencies**: Mock all external dependencies (OpenTelemetry, Ollama, network)
3. **Test Error Paths**: Include both positive and negative test scenarios
4. **Environment Isolation**: Use `patch.dict(os.environ)` for environment variables
5. **Descriptive Names**: Use clear, descriptive test method names

### Example Test Pattern

```python
def test_feature_with_success_scenario(self, mock_chat_interface, opentelemetry_environment):
    """Test feature description with expected behavior."""
    with patch.dict(os.environ, opentelemetry_environment), \
         patch("module.function") as mock_function:
        
        # Setup
        mock_function.return_value = expected_value
        
        # Execute
        result = mock_chat_interface.method_under_test()
        
        # Assert
        assert result == expected_result
        mock_function.assert_called_with(expected_args)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all mocks are set up before imports
2. **Environment Variables**: Use `patch.dict(os.environ)` for isolation
3. **Thread Safety**: Be careful with threading tests and timeouts
4. **Mock Reset**: Reset mocks between tests if needed

### Debug Mode

Run tests with maximum verbosity:

```bash
pytest tests/test_opentelemetry_*.py -vvv --tb=long --capture=no
```

### Test Selection

Run specific test patterns:

```bash
# Run only initialization tests
pytest tests/test_opentelemetry_initialization.py::TestOpenTelemetryInitialization::test_service_name_configuration -v

# Run tests matching pattern
pytest tests/test_opentelemetry_*.py -k "test_timeout" -v
```

This comprehensive test suite ensures the OpenTelemetry implementation is robust, reliable, and properly handles all edge cases and error scenarios.