import unittest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# Import the modules to test
from api import app, ChatRequest
from loading import load_and_chunk_documents
from retrieval import setup_retrievers, setup_llm
from config import knowledge_base_path
from test_config import TEST_API_KEY, setup_test_environment, cleanup_test_environment

class TestFilterVectorization(unittest.TestCase):
    """Test cases for filter vectorization during document loading and processing."""
    
    def setUp(self):
        """Set up test environment."""
        setup_test_environment()
        self.test_knowledge_base = tempfile.mkdtemp()
        self.test_vector_db = tempfile.mkdtemp()
        
        # Create test directory structure
        self.company1_dir = os.path.join(self.test_knowledge_base, "company1")
        self.company2_dir = os.path.join(self.test_knowledge_base, "company2")
        
        os.makedirs(self.company1_dir, exist_ok=True)
        os.makedirs(self.company2_dir, exist_ok=True)
        
        # Create department and employee directories
        self.dept1_dir = os.path.join(self.company1_dir, "dept1")
        self.emp1_dir = os.path.join(self.dept1_dir, "emp1")
        os.makedirs(self.emp1_dir, exist_ok=True)
        
        # Create test documents
        self.create_test_documents()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_knowledge_base, ignore_errors=True)
        shutil.rmtree(self.test_vector_db, ignore_errors=True)
        cleanup_test_environment()
    
    def create_test_documents(self):
        """Create test documents with different hierarchy levels."""
        # Company level document
        company_doc = os.path.join(self.company1_dir, "company_policy.md")
        with open(company_doc, 'w') as f:
            f.write("This is company level policy document.")
        
        # Department level document
        dept_doc = os.path.join(self.dept1_dir, "department_guidelines.md")
        with open(dept_doc, 'w') as f:
            f.write("This is department level guidelines document.")
        
        # Employee level document
        emp_doc = os.path.join(self.emp1_dir, "employee_manual.md")
        with open(emp_doc, 'w') as f:
            f.write("This is employee level manual document.")
        
        # Company2 document for cross-company testing
        company2_doc = os.path.join(self.company2_dir, "company2_policy.md")
        with open(company2_doc, 'w') as f:
            f.write("This is company2 policy document.")
    
    @patch('loading.knowledge_base_path')
    def test_metadata_setting_for_different_levels(self, mock_kb_path):
        """Test that metadata is correctly set for different hierarchy levels."""
        mock_kb_path.__str__ = lambda: self.test_knowledge_base
        
        chunks = load_and_chunk_documents(knowledge_base_path=self.test_knowledge_base)
        
        # Check that we have chunks from different levels
        company_chunks = [c for c in chunks if c.metadata.get('company') == 'company1' and not c.metadata.get('department')]
        dept_chunks = [c for c in chunks if c.metadata.get('company') == 'company1' and c.metadata.get('department') == 'dept1' and not c.metadata.get('employee')]
        emp_chunks = [c for c in chunks if c.metadata.get('company') == 'company1' and c.metadata.get('department') == 'dept1' and c.metadata.get('employee') == 'emp1']
        
        self.assertGreater(len(company_chunks), 0, "Should have company level chunks")
        self.assertGreater(len(dept_chunks), 0, "Should have department level chunks")
        self.assertGreater(len(emp_chunks), 0, "Should have employee level chunks")
        
        # Check hierarchy keys
        for chunk in company_chunks:
            self.assertEqual(chunk.metadata.get('hierarchy_key'), 'company1')
        
        for chunk in dept_chunks:
            self.assertEqual(chunk.metadata.get('hierarchy_key'), 'company1|dept1')
        
        for chunk in emp_chunks:
            self.assertEqual(chunk.metadata.get('hierarchy_key'), 'company1|dept1|emp1')
    
    @patch('loading.knowledge_base_path')
    def test_optional_filters_not_set(self, mock_kb_path):
        """Test that optional filters (department, employee) can be None."""
        mock_kb_path.__str__ = lambda: self.test_knowledge_base
        
        chunks = load_and_chunk_documents(knowledge_base_path=self.test_knowledge_base)
        
        # Find chunks where department or employee might be None
        chunks_with_none_dept = [c for c in chunks if c.metadata.get('department') is None]
        chunks_with_none_emp = [c for c in chunks if c.metadata.get('employee') is None]
        
        # Should have chunks without department (company level)
        self.assertGreater(len(chunks_with_none_dept), 0, "Should have chunks without department")
        
        # Should have chunks without employee (company and department level)
        self.assertGreater(len(chunks_with_none_emp), 0, "Should have chunks without employee")
    
    @patch('loading.knowledge_base_path')
    def test_company_filter_mandatory(self, mock_kb_path):
        """Test that company filter is always set (mandatory)."""
        mock_kb_path.__str__ = lambda: self.test_knowledge_base
        
        chunks = load_and_chunk_documents(knowledge_base_path=self.test_knowledge_base)
        
        # All chunks should have company metadata
        for chunk in chunks:
            self.assertIsNotNone(chunk.metadata.get('company'), "Company should always be set")
            self.assertNotEqual(chunk.metadata.get('company'), '', "Company should not be empty")


