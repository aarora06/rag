import React, { useState } from 'react';
import axios from 'axios';

const UPLOAD_URL = 'http://127.0.0.1:8000/upload/';
const API_KEY = 'mu4jLFQ3IYFhYxj0ymBRqKgTkDxuadYdds2tkWSm'; // Use your backend API key

const FileUploadComponent: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [company, setCompany] = useState('');
  const [department, setDepartment] = useState('');
  const [employee, setEmployee] = useState('');
  const [level, setLevel] = useState('employee');
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
      setUploadMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !company.trim()) {
      setUploadMessage('Please select a file and enter a company name.');
      return;
    }
    setUploading(true);
    setUploadMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('company', company);
      if (department.trim()) formData.append('department', department);
      if (employee.trim()) formData.append('employee', employee);
      formData.append('level', level);

      await axios.post(UPLOAD_URL, formData, {
        headers: {
          'X-API-Key': API_KEY,
          'accept': 'application/json',
        },
      });
      setUploadMessage('File uploaded successfully!');
      setSelectedFile(null);
      setCompany('');
      setDepartment('');
      setEmployee('');
    } catch (error: any) {
      setUploadMessage('File upload failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{ marginBottom: '8px' }}>
        <input
          type="text"
          placeholder="Company (required)"
          value={company}
          onChange={e => setCompany(e.target.value)}
          disabled={uploading}
          style={{ marginRight: '8px' }}
          required
        />
        <input
          type="text"
          placeholder="Department (optional)"
          value={department}
          onChange={e => setDepartment(e.target.value)}
          disabled={uploading}
          style={{ marginRight: '8px' }}
        />
        <input
          type="text"
          placeholder="Employee (optional)"
          value={employee}
          onChange={e => setEmployee(e.target.value)}
          disabled={uploading}
        />
      </div>
      <input type="file" onChange={handleFileChange} disabled={uploading} />
      <input
        type="text"
        placeholder="Level (default: employee)"
        value={level}
        onChange={e => setLevel(e.target.value)}
        disabled={uploading}
        style={{ marginLeft: '8px', width: '160px' }}
      />
      <button
        onClick={handleUpload}
        disabled={!selectedFile || uploading}
        style={{ marginLeft: '10px' }}
      >
        {uploading ? 'Uploading...' : 'Upload'}
      </button>
      {uploadMessage && (
        <div style={{ marginTop: '8px', color: uploadMessage.includes('success') ? 'green' : 'red' }}>
          {uploadMessage}
        </div>
      )}
    </div>
  );
};

export default FileUploadComponent;