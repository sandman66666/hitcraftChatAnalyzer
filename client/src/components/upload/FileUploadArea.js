import React, { useState, useRef } from 'react';
import { Card, Button, ProgressBar } from 'react-bootstrap';
import { FaUpload, FaFileAlt, FaFileCode, FaFileCsv } from 'react-icons/fa';
import { useAnalyzer } from '../../context/AnalyzerContext';
import api from '../../services/api';
import './FileUploadArea.css';

const FileUploadArea = () => {
  const { actions } = useAnalyzer();
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  // Handle drag events
  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  // Handle file selection
  const handleFileSelected = (selectedFile) => {
    // Check file type
    const allowedTypes = ['application/json', 'text/plain'];
    if (!allowedTypes.includes(selectedFile.type)) {
      setUploadError('Please upload a JSON or TXT file');
      return;
    }

    setFile(selectedFile);
    setUploadError(null);
  };

  // Handle file input change
  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  // Handle upload button click
  const handleUpload = async () => {
    if (!file) return;

    try {
      setUploading(true);
      setUploadProgress(0);
      setUploadError(null);

      // Upload file
      const response = await api.uploadFile(file, (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        setUploadProgress(percentCompleted);
      });

      // Update app state with session info
      actions.setSession(response.data.session_id, response.data.filename);
      
      // Add a log
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `File uploaded successfully: ${file.name}`,
        level: 'success'
      });
      
      // Extract threads
      await extractThreads(response.data.session_id, response.data.filename);
      
    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error.response?.data?.error || 'Failed to upload file');
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Upload error: ${error.message}`,
        level: 'error'
      });
    } finally {
      setUploading(false);
    }
  };

  // Extract threads after upload
  const extractThreads = async (sessionId, filename) => {
    try {
      // Add log entry
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: 'Starting thread extraction...',
        level: 'info'
      });
      
      // Extract threads
      const response = await api.extractThreads(sessionId, filename);
      
      // Update thread count in state
      actions.setThreadCount(response.data.thread_count);
      actions.setThreadExtracted(true);
      
      // Add success log
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Extracted ${response.data.thread_count} threads`,
        level: 'success'
      });
      
    } catch (error) {
      console.error('Thread extraction error:', error);
      actions.setError(error.response?.data?.error || 'Failed to extract threads');
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Thread extraction error: ${error.message}`,
        level: 'error'
      });
    }
  };

  // Get file icon based on file type
  const getFileIcon = () => {
    if (!file) return <FaUpload size={48} />;
    
    const extension = file.name.split('.').pop().toLowerCase();
    
    switch (extension) {
      case 'json':
        return <FaFileCode size={48} />;
      case 'csv':
        return <FaFileCsv size={48} />;
      default:
        return <FaFileAlt size={48} />;
    }
  };

  return (
    <Card className="file-upload-card">
      <Card.Body>
        <div
          className={`upload-area ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !uploading && fileInputRef.current.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.txt"
            onChange={handleFileInputChange}
            className="file-input"
            disabled={uploading}
          />
          
          <div className="upload-icon">
            {getFileIcon()}
          </div>
          
          <div className="upload-text">
            {file ? (
              <>
                <h4 className="upload-filename">{file.name}</h4>
                <p className="upload-filesize">
                  {(file.size / 1024).toFixed(2)} KB
                </p>
              </>
            ) : (
              <>
                <h4>Drop your chat file here</h4>
                <p>or click to browse</p>
                <small className="text-muted">Supports JSON or TXT files</small>
              </>
            )}
          </div>
          
          {uploadError && (
            <div className="upload-error">
              {uploadError}
            </div>
          )}
          
          {uploading && (
            <div className="upload-progress">
              <ProgressBar 
                now={uploadProgress} 
                label={`${uploadProgress}%`}
                variant="info" 
                animated
              />
            </div>
          )}
        </div>
        
        {file && !uploading && (
          <div className="upload-actions">
            <Button 
              variant="outline-secondary" 
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
            >
              Change File
            </Button>
            <Button 
              variant="primary" 
              onClick={(e) => {
                e.stopPropagation();
                handleUpload();
              }}
            >
              Upload and Extract Threads
            </Button>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default FileUploadArea;