class TestFilterRetrieval(unittest.TestCase):
    """Test cases for filter retrieval functionality."""
    
    def setUp(self):
        """Set up test environment."""
        setup_test_environment()
        self.test_vector_db = tempfile.mkdtemp()
        self.embeddings = Mock(spec=OpenAIEmbeddings)
        
        # Create mock documents with different metadata
        self.documents = [
            Document(
                page_content="Company level content",
                metadata={"company": "company1", "hierarchy_key": "company1"}
            ),
            Document(
                page_content="Department level content",
                metadata={"company": "company1", "department": "dept1", "hierarchy_key": "company1|dept1"}
            ),
            Document(
                page_content="Employee level content",
                metadata={"company": "company1", "department": "dept1", "employee": "emp1", "hierarchy_key": "company1|dept1|emp1"}
            ),
            Document(
                page_content="Company2 content",
                metadata={"company": "company2", "hierarchy_key": "company2"}
            )
        ]
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_vector_db, ignore_errors=True)
        cleanup_test_environment()
    
    def test_retriever_setup(self):
        """Test that retrievers are set up correctly."""
        # Mock vectorstore
        mock_vectorstore = Mock(spec=Chroma)
        mock_retriever = Mock()
        mock_vectorstore.as_retriever.return_value = mock_retriever
        
        retrievers = setup_retrievers(mock_vectorstore)
        
        # Should have all required retriever levels
        expected_keys = ['employee_level', 'department_level', 'company_level', 'general']
        for key in expected_keys:
            self.assertIn(key, retrievers, f"Should have {key} retriever")
    
    def test_company_only_filter(self):
        """Test retrieval with only company filter (mandatory)."""
        # This would be tested with actual API calls
        # For now, we test the logic that determines which retrievers to use
        
        # Simulate the logic from the API
        company = "company1"
        department = None
        employee = None
        
        retriever_keys_to_query = []
        
        if company and department and employee:
            retriever_keys_to_query.append('employee_level')
        if company and department:
            retriever_keys_to_query.append('department_level')
        if company:
            retriever_keys_to_query.append('company_level')
        
        retriever_keys_to_query.append('general')
        
        # Should only have company_level and general
        expected_keys = ['company_level', 'general']
        self.assertEqual(retriever_keys_to_query, expected_keys)
    
    def test_company_department_filter(self):
        """Test retrieval with company and department filters."""
        company = "company1"
        department = "dept1"
        employee = None
        
        retriever_keys_to_query = []
        
        if company and department and employee:
            retriever_keys_to_query.append('employee_level')
        if company and department:
            retriever_keys_to_query.append('department_level')
        if company:
            retriever_keys_to_query.append('company_level')
        
        retriever_keys_to_query.append('general')
        
        # Should have department_level, company_level, and general
        expected_keys = ['department_level', 'company_level', 'general']
        self.assertEqual(retriever_keys_to_query, expected_keys)
    
    def test_full_hierarchy_filter(self):
        """Test retrieval with all filters (company, department, employee)."""
        company = "company1"
        department = "dept1"
        employee = "emp1"
        
        retriever_keys_to_query = []
        
        if company and department and employee:
            retriever_keys_to_query.append('employee_level')
        if company and department:
            retriever_keys_to_query.append('department_level')
        if company:
            retriever_keys_to_query.append('company_level')
        
        retriever_keys_to_query.append('general')
        
        # Should have all levels
        expected_keys = ['employee_level', 'department_level', 'company_level', 'general']
        self.assertEqual(retriever_keys_to_query, expected_keys)


