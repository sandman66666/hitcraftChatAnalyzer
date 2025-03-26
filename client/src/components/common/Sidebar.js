import React from 'react';
import { Nav } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import { FaUpload, FaChartBar, FaComments } from 'react-icons/fa';
import { useAnalyzer } from '../../context/AnalyzerContext';
import './Sidebar.css';

const Sidebar = () => {
  const location = useLocation();
  const { state } = useAnalyzer();
  const { sessionId, threadExtracted, analysisComplete, analysisInProgress } = state;

  // Check if path is active
  const isActive = (path) => location.pathname === path;

  // Analysis is available when it's in progress or complete
  // Remove this restriction to always enable the analysis tab
  // const analysisAvailable = analysisInProgress || analysisComplete;
  const analysisAvailable = sessionId !== null; // Enable as long as there's a session

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h3>HitCraft</h3>
        <p className="brand-subtitle">Chat Analyzer</p>
      </div>
      
      <Nav className="flex-column sidebar-menu">
        <Nav.Item>
          <Nav.Link
            as={Link}
            to="/"
            className={isActive('/') ? 'active' : ''}
          >
            <FaUpload className="me-2" />
            Upload
          </Nav.Link>
        </Nav.Item>
        
        <Nav.Item>
          <Nav.Link
            as={Link}
            to="/analysis"
            className={`${isActive('/analysis') ? 'active' : ''}`}
            // Remove the disabled attribute to always enable the tab
            // disabled={!analysisAvailable}
          >
            <FaChartBar className="me-2" />
            Analysis
            {analysisInProgress && !analysisComplete && <span className="analysis-in-progress"> (In Progress)</span>}
            {analysisComplete && <span className="analysis-complete"> (Complete)</span>}
          </Nav.Link>
        </Nav.Item>
        
        <Nav.Item>
          <Nav.Link
            as={Link}
            to="/threads"
            className={`${isActive('/threads') ? 'active' : ''} ${!threadExtracted ? 'disabled' : ''}`}
            disabled={!threadExtracted}
          >
            <FaComments className="me-2" />
            Threads
          </Nav.Link>
        </Nav.Item>
      </Nav>
      
      {sessionId && (
        <div className="sidebar-footer">
          <small className="text-muted">Session ID: {sessionId?.substring(0, 8)}...</small>
        </div>
      )}
    </div>
  );
};

export default Sidebar;
