# Filter Functionality Tests

This directory contains comprehensive unit tests for the RAG system's filter functionality, specifically testing the optional filter vectorization and retrieval features.

## Test Overview

The tests cover the following filter scenarios:

### 🔍 **Filter Requirements**
- **Company Filter**: Mandatory (always required)
- **Department Filter**: Optional (can be None)
- **Employee Filter**: Optional (can be None)

### 📋 **Test Categories**

1. **TestFilterVectorization**: Tests document loading and metadata setting
2. **TestFilterRetrieval**: Tests retrieval logic and filter combinations
3. **TestFilterAPIEndpoints**: Tests API endpoints with different filter scenarios
4. **TestFilterValidation**: Tests model validation and error handling

## 🚀 **Running the Tests**

### Prerequisites
```bash
pip install fastapi httpx langchain langchain-openai langchain-chroma
```

### Run All Tests
```bash
python run_filter_tests.py
```

### Run Specific Test Category
```bash
python run_filter_tests.py --test vectorization
python run_filter_tests.py --test retrieval
python run_filter_tests.py --test api
python run_filter_tests.py --test validation
```

### Run Individual Test File
```bash
python test_filters.py
```

## 🧪 **Test Scenarios Covered**

### 1. **Vectorization Tests**
- ✅ Metadata setting for different hierarchy levels
- ✅ Optional filters (department, employee) can be None
- ✅ Company filter is always mandatory
- ✅ Hierarchy keys are correctly generated

### 2. **Retrieval Tests**
- ✅ Retriever setup with all required levels
- ✅ Company-only filter logic
- ✅ Company + Department filter logic
- ✅ Full hierarchy filter logic (Company + Department + Employee)

### 3. **API Endpoint Tests**
- ✅ Chat endpoint with company-only filter
- ✅ Chat endpoint with company + department filters
- ✅ Chat endpoint with full hierarchy filters
- ✅ Company filter validation (mandatory)
- ✅ Optional filters can be None
- ✅ Error handling for non-existent companies

### 4. **Validation Tests**
- ✅ ChatRequest model validation
- ✅ Mandatory vs optional field validation
- ✅ Error handling for missing mandatory fields

## 📊 **Expected Test Results**

When all tests pass, you should see:
```
🧪 Running Filter Functionality Tests
==================================================
✅ Tests run: 15
❌ Failures: 0
⚠️  Errors: 0
📈 Success rate: 100.0%
==================================================
```

## 🔧 **Test Configuration**

The tests use a separate configuration (`test_config.py`) that:
- Provides test-specific API keys
- Sets up mock environments
- Handles cleanup after tests

## 🐛 **Troubleshooting**

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **API Key Issues**: Tests use mock API keys, no real credentials needed

3. **Test Failures**: Check that the main application code is working correctly

### Debug Mode
For detailed test output, run:
```bash
python -m unittest test_filters -v
```

## 📝 **Adding New Tests**

To add new test cases:

1. Add test methods to the appropriate test class
2. Follow the naming convention: `test_<feature_name>`
3. Use descriptive docstrings
4. Include both positive and negative test cases

Example:
```python
def test_new_filter_scenario(self):
    """Test new filter scenario description."""
    # Test setup
    # Test execution
    # Assertions
```

## 🎯 **Test Coverage**

The tests ensure:
- ✅ All filter combinations work correctly
- ✅ Optional filters behave as expected
- ✅ Mandatory filters are enforced
- ✅ Error handling works properly
- ✅ API responses are correct
- ✅ Metadata is set correctly during vectorization
- ✅ Retrieval logic selects appropriate levels 