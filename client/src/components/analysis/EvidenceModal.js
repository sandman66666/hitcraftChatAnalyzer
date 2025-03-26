import React from 'react';
import { Modal, Button } from 'react-bootstrap';
import './EvidenceModal.css';

const EvidenceModal = ({ show, onHide, title, evidence }) => {
  // Function to format message based on role (user vs assistant)
  const formatMessage = (message) => {
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
          {evidence && evidence.length > 0 ? (
            evidence.map((item, index) => (
              <div key={index} className="evidence-item">
                {formatMessage(item)}
              </div>
            ))
          ) : (
            <p className="text-muted text-center">No supporting evidence available.</p>
          )}
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
