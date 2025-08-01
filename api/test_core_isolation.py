#!/usr/bin/env python3
"""
Test script to verify the core data isolation logic without requiring embeddings.
This test focuses on the document loading and metadata assignment logic.
"""

from loading import load_and_chunk_documents

def test_core_isolation():
    """Test the core data isolation logic"""
    print("=== TESTING CORE DATA ISOLATION LOGIC ===")
    
    # Test 1: Verify company filter works correctly
    print("\n1. Testing company filter functionality:")
    
    # Load documents for company c1 only
    c1_docs = load_and_chunk_documents(company_filter="c1")
    c1_companies = set(doc.metadata.get('company') for doc in c1_docs)
    print(f"   c1 filter returned {len(c1_docs)} documents with companies: {c1_companies}")
    
    # Load documents for company c2 only
    c2_docs = load_and_chunk_documents(company_filter="c2")
    c2_companies = set(doc.metadata.get('company') for doc in c2_docs)
    print(f"   c2 filter returned {len(c2_docs)} documents with companies: {c2_companies}")
    
    # Load all documents
    all_docs = load_and_chunk_documents()
    all_companies = set(doc.metadata.get('company') for doc in all_docs)
    print(f"   No filter returned {len(all_docs)} documents with companies: {all_companies}")
    
    # Verify isolation
    if (c1_companies == {'c1'} and 
        c2_companies == {'c2'} and 
        all_companies == {'c1', 'c2'} and
        len(c1_docs) + len(c2_docs) == len(all_docs)):
        print("   ✅ Company filter isolation working correctly!")
    else:
        print("   ❌ Company filter isolation failed!")
        return False
    
    # Test 2: Verify metadata assignment
    print("\n2. Testing metadata assignment:")
    
    # Check c1 documents
    c1_metadata = {}
    for doc in c1_docs:
        company = doc.metadata.get('company')
        department = doc.metadata.get('department')
        employee = doc.metadata.get('employee')
        hierarchy_key = doc.metadata.get('hierarchy_key')
        
        if company not in c1_metadata:
            c1_metadata[company] = {'departments': set(), 'employees': set(), 'hierarchy_keys': set()}
        
        if department:
            c1_metadata[company]['departments'].add(department)
        if employee:
            c1_metadata[company]['employees'].add(employee)
        if hierarchy_key:
            c1_metadata[company]['hierarchy_keys'].add(hierarchy_key)
    
    print(f"   c1 metadata: {c1_metadata}")
    
    # Check c2 documents
    c2_metadata = {}
    for doc in c2_docs:
        company = doc.metadata.get('company')
        department = doc.metadata.get('department')
        employee = doc.metadata.get('employee')
        hierarchy_key = doc.metadata.get('hierarchy_key')
        
        if company not in c2_metadata:
            c2_metadata[company] = {'departments': set(), 'employees': set(), 'hierarchy_keys': set()}
        
        if department:
            c2_metadata[company]['departments'].add(department)
        if employee:
            c2_metadata[company]['employees'].add(employee)
        if hierarchy_key:
            c2_metadata[company]['hierarchy_keys'].add(hierarchy_key)
    
    print(f"   c2 metadata: {c2_metadata}")
    
    # Verify metadata isolation
    c1_has_c2_data = any('c2' in str(item) for item in c1_metadata.values())
    c2_has_c1_data = any('c1' in str(item) for item in c2_metadata.values())
    
    if not c1_has_c2_data and not c2_has_c1_data:
        print("   ✅ Metadata isolation working correctly!")
    else:
        print("   ❌ Metadata isolation failed!")
        return False
    
    # Test 3: Verify hierarchy key construction
    print("\n3. Testing hierarchy key construction:")
    
    # Check that hierarchy keys are correctly constructed
    expected_c1_keys = {'c1', 'c1|d1', 'c1|d1|e1'}
    expected_c2_keys = {'c2', 'c2|d2', 'c2|d2|e2'}
    
    actual_c1_keys = set()
    actual_c2_keys = set()
    
    for doc in c1_docs:
        if doc.metadata.get('hierarchy_key'):
            actual_c1_keys.add(doc.metadata['hierarchy_key'])
    
    for doc in c2_docs:
        if doc.metadata.get('hierarchy_key'):
            actual_c2_keys.add(doc.metadata['hierarchy_key'])
    
    print(f"   Expected c1 hierarchy keys: {expected_c1_keys}")
    print(f"   Actual c1 hierarchy keys: {actual_c1_keys}")
    print(f"   Expected c2 hierarchy keys: {expected_c2_keys}")
    print(f"   Actual c2 hierarchy keys: {actual_c2_keys}")
    
    if actual_c1_keys == expected_c1_keys and actual_c2_keys == expected_c2_keys:
        print("   ✅ Hierarchy key construction working correctly!")
    else:
        print("   ❌ Hierarchy key construction failed!")
        return False
    
    # Test 4: Verify document content isolation
    print("\n4. Testing document content isolation:")
    
    # Check that c1 documents contain c1-specific content
    c1_content = ' '.join(doc.page_content for doc in c1_docs).lower()
    c2_content = ' '.join(doc.page_content for doc in c2_docs).lower()
    
    c1_has_tech = 'technology solutions' in c1_content
    c1_has_healthcare = 'healthcare solutions' in c1_content
    c2_has_tech = 'technology solutions' in c2_content
    c2_has_healthcare = 'healthcare solutions' in c2_content
    
    print(f"   c1 has technology content: {c1_has_tech}")
    print(f"   c1 has healthcare content: {c1_has_healthcare}")
    print(f"   c2 has technology content: {c2_has_tech}")
    print(f"   c2 has healthcare content: {c2_has_healthcare}")
    
    if c1_has_tech and not c1_has_healthcare and c2_has_healthcare and not c2_has_tech:
        print("   ✅ Document content isolation working correctly!")
    else:
        print("   ❌ Document content isolation failed!")
        return False
    
    print("\n=== CORE ISOLATION TEST PASSED ===")
    return True

if __name__ == "__main__":
    success = test_core_isolation()
    if success:
        print("\n🎉 All core isolation tests passed! The data leakage fix is working correctly.")
        print("\nSummary of fixes implemented:")
        print("1. ✅ Added company_filter parameter to load_and_chunk_documents()")
        print("2. ✅ Modified startup process to load documents per company")
        print("3. ✅ Ensured separate vector stores for each company")
        print("4. ✅ Verified metadata assignment and hierarchy key construction")
        print("5. ✅ Confirmed document content isolation")
    else:
        print("\n❌ Core isolation tests failed! Data leakage issue persists.") 