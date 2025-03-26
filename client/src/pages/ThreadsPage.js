import React, { useEffect, useState } from 'react';
import { Row, Col, Card, ListGroup, Badge, Button, Form, Pagination } from 'react-bootstrap';
import { useAnalyzer } from '../context/AnalyzerContext';
import api from '../services/api';
import './Pages.css';
import { FaSearch, FaSync, FaChartBar } from 'react-icons/fa';

const ThreadsPage = () => {
  const { state, actions } = useAnalyzer();
  const { sessionId, threadsAnalyzed } = state;
  
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [threads, setThreads] = useState([]);
  const [currentThread, setCurrentThread] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 10,
    total: 0,
    totalPages: 0
  });
  const [threadCount, setThreadCount] = useState(0);
  const [threadsToAnalyze, setThreadsToAnalyze] = useState(10);
  const [analysisStats, setAnalysisStats] = useState({
    totalThreads: 0,
    analyzedThreads: 0,
    remainingThreads: 0
  });
  
  // Load thread list when component mounts or session changes
  useEffect(() => {
    loadThreads(pagination.page);
    fetchAnalysisStats();
  }, []);
  
  // Load threads with pagination
  const loadThreads = async (page = 1) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.listThreads(sessionId || '', page, pagination.perPage);
      
      if (response.data) {
        setThreads(response.data.threads || []);
        setPagination({
          page: response.data.page || 1,
          perPage: response.data.per_page || 10,
          total: response.data.total || 0,
          totalPages: response.data.total_pages || 1
        });
        setThreadCount(response.data.total || 0);
        
        // Update analysis stats
        setAnalysisStats(prev => ({
          ...prev,
          totalThreads: response.data.total || 0,
          remainingThreads: (response.data.total || 0) - prev.analyzedThreads
        }));
      }
    } catch (err) {
      console.error('Error loading threads:', err);
      setError('Failed to load conversation threads');
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Error loading threads: ${err.message}`,
        level: 'error'
      });
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch analysis stats
  const fetchAnalysisStats = async () => {
    try {
      const response = await api.getAnalysisStatus(sessionId || '');
      
      if (response.data) {
        const analyzed = response.data.analyzed_threads || 0;
        setAnalysisStats({
          totalThreads: threadCount,
          analyzedThreads: analyzed,
          remainingThreads: threadCount - analyzed
        });
        
        // Update global state
        if (analyzed > 0) {
          actions.updateAnalysisProgress(analyzed);
        }
      }
    } catch (err) {
      console.error('Error fetching analysis stats:', err);
    }
  };
  
  // Handle pagination
  const handlePageChange = (page) => {
    loadThreads(page);
  };
  
  // Load specific thread
  const loadThread = async (threadId) => {
    if (!threadId) return;
    
    try {
      setLoading(true);
      
      const response = await api.getThread(sessionId, threadId);
      console.log('Thread response for ID:', threadId, response.data);
      
      if (response.data) {
        let thread = {
          id: threadId,
          title: `Thread #${threadId}`,
          messages: []
        };
        
        // Handle direct messages array
        if (Array.isArray(response.data.messages)) {
          thread.messages = response.data.messages;
          thread.message_count = response.data.messages.length;
          console.log('Using direct messages array:', thread.messages.length);
        } 
        // Handle thread property
        else if (response.data.thread && response.data.thread.messages) {
          thread = response.data.thread;
          console.log('Using thread.messages object:', thread.messages.length);
        } 
        // Handle content array
        else if (Array.isArray(response.data.content)) {
          const messages = response.data.content.map(message => {
            if (typeof message === 'string') {
              // Parse role from message text
              let role = 'system';
              let content = message;
              
              if (message.toUpperCase().includes('USER:')) {
                role = 'user';
                content = message.substring(message.indexOf(':') + 1).trim();
              } else if (message.toUpperCase().includes('ASSISTANT:')) {
                role = 'assistant';
                content = message.substring(message.indexOf(':') + 1).trim();
              }
              
              return { role, content };
            } else if (typeof message === 'object' && message !== null) {
              // Already in proper format
              return {
                role: message.role || 'system',
                content: message.content || ''
              };
            }
            
            return { role: 'system', content: JSON.stringify(message) };
          });
          
          thread.messages = messages;
          thread.message_count = messages.length;
          console.log('Using content array:', thread.messages.length);
        }
        // Fallback to content as a property
        else if (response.data.content && typeof response.data.content === 'string') {
          try {
            // Try to parse as JSON
            const parsedContent = JSON.parse(response.data.content);
            if (Array.isArray(parsedContent)) {
              thread.messages = parsedContent.map(item => {
                if (typeof item === 'object' && item !== null && item.role) {
                  return item;
                }
                return { role: 'system', content: JSON.stringify(item) };
              });
            } else {
              thread.messages = [{ role: 'system', content: response.data.content }];
            }
          } catch (e) {
            // If parsing fails, treat as plain text
            thread.messages = [{ role: 'system', content: response.data.content }];
          }
          thread.message_count = thread.messages.length;
          console.log('Using parsed content string:', thread.messages.length);
        } else {
          // Last resort - use the entire response data as a message
          console.log('No recognized message format found, creating a fallback message');
          thread.messages = [{ role: 'system', content: JSON.stringify(response.data) }];
          thread.message_count = 1;
        }
        
        // Update metadata if available
        if (response.data.id) thread.id = response.data.id;
        if (response.data.title) thread.title = response.data.title;
        if (response.data.message_count) thread.message_count = response.data.message_count;
        
        console.log('Final thread object:', thread);
        setCurrentThread(thread);
      }
    } catch (err) {
      console.error('Error loading thread:', err);
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Error loading thread: ${err.message}`,
        level: 'error'
      });
    } finally {
      setLoading(false);
    }
  };
  
  // Start thread analysis
  const startAnalysis = async () => {
    if (!sessionId) return;
    
    try {
      setAnalyzing(true);
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Starting analysis of ${threadsToAnalyze} threads...`,
        level: 'info'
      });
      
      const response = await api.analyzeThreads(sessionId, threadsToAnalyze);
      
      if (response.data && response.data.success) {
        actions.addLog({
          timestamp: new Date().toISOString(),
          message: 'Analysis started successfully',
          level: 'info'
        });
        
        // Redirect to analysis page to see progress
        actions.navigate('/analysis');
      }
    } catch (err) {
      console.error('Error starting analysis:', err);
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Error starting analysis: ${err.message}`,
        level: 'error'
      });
    } finally {
      setAnalyzing(false);
    }
  };
  
  // Format message based on role (user, assistant, system)
  const formatMessage = (message) => {
    // Determine role - default to 'system' if not specified
    let role = 'system';
    let content = '';
    
    if (message && typeof message === 'object') {
      // Handle object format with role property
      if (message.role) {
        role = message.role.toLowerCase();
      }
      
      // Handle different content formats
      if (message.content) {
        // Ensure content is a string
        content = typeof message.content === 'object' 
          ? JSON.stringify(message.content) 
          : String(message.content);
      } else if (message.text) {
        // Ensure text is a string
        content = typeof message.text === 'object' 
          ? JSON.stringify(message.text) 
          : String(message.text);
        
        // If there's a type property, it might also indicate the role
        if (message.type) {
          if (message.type === 'human' || message.type === 'user') {
            role = 'user';
          } else if (message.type === 'ai' || message.type === 'assistant') {
            role = 'assistant';
          }
        }
      } else {
        // Fallback to stringifying the object if no content or text field
        content = JSON.stringify(message);
      }
      
      // Return formatted message bubble
      return (
        <div className={`message-bubble ${role}-message`}>
          <div className="message-header">
            <span className="message-role">{role}</span>
          </div>
          <div className="message-content">{content}</div>
        </div>
      );
    } else if (typeof message === 'string') {
      // Handle plain string message (fallback)
      return (
        <div className="message-bubble system-message">
          <div className="message-content">{message}</div>
        </div>
      );
    }
    
    // Last resort fallback
    return (
      <div className="message-bubble system-message">
        <div className="message-content">Unknown message format</div>
      </div>
    );
  };
  
  // Generate pagination items
  const paginationItems = () => {
    const items = [];
    
    // Previous button
    items.push(
      <Pagination.Prev 
        key="prev"
        disabled={pagination.page === 1 || loading}
        onClick={() => handlePageChange(pagination.page - 1)}
      />
    );
    
    // First page
    items.push(
      <Pagination.Item
        key={1}
        active={pagination.page === 1}
        onClick={() => handlePageChange(1)}
      >
        1
      </Pagination.Item>
    );
    
    // Ellipsis if needed
    if (pagination.page > 3) {
      items.push(<Pagination.Ellipsis key="ellipsis1" disabled />);
    }
    
    // Pages around current page
    for (let i = Math.max(2, pagination.page - 1); i <= Math.min(pagination.totalPages - 1, pagination.page + 1); i++) {
      items.push(
        <Pagination.Item
          key={i}
          active={pagination.page === i}
          onClick={() => handlePageChange(i)}
        >
          {i}
        </Pagination.Item>
      );
    }
    
    // Ellipsis if needed
    if (pagination.page < pagination.totalPages - 2) {
      items.push(<Pagination.Ellipsis key="ellipsis2" disabled />);
    }
    
    // Last page if different from first
    if (pagination.totalPages > 1) {
      items.push(
        <Pagination.Item
          key={pagination.totalPages}
          active={pagination.page === pagination.totalPages}
          onClick={() => handlePageChange(pagination.totalPages)}
        >
          {pagination.totalPages}
        </Pagination.Item>
      );
    }
    
    // Next button
    items.push(
      <Pagination.Next
        key="next"
        disabled={pagination.page === pagination.totalPages || loading}
        onClick={() => handlePageChange(pagination.page + 1)}
      />
    );
    
    return items;
  };
  
  return (
    <div className="threads-page">
      <Row className="mb-4">
        <Col>
          <h2 className="page-title">Conversation Threads</h2>
          <p className="page-description">
            Browse through imported conversation threads.
          </p>
        </Col>
      </Row>
      
      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}
      
      <Row className="mb-4">
        <Col md={6}>
          <Card className="thread-stats-card">
            <Card.Header>
              <h5 className="mb-0">Thread Statistics</h5>
            </Card.Header>
            <Card.Body>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-label">Total Threads</div>
                  <div className="stat-value">{analysisStats.totalThreads}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">Analyzed Threads</div>
                  <div className="stat-value">{analysisStats.analyzedThreads}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">Remaining Threads</div>
                  <div className="stat-value">{analysisStats.remainingThreads}</div>
                </div>
              </div>
              
              {analysisStats.remainingThreads > 0 && (
                <div className="mt-3">
                  <Form className="d-flex align-items-center">
                    <Form.Group className="me-3 flex-grow-1">
                      <Form.Label>Analyze additional threads:</Form.Label>
                      <Form.Control 
                        type="number" 
                        min="1" 
                        max={analysisStats.remainingThreads} 
                        value={threadsToAnalyze}
                        onChange={(e) => setThreadsToAnalyze(parseInt(e.target.value, 10) || 0)}
                      />
                    </Form.Group>
                    <Button 
                      variant="primary" 
                      className="mt-auto"
                      onClick={startAnalysis}
                      disabled={analyzing || !sessionId || threadsToAnalyze <= 0 || threadsToAnalyze > analysisStats.remainingThreads}
                    >
                      {analyzing ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                          Analyzing...
                        </>
                      ) : (
                        <>
                          <FaChartBar className="me-2" />
                          Analyze
                        </>
                      )}
                    </Button>
                  </Form>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card className="thread-controls-card">
            <Card.Header>
              <h5 className="mb-0">Thread Navigation</h5>
            </Card.Header>
            <Card.Body>
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  Showing {threads.length > 0 ? (pagination.page - 1) * pagination.perPage + 1 : 0} to {Math.min(pagination.page * pagination.perPage, pagination.total)} of {pagination.total} threads
                </div>
                <div>
                  <Button 
                    variant="outline-secondary" 
                    className="ms-2"
                    onClick={() => loadThreads(pagination.page)}
                    disabled={loading}
                  >
                    <FaSync className={loading ? 'fa-spin' : ''} />
                  </Button>
                </div>
              </div>
              
              <div className="mt-3">
                <Pagination className="justify-content-center">
                  {paginationItems()}
                </Pagination>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      <Row>
        <Col md={4}>
          <Card className="thread-list-card">
            <Card.Header>
              <h5 className="mb-0">Threads</h5>
            </Card.Header>
            <ListGroup variant="flush">
              {loading && threads.length === 0 ? (
                <ListGroup.Item className="text-center py-3">
                  <div className="spinner-border spinner-border-sm text-primary me-2" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  Loading threads...
                </ListGroup.Item>
              ) : threads.length === 0 ? (
                <ListGroup.Item className="text-center py-3 text-muted">
                  No threads available
                </ListGroup.Item>
              ) : (
                threads.map((thread) => (
                  <ListGroup.Item 
                    key={thread.id}
                    action
                    active={currentThread && currentThread.id === thread.id}
                    onClick={() => loadThread(thread.id)}
                    className="thread-item"
                  >
                    <div className="thread-item-title">
                      {thread.title || `Thread #${thread.id}`}
                    </div>
                    {thread.message_count && (
                      <Badge bg="info" pill>
                        {thread.message_count} messages
                      </Badge>
                    )}
                  </ListGroup.Item>
                ))
              )}
            </ListGroup>
          </Card>
        </Col>
        
        <Col md={8}>
          <Card className="thread-details-card">
            <Card.Header>
              <h5 className="mb-0">
                {currentThread ? (
                  currentThread.title || `Thread #${currentThread.id}`
                ) : (
                  'Select a thread to view'
                )}
              </h5>
            </Card.Header>
            <Card.Body>
              {!currentThread ? (
                <div className="text-center text-muted py-5">
                  <p>Select a thread from the list to view its messages</p>
                </div>
              ) : loading ? (
                <div className="text-center py-5">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                </div>
              ) : (
                <div className="thread-messages">
                  {currentThread.messages && currentThread.messages.length > 0 ? (
                    currentThread.messages.map((message, index) => {
                      return (
                        <div key={index} className={`thread-message-container ${message.role === 'user' ? 'user-container' : message.role === 'assistant' ? 'assistant-container' : 'system-container'}`}>
                          {formatMessage(message)}
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-center text-muted py-5">
                      <p>No messages in this thread</p>
                    </div>
                  )}
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ThreadsPage;
