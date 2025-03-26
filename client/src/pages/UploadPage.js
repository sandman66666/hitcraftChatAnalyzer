import React from 'react';
import { Row, Col, Card } from 'react-bootstrap';
import FileUploadArea from '../components/upload/FileUploadArea';
import ProcessingLog from '../components/common/ProcessingLog';
import { useAnalyzer } from '../context/AnalyzerContext';
import './Pages.css';

const UploadPage = () => {
  const { state } = useAnalyzer();
  const { logs } = state;

  return (
    <div className="upload-page">
      <h2 className="page-title">Upload Chat File</h2>
      <p className="page-description">
        Upload your conversation data for analysis. We support JSON files exported from messaging platforms.
      </p>
      
      <Row className="mt-4">
        <Col lg={8}>
          <FileUploadArea />
        </Col>
        
        <Col lg={4}>
          <div className="log-container">
            <ProcessingLog logs={logs} />
          </div>
        </Col>
      </Row>
    </div>
  );
};

export default UploadPage;
