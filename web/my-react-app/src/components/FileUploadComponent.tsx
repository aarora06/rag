import React, { useState } from 'react';
import axios from 'axios';

const UPLOAD_URL = 'http://127.0.0.1:8000/upload/';
const API_KEY = 'mu4jLFQ3IYFhYxj0ymBRqKgTkDxuadYdds2tkWSm'; // Use your backend API key

const FileUploadComponent: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
      setUploadMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      await axios.post(UPLOAD_URL, formData, {
        headers: {
          'X-API-Key': API_KEY,
          'Content-Type': 'multipart/form-data',
        },
      });
      setUploadMessage('File uploaded successfully!');
      setSelectedFile(null);
    } catch (error: any) {
      setUploadMessage('File upload failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ marginBottom: '20px' }}>
      <input type="file" onChange={handleFileChange} disabled={uploading} />
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