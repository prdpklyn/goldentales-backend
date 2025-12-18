# GoldenTales Testing Guide

> Comprehensive guide for running and understanding the test suite

## Overview

The GoldenTales backend has comprehensive test coverage including:
- **Unit Tests**: Individual components and services
- **Integration Tests**: Service interactions and Edge Function integration
- **End-to-End Tests**: Complete workflows from API to database

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── fixtures/                      # Reusable test fixtures
│   ├── edge_functions.py         # Edge Function mocks
│   ├── fal_ai.py                 # Fal.ai service mocks
│   ├── gemini.py                  # Gemini service mocks
│   └── storage.py                 # Storage service mocks
├── test_v2_api_books.py          # V2 Books API tests
├── test_v2_api_photo.py          # V2 Photo Character API tests
├── test_storage_service.py       # StorageService tests
├── test_print_service.py         # PrintService tests
├── test_photo_character_service.py  # PhotoCharacterService tests
├── test_integration_e2e.py       # End-to-end integration tests
├── test_database_edge_service.py # Database Edge Service tests
├── test_api_books.py             # V1 Books API tests
├── test_api_orders.py            # Orders API tests
├── test_order_service.py         # OrderService tests
├── test_middleware.py             # Middleware tests
├── test_error_handling.py        # Error handling tests
└── test_config_management.py     # Configuration management tests
```

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-asyncio pytest-mock httpx
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Run Specific Test Suites

```bash
# V2 API tests
pytest tests/test_v2_api_books.py -v
pytest tests/test_v2_api_photo.py -v

# Service tests
pytest tests/test_storage_service.py -v
pytest tests/test_print_service.py -v
pytest tests/test_photo_character_service.py -v

# Integration tests
pytest tests/test_integration_e2e.py -v

# Database tests
pytest tests/test_database_edge_service.py -v
```

### Run Tests by Category

```bash
# Run only unit tests
pytest -m "not integration" -v

# Run only integration tests
pytest -m integration -v

# Run only API tests
pytest tests/test_*_api_*.py -v
```

## Test Coverage

### V2 API Tests (`test_v2_api_books.py`)

**Coverage:**
- ✅ BASIC tier book creation
- ✅ PREMIUM tier book creation
- ✅ ULTRA tier book creation (with photo reference)
- ✅ Book retrieval by ID
- ✅ Page regeneration (all tiers)
- ✅ Book preview endpoint
- ✅ Error handling (not found, validation errors)
- ✅ Edge Function integration

**Key Test Cases:**
- `test_create_basic_tier_book` - Creates BASIC tier book
- `test_create_premium_tier_book` - Creates PREMIUM tier with tier-aware generation
- `test_create_ultra_tier_book` - Creates ULTRA tier with character reference
- `test_create_ultra_tier_missing_reference_url` - Validates ULTRA requirements
- `test_get_book_success` - Retrieves book from Edge Functions
- `test_regenerate_page_basic_tier` - Regenerates page for BASIC tier
- `test_regenerate_page_premium_tier` - Regenerates page for PREMIUM tier

### V2 Photo API Tests (`test_v2_api_photo.py`)

**Coverage:**
- ✅ Photo validation (success, no face, low quality)
- ✅ Character preview generation
- ✅ Character approval workflow
- ✅ Preview status retrieval
- ✅ Error handling (invalid URLs, expired sessions)

**Key Test Cases:**
- `test_validate_photo_success` - Validates valid photo
- `test_validate_photo_no_face` - Handles missing face
- `test_preview_character_success` - Generates character preview
- `test_approve_character_success` - Approves character for use
- `test_get_preview_status_success` - Retrieves preview session

### Storage Service Tests (`test_storage_service.py`)

**Coverage:**
- ✅ PDF upload with retry logic
- ✅ Signed URL generation
- ✅ Print image upload
- ✅ Error handling and resilience
- ✅ Circuit breaker behavior

**Key Test Cases:**
- `test_upload_order_pdf_success` - Uploads PDF successfully
- `test_upload_order_pdf_with_retry` - Retries on transient errors
- `test_get_order_pdf_url_success` - Generates signed URLs
- `test_upload_and_retrieve_pdf_workflow` - Complete upload/retrieve flow

### Print Service Tests (`test_print_service.py`)

**Coverage:**
- ✅ PDF generation for all tiers (Basic, Premium, Ultra)
- ✅ Image upscaling for print quality
- ✅ Order processing workflow
- ✅ Error handling

**Key Test Cases:**
- `test_generate_pdf_basic_tier` - Generates PDF for BASIC tier
- `test_generate_pdf_premium_tier` - Generates PDF for PREMIUM tier
- `test_generate_pdf_ultra_tier` - Generates PDF for ULTRA tier
- `test_upscale_images_for_print` - Upscales images for print
- `test_process_order_digital` - Processes digital order
- `test_process_order_physical` - Processes physical order with upscaling

### Photo Character Service Tests (`test_photo_character_service.py`)

**Coverage:**
- ✅ Photo validation (face detection, quality checks)
- ✅ Character preview generation
- ✅ Preview session management
- ✅ Character approval workflow
- ✅ Complete photo-to-character workflow

**Key Test Cases:**
- `test_validate_photo_success` - Validates photo successfully
- `test_generate_character_preview_success` - Generates preview
- `test_approve_character_success` - Approves character
- `test_complete_photo_to_character_workflow` - End-to-end workflow

### Integration Tests (`test_integration_e2e.py`)

**Coverage:**
- ✅ Complete book creation → order → PDF workflow
- ✅ Photo validation → preview → approval → book creation
- ✅ Order processing with upscaling and PDF generation
- ✅ Error recovery and resilience

**Key Test Cases:**
- `test_complete_basic_tier_workflow` - Full BASIC tier workflow
- `test_photo_to_ultra_tier_book_workflow` - Photo to ULTRA book workflow
- `test_order_processing_workflow` - Complete order processing
- `test_book_creation_partial_failure_recovery` - Error recovery

## Test Fixtures

### Edge Functions Fixtures (`fixtures/edge_functions.py`)

Provides mocked Edge Function clients and database services:

```python
@pytest.fixture
def mock_database_edge_service():
    """Mock DatabaseEdgeService with all CRUD operations."""
    # Returns mocked service with AsyncMock methods
