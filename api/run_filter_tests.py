#!/usr/bin/env python3
"""
Simple test runner for filter functionality tests.
Run this script to execute all filter-related tests.
"""

import sys
import os
import unittest

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_filter_tests():
    """Run all filter-related tests."""
    
    print("🧪 Running Filter Functionality Tests")
    print("=" * 50)
    
    # Import test modules
    try:
        from test_filters import (
            TestFilterVectorization,
            TestFilterRetrieval,
            TestFilterAPIEndpoints,
            TestFilterValidation
        )
    except ImportError as e:
        print(f"❌ Error importing test modules: {e}")
        print("Make sure all required dependencies are installed:")
        print("pip install fastapi httpx langchain langchain-openai langchain-chroma")
        return False
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestFilterVectorization,
        TestFilterRetrieval,
        TestFilterAPIEndpoints,
        TestFilterValidation
    ]
    
    for test_class in test_classes:
        test_suite.addTest(unittest.makeSuite(test_class))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    print(f"✅ Tests run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"⚠️  Errors: {len(result.errors)}")
    
    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
        print(f"📈 Success rate: {success_rate:.1f}%")
    else:
        print("📈 Success rate: N/A (no tests run)")
    
    # Print detailed results
    if result.failures:
        print(f"\n❌ FAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n⚠️  ERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    print(f"{'='*50}")
    
    # Return success/failure
    return len(result.failures) == 0 and len(result.errors) == 0

def run_specific_test(test_name):
    """Run a specific test by name."""
    print(f"🧪 Running specific test: {test_name}")
    print("=" * 50)
    
    try:
        from test_filters import (
            TestFilterVectorization,
            TestFilterRetrieval,
            TestFilterAPIEndpoints,
            TestFilterValidation
        )
    except ImportError as e:
        print(f"❌ Error importing test modules: {e}")
        return False
    
    # Map test names to classes
    test_classes = {
        'vectorization': TestFilterVectorization,
        'retrieval': TestFilterRetrieval,
        'api': TestFilterAPIEndpoints,
        'validation': TestFilterValidation
    }
    
    if test_name not in test_classes:
        print(f"❌ Unknown test: {test_name}")
        print(f"Available tests: {', '.join(test_classes.keys())}")
        return False
    
    # Run specific test
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(test_classes[test_name]))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print(f"\n📊 Results for {test_name}:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run filter functionality tests')
    parser.add_argument('--test', '-t', type=str, help='Run specific test (vectorization, retrieval, api, validation)')
    
    args = parser.parse_args()
    
    if args.test:
        success = run_specific_test(args.test)
    else:
        success = run_filter_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 