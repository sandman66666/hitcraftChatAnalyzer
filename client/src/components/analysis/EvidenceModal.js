import React from 'react';
import { Modal, Button, Card, Badge, Accordion } from 'react-bootstrap';
import './EvidenceModal.css';

const EvidenceModal = ({ show, onHide, title, evidence }) => {
  // Function to format message based on role (user vs assistant)
  const formatMessage = (message) => {
    // Handle different message formats
    if (typeof message === 'object' && message !== null) {
      const role = message.role?.toLowerCase() || 'system';
      let content = '';
      
      // Handle content that could be string or array of content blocks
      if (typeof message.content === 'string') {
        content = message.content;
      } else if (Array.isArray(message.content)) {
        // Convert array of content blocks to text
        content = message.content.map(block => {
          if (typeof block === 'string') return block;
          if (typeof block === 'object' && block.text) return block.text;
          return JSON.stringify(block);
        }).join("\n");
      } else if (message.content) {
        // Fallback for other formats
        content = JSON.stringify(message.content);
      }
      
      return (
        <div className={`chat-message ${role}-message`}>
          <div className="message-role">{role.toUpperCase()}</div>
          <div className="message-content">{content}</div>
        </div>
      );
    }
    
    // Handle plain strings - try to detect if it's a user or assistant message
    if (typeof message === 'string') {
      // For Claude API evidence, which might just be conversation snippets
      if (message.includes('User:') && message.includes('Assistant:')) {
        return (
          <div className="chat-message system-message">
            <div className="message-content conversation-snippet">
              {message.split('\n').map((line, i) => (
                <div key={i} className={
                  line.startsWith('User:') ? 'snippet-user' : 
                  line.startsWith('Assistant:') ? 'snippet-assistant' : 
                  'snippet-other'
                }>
                  {line}
                </div>
              ))}
            </div>
          </div>
        );
      }
      
      // Standard message detection
      const isUser = message.toLowerCase().includes('user:');
      const isAssistant = message.toLowerCase().includes('assistant:');
      
      if (isUser) {
        return (
          <div className="chat-message user-message">
            <div className="message-content">{message}</div>
          </div>
        );
      } else if (isAssistant) {
        return (
          <div className="chat-message assistant-message">
            <div className="message-content">{message}</div>
          </div>
        );
      } else {
        return (
          <div className="chat-message system-message">
            <div className="message-content">{message}</div>
          </div>
        );
      }
    }
    
    // Fallback for unexpected types
    return (
      <div className="chat-message system-message">
        <div className="message-content">{JSON.stringify(message)}</div>
      </div>
    );
  };

  // Handle evidence that might be in different formats
  const renderEvidence = () => {
    if (!evidence || evidence.length === 0) {
      return <p className="text-muted text-center">No supporting evidence available.</p>;
    }
    
    // Check if evidence is an array of thread objects with messages
    if (evidence[0] && evidence[0].messages) {
      return (
        <Accordion defaultActiveKey="0">
          {evidence.map((thread, threadIndex) => (
            <Accordion.Item key={threadIndex} eventKey={threadIndex.toString()}>
              <Accordion.Header>
                <strong>Thread {thread.thread_id || `#${threadIndex+1}`}</strong>
                {thread.metadata?.message_count && (
                  <Badge bg="info" className="ms-2">
                    {thread.metadata.message_count} messages
                  </Badge>
                )}
              </Accordion.Header>
              <Accordion.Body>
                <div className="thread-messages">
                  {thread.messages && thread.messages.map((message, msgIndex) => (
                    <div key={msgIndex} className="message-container">
                      {formatMessage(message)}
                    </div>
                  ))}
                </div>
              </Accordion.Body>
            </Accordion.Item>
          ))}
        </Accordion>
      );
    }
    
    // Claude API evidence might be an array of conversation snippets
    if (typeof evidence[0] === 'string') {
      return (
        <div className="evidence-snippets">
          {evidence.map((snippet, index) => (
            <Card key={index} className="mb-3 evidence-snippet-card">
              <Card.Body>
                {formatMessage(snippet)}
              </Card.Body>
            </Card>
          ))}
        </div>
      );
    }
    
    // Fallback - just stringify the evidence
    return (
      <div className="evidence-raw">
        <pre>{JSON.stringify(evidence, null, 2)}</pre>
      </div>
    );
  };

  return (
    <Modal
      show={show}
      onHide={onHide}
      size="lg"
      centered
      className="evidence-modal"
    >
      <Modal.Header closeButton>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="evidence-container">
          {renderEvidence()}
        </div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Close
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default EvidenceModal;
