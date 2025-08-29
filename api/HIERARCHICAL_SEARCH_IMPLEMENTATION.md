# Hierarchical Search Implementation

## Overview

The hierarchical search functionality has been successfully implemented to address the user's requirement: **"During the chat, when the employee searches for information, look for information that matches employee filter, department filter and company filter and then send the information together to LLM for processing."**

## Key Changes Made

### 1. Modified Chat Endpoint Logic (`api.py`)

**Before**: The system would stop at the first level where documents were found
**After**: The system now collects information from all relevant levels and sends them together to the LLM

#### Key Changes:

**A. Hierarchical Retrieval Logic:**
```python
# 2. Perform hierarchical retrieval - collect information from all relevant levels
retrieved_docs = []
level_docs = {}  # Track documents by level for better context organization

# Determine which retrieval levels to use based on provided filters
retriever_keys_to_query = []

# Collect from most specific to most general levels
if company and department and employee:
    retriever_keys_to_query.append('employee_level')
if company and department:
    retriever_keys_to_query.append('department_level')
if company:
    retriever_keys_to_query.append('company_level')

# Add general level last for broader context
retriever_keys_to_query.append('general')
```

**B. Context Organization:**
```python
# 3. Prepare the context for the LLM with hierarchical organization
context_sections = []

# Add context from each level, organized by hierarchy
if level_docs:
    # Employee level (most specific)
    if 'employee_level' in level_docs and level_docs['employee_level']:
        employee_content = "\n\n".join([doc.page_content for doc in level_docs['employee_level']])
        context_sections.append(f"EMPLOYEE-SPECIFIC INFORMATION:\n{employee_content}")
    
    # Department level
    if 'department_level' in level_docs and level_docs['department_level']:
        department_content = "\n\n".join([doc.page_content for doc in level_docs['department_level']])
        context_sections.append(f"DEPARTMENT-LEVEL INFORMATION:\n{department_content}")
    
    # Company level
    if 'company_level' in level_docs and level_docs['company_level']:
        company_content = "\n\n".join([doc.page_content for doc in level_docs['company_level']])
        context_sections.append(f"COMPANY-LEVEL INFORMATION:\n{company_content}")
    
    # General level (broadest)
    if 'general' in level_docs and level_docs['general']:
        general_content = "\n\n".join([doc.page_content for doc in level_docs['general']])
        context_sections.append(f"GENERAL COMPANY INFORMATION:\n{general_content}")
```

**C. Enhanced System Message:**
```python
system_message_content = f"""You are a helpful AI assistant for {company}. Use the following hierarchical context to answer the user's question. 

The context is organized by levels of specificity:
- EMPLOYEE-SPECIFIC INFORMATION: Most relevant to the specific employee
- DEPARTMENT-LEVEL INFORMATION: Relevant to the department
- COMPANY-LEVEL INFORMATION: General company information
- GENERAL COMPANY INFORMATION: Broad company context

Prioritize information from more specific levels (employee > department > company > general) when available. 
If you don't know the answer from the context, say you don't know.

Context:{context_text}"""
```

## How It Works

### 1. **Employee-Level Search** (company + department + employee)
When an employee searches for information, the system:
- Queries `employee_level` for employee-specific documents
- Queries `department_level` for department-wide documents
- Queries `company_level` for company-wide documents
- Queries `general` for broad company context
- Organizes all found information by hierarchy level
- Sends comprehensive context to LLM with clear instructions

### 2. **Department-Level Search** (company + department)
When a department-level search is performed:
- Queries `department_level` for department-specific documents
- Queries `company_level` for company-wide documents
- Queries `general` for broad company context
- Organizes information by hierarchy level

### 3. **Company-Level Search** (company only)
When a company-level search is performed:
- Queries `company_level` for company-specific documents
- Queries `general` for broad company context
- Organizes information by hierarchy level

## Benefits

### 1. **Comprehensive Information Retrieval**
- Employees get access to information from all relevant levels
- No information is missed due to stopping at the first level
- Context is enriched with broader company information

### 2. **Better LLM Understanding**
- Information is clearly organized by hierarchy levels
- LLM receives clear instructions on how to prioritize information
- More specific information is prioritized over general information

### 3. **Maintained Data Isolation**
- Company isolation is preserved
- No cross-company data leakage
- Each company only sees its own hierarchical information

### 4. **Improved User Experience**
- Employees get more comprehensive answers
- Context includes both specific and general information
- Better understanding of how information relates to their role

## Example Scenarios

### Scenario 1: Employee Search
**User Query**: "What is my role and what does my department do?"

**System Response**:
- Collects employee-specific information (role, responsibilities)
- Collects department-level information (department functions, team structure)
- Collects company-level information (company overview, policies)
- Organizes all information hierarchically
- LLM provides comprehensive answer with context from all levels

### Scenario 2: Department Search
**User Query**: "What does my department handle?"

**System Response**:
- Collects department-level information (department functions, projects)
- Collects company-level information (company context, policies)
- Organizes information hierarchically
- LLM provides answer with department and company context

### Scenario 3: Company Search
**User Query**: "What does my company specialize in?"

**System Response**:
- Collects company-level information (company overview, specialization)
- Collects general company information (broader context)
- Organizes information hierarchically
- LLM provides comprehensive company overview

## Testing Results

All tests pass successfully:

✅ **Hierarchical Search Logic**: Correctly determines which levels to query based on provided filters
✅ **Context Organization**: Properly organizes information by hierarchy levels
✅ **System Message Generation**: Creates clear instructions for LLM
✅ **Data Isolation**: Maintains company separation
✅ **Core Functionality**: All existing functionality remains intact

## Files Modified

1. **`api.py`**: Updated chat endpoint to implement hierarchical search
2. **`test_hierarchical_logic.py`**: Created test suite for hierarchical search logic
3. **`test_core_isolation.py`**: Verified data isolation still works
4. **`HIERARCHICAL_SEARCH_IMPLEMENTATION.md`**: This documentation

## Conclusion

The hierarchical search implementation successfully addresses the user's requirement by:

1. **Collecting information from all relevant levels** (employee, department, company, general)
2. **Organizing information hierarchically** for better LLM understanding
3. **Sending comprehensive context** to the LLM for processing
4. **Maintaining data isolation** between companies
5. **Providing clear instructions** to the LLM on how to prioritize information

The system now provides employees with comprehensive, context-rich responses that include information from their specific level as well as broader organizational context, leading to better-informed answers and improved user experience. 