```

### Fal.ai Fixtures (`fixtures/fal_ai.py`)

Provides mocked Fal.ai image generation:

```python
@pytest.fixture
def mock_fal_ai_service():
    """Mock Fal.ai service for image generation."""
```

### Gemini Fixtures (`fixtures/gemini.py`)

Provides mocked Gemini story generation:

```python
@pytest.fixture
def mock_gemini_service():
    """Mock Gemini service for story generation."""
```

### Storage Fixtures (`fixtures/storage.py`)

Provides mocked storage service:

```python
@pytest.fixture
def mock_storage_service():
    """Mock StorageService for PDF and image storage."""
```

## Mocking Strategy

### External Services

All external services are mocked to:
- **Avoid API costs** during testing
- **Ensure fast test execution**
- **Test error scenarios** without actual failures
- **Isolate unit tests** from external dependencies

### Edge Functions

Edge Functions are mocked using `AsyncMock` to:
- **Test without actual Supabase deployment**
- **Simulate various response scenarios**
- **Test error handling** (404, 500, timeouts)

### Database

Database operations are mocked via Edge Function mocks:
- **No actual database required**
- **Fast test execution**
- **Test data isolation**

## Writing New Tests

### Test Naming Convention

```python
def test_<component>_<action>_<expected_outcome>():
    """Test description."""
    # Test implementation
```

Examples:
- `test_create_basic_tier_book` - Creates BASIC tier book
- `test_get_book_not_found` - Handles book not found
- `test_upload_order_pdf_with_retry` - Retries on failure

### Using Fixtures

```python
@pytest.mark.asyncio
async def test_example(mock_database_edge_service, client):
    """Example test using fixtures."""
    # Use mocked services
    result = await mock_database_edge_service.get_story("story-123")
    assert result is not None
```

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await some_async_function()
    assert result is not None
```

### Testing Error Cases

```python
def test_error_handling():
    """Test error handling."""
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_raises_error()
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-mock
      - name: Run tests
        run: pytest -v --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Test Metrics

### Current Coverage

- **V2 API Endpoints**: 95%+ coverage
- **Services**: 90%+ coverage
- **Error Handling**: 85%+ coverage
- **Integration Workflows**: 80%+ coverage

### Running Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure all dependencies are installed
   pip install -r requirements.txt
   ```

2. **Async Test Failures**
   ```python
   # Ensure @pytest.mark.asyncio decorator is used
   @pytest.mark.asyncio
   async def test_async():
       ...
   ```

3. **Mock Not Working**
   ```python
   # Ensure correct import path for mocking
   @patch("app.routers.v2.books.get_database")
   ```

4. **Fixture Not Found**
   ```python
   # Ensure fixture is in conftest.py or imported
   # Check fixture name matches exactly
   ```

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Use Fixtures**: Reuse common test data and mocks
3. **Test Edge Cases**: Include error scenarios and boundary conditions
4. **Keep Tests Fast**: Mock external services
5. **Clear Assertions**: Use descriptive assertion messages
6. **Test Documentation**: Document complex test scenarios

## Next Steps

- [ ] Add performance tests for high-load scenarios
- [ ] Add contract tests for Edge Functions
- [ ] Add visual regression tests for PDF generation
- [ ] Add load tests for concurrent requests
- [ ] Add security tests for authentication/authorization

---

*Last updated: December 16, 2024*