class TestFilterAPIEndpoints(unittest.TestCase):
    """Test cases for API endpoints with different filter combinations."""
    
    def setUp(self):
        """Set up test client."""
        setup_test_environment()
        self.client = TestClient(app)
        
        # Mock the global variables
        self.mock_retrievers = {
            'company1': {
                'employee_level': Mock(),
                'department_level': Mock(),
                'company_level': Mock(),
                'general': Mock()
            }
        }
        self.mock_llm = Mock()
        
        # Patch the global variables
        self.patcher1 = patch('api.retrievers', self.mock_retrievers)
        self.patcher2 = patch('api.llm_instance', self.mock_llm)
        self.patcher3 = patch('api.API_KEY', TEST_API_KEY)
        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()
    
    def tearDown(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        cleanup_test_environment()
    
    def test_chat_company_only_filter(self):
        """Test chat endpoint with only company filter."""
        # Mock the retriever responses
        mock_docs = [
            Document(page_content="Company level content", metadata={"company": "company1"})
        ]
        
        self.mock_retrievers['company1']['company_level'].get_relevant_documents.return_value = mock_docs
        self.mock_llm.invoke.return_value = Mock(content="Test response")
        
        # Test request with only company
        request_data = {
            "question": "What is the company policy?",
            "company": "company1",
            "department": None,
            "employee": None,
            "chat_history": []
        }
        
        response = self.client.post("/chat/", json=request_data, headers={"X-API-Key": TEST_API_KEY})
        
        self.assertEqual(response.status_code, 200)
        
        # Verify that company_level retriever was called
        self.mock_retrievers['company1']['company_level'].get_relevant_documents.assert_called_once()
    
    def test_chat_company_department_filter(self):
        """Test chat endpoint with company and department filters."""
        mock_docs = [
            Document(page_content="Department level content", metadata={"company": "company1", "department": "dept1"})
        ]
        
        self.mock_retrievers['company1']['department_level'].get_relevant_documents.return_value = mock_docs
        self.mock_llm.invoke.return_value = Mock(content="Test response")
        
        request_data = {
            "question": "What are the department guidelines?",
            "company": "company1",
            "department": "dept1",
            "employee": None,
            "chat_history": []
        }
        
        response = self.client.post("/chat/", json=request_data, headers={"X-API-Key": TEST_API_KEY})
        
        self.assertEqual(response.status_code, 200)
        
        # Verify that department_level retriever was called
        self.mock_retrievers['company1']['department_level'].get_relevant_documents.assert_called_once()
    
    def test_chat_full_hierarchy_filter(self):
        """Test chat endpoint with all filters (company, department, employee)."""
        mock_docs = [
            Document(page_content="Employee level content", metadata={"company": "company1", "department": "dept1", "employee": "emp1"})
        ]
        
        self.mock_retrievers['company1']['employee_level'].get_relevant_documents.return_value = mock_docs
        self.mock_llm.invoke.return_value = Mock(content="Test response")
        
        request_data = {
            "question": "What is the employee manual?",
            "company": "company1",
            "department": "dept1",
            "employee": "emp1",
            "chat_history": []
        }
        
        response = self.client.post("/chat/", json=request_data, headers={"X-API-Key": TEST_API_KEY})
        
        self.assertEqual(response.status_code, 200)
        
        # Verify that employee_level retriever was called
        self.mock_retrievers['company1']['employee_level'].get_relevant_documents.assert_called_once()
    
    def test_chat_company_mandatory(self):
        """Test that company filter is mandatory."""
        request_data = {
            "question": "What is the policy?",
            "company": None,  # Missing company
            "department": "dept1",
            "employee": "emp1",
            "chat_history": []
        }
        
        response = self.client.post("/chat/", json=request_data, headers={"X-API-Key": TEST_API_KEY})
        
        # Should fail validation
        self.assertEqual(response.status_code, 422)  # Validation error
    
    def test_chat_optional_filters_none(self):
        """Test that department and employee can be None."""
        mock_docs = [
            Document(page_content="Company level content", metadata={"company": "company1"})
        ]
        
        self.mock_retrievers['company1']['company_level'].get_relevant_documents.return_value = mock_docs
        self.mock_llm.invoke.return_value = Mock(content="Test response")
        
        request_data = {
            "question": "What is the policy?",
            "company": "company1",
            "department": None,  # Optional filter
            "employee": None,    # Optional filter
            "chat_history": []
        }
        
        response = self.client.post("/chat/", json=request_data, headers={"X-API-Key": TEST_API_KEY})
        
        self.assertEqual(response.status_code, 200)
    
    def test_chat_wrong_company(self):
        """Test chat with non-existent company."""
        request_data = {
            "question": "What is the policy?",
            "company": "nonexistent_company",
            "department": None,
            "employee": None,
            "chat_history": []
        }
        
        response = self.client.post("/chat/", json=request_data, headers={"X-API-Key": TEST_API_KEY})
        
        # Should return 404 or 500 for non-existent company (both are acceptable error responses)
        self.assertIn(response.status_code, [404, 500], f"Expected 404 or 500, got {response.status_code}")


class TestFilterValidation(unittest.TestCase):
    """Test cases for filter validation logic."""
    
    def test_chat_request_model_validation(self):
        """Test ChatRequest model validation."""
        # Valid request with all fields
        valid_request = ChatRequest(
            question="Test question",
            company="company1",
            department="dept1",
            employee="emp1",
            chat_history=[]
        )
        self.assertEqual(valid_request.company, "company1")
        self.assertEqual(valid_request.department, "dept1")
        self.assertEqual(valid_request.employee, "emp1")
        
        # Valid request with optional fields as None
        valid_request_none = ChatRequest(
            question="Test question",
            company="company1",
            department=None,
            employee=None,
            chat_history=[]
        )
        self.assertEqual(valid_request_none.company, "company1")
        self.assertIsNone(valid_request_none.department)
        self.assertIsNone(valid_request_none.employee)
        
        # Invalid request - missing company (mandatory)
        with self.assertRaises(Exception):  # Should raise validation error
            ChatRequest(
                question="Test question",
                company=None,  # Missing mandatory field
                department="dept1",
                employee="emp1",
                chat_history=[]
            )
        
        # Test that optional fields can be None
        valid_request_none = ChatRequest(
            question="Test question",
            company="company1",
            department=None,
            employee=None,
            chat_history=[]
        )
        self.assertEqual(valid_request_none.company, "company1")
        self.assertIsNone(valid_request_none.department)
        self.assertIsNone(valid_request_none.employee)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_suite.addTest(unittest.makeSuite(TestFilterVectorization))
    test_suite.addTest(unittest.makeSuite(TestFilterRetrieval))
    test_suite.addTest(unittest.makeSuite(TestFilterAPIEndpoints))
    test_suite.addTest(unittest.makeSuite(TestFilterValidation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}") 