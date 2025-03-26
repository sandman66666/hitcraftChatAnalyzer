import React, { useState } from 'react';
import { Row, Col, Card, Badge } from 'react-bootstrap';
import { FaLightbulb, FaArrowAltCircleUp, FaTasks } from 'react-icons/fa';
import EvidenceModal from './EvidenceModal';
import './AnalysisResults.css';

const AnalysisResults = ({ results }) => {
  const [showModal, setShowModal] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalEvidence, setModalEvidence] = useState([]);
  
  // Add debugging information to console
  console.log('Rendering AnalysisResults with:', results);
  
  // Handle click on an item with supporting evidence
  const handleEvidenceClick = (title, evidence) => {
    setModalTitle(title);
    setModalEvidence(evidence || []);
    setShowModal(true);
  };
  
  if (!results) {
    return (
      <div className="text-center mt-5">
        <h4>No analysis results available</h4>
        <p className="text-muted">Upload a file and run analysis to view results</p>
      </div>
    );
  }
  
  // Extract key data with fallbacks for different data structures
  const insights = results.insights || 
                  results.key_insights || 
                  results.top_insights || 
                  [];
  
  const improvement_areas = results.improvement_areas || 
                           results.areas_for_improvement || 
                           [];
  
  const unmet_needs = results.unmet_needs || 
                     results.user_needs || 
                     [];
                     
  // Support for additional data formats
  const categories = results.top_categories || results.categories || [];
  const discussions = results.top_discussions || results.discussions || [];
  
  // Format data if it's in array format instead of object format
  const formatInsights = () => {
    if (!insights) return [];
    
    // If insights is already an array of objects with the right structure
    if (Array.isArray(insights) && insights.length > 0 && typeof insights[0] === 'object' && 'insight' in insights[0]) {
      return insights;
    }
    
    // If insights is an array of strings, convert to expected format
    if (Array.isArray(insights) && insights.length > 0 && typeof insights[0] === 'string') {
      return insights.map(insight => ({ 
        insight, 
        supporting_evidence: [] 
      }));
    }
    
    return [];
  };
  
  const formattedInsights = formatInsights();
  
  return (
    <div className="analysis-results">
      {/* Categories Section (if available) */}
      {categories && categories.length > 0 && (
        <Card className="mb-4">
          <Card.Header>
            <h5 className="mb-0">Top Categories</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              {categories.map((cat, index) => (
                <Col key={index} md={4} sm={6} className="mb-3">
                  <div className="category-item p-2 border rounded">
                    <h6>{cat.category || cat}</h6>
                    {cat.count && <small className="text-muted">{cat.count} instances</small>}
                  </div>
                </Col>
              ))}
            </Row>
          </Card.Body>
        </Card>
      )}
      
      {/* Discussions Section (if available) */}
      {discussions && discussions.length > 0 && (
        <Card className="mb-4">
          <Card.Header>
            <h5 className="mb-0">Top Discussion Topics</h5>
          </Card.Header>
          <Card.Body>
            <ul className="list-group">
              {discussions.map((item, index) => (
                <li key={index} className="list-group-item d-flex justify-content-between align-items-center">
                  <span>{item.topic || item}</span>
                  {item.count && <Badge bg="primary" pill>{item.count}</Badge>}
                </li>
              ))}
            </ul>
          </Card.Body>
        </Card>
      )}
      
      <Row>
        <Col lg={4} md={6} className="mb-4">
          <Card className="h-100 insight-card">
            <Card.Header>
              <h5 className="mb-0">
                <FaLightbulb className="me-2" />
                Key Insights
              </h5>
            </Card.Header>
            <Card.Body>
              <ul className="analysis-list">
                {formattedInsights && formattedInsights.length > 0 ? (
                  formattedInsights.map((item, index) => (
                    <li 
                      key={index} 
                      className={item.supporting_evidence?.length > 0 ? 'has-evidence' : ''}
                      onClick={() => 
                        item.supporting_evidence?.length > 0 && 
                        handleEvidenceClick(`Evidence for: ${item.insight}`, item.supporting_evidence)
                      }
                    >
                      <div className="list-item-content">
                        <span>{item.insight}</span>
                        {item.supporting_evidence?.length > 0 && (
                          <Badge bg="info" pill className="evidence-badge">
                            {item.supporting_evidence.length}
                          </Badge>
                        )}
                      </div>
                    </li>
                  ))
                ) : (
                  <li className="text-muted">No insights found</li>
                )}
              </ul>
            </Card.Body>
          </Card>
        </Col>
        
        <Col lg={4} md={6} className="mb-4">
          <Card className="h-100 improvement-card">
            <Card.Header>
              <h5 className="mb-0">
                <FaArrowAltCircleUp className="me-2" />
                Improvement Areas
              </h5>
            </Card.Header>
            <Card.Body>
              <ul className="analysis-list">
                {improvement_areas && improvement_areas.length > 0 ? (
                  improvement_areas.map((item, index) => (
                    <li 
                      key={index} 
                      className={item.supporting_evidence?.length > 0 ? 'has-evidence' : ''}
                      onClick={() => 
                        item.supporting_evidence?.length > 0 && 
                        handleEvidenceClick(`Evidence for: ${item.area}`, item.supporting_evidence)
                      }
                    >
                      <div className="list-item-content">
                        <span>{item.area}</span>
                        {item.supporting_evidence?.length > 0 && (
                          <Badge bg="warning" pill className="evidence-badge">
                            {item.supporting_evidence.length}
                          </Badge>
                        )}
                      </div>
                    </li>
                  ))
                ) : (
                  <li className="text-muted">No improvement areas found</li>
                )}
              </ul>
            </Card.Body>
          </Card>
        </Col>
        
        <Col lg={4} md={6} className="mb-4">
          <Card className="h-100 needs-card">
            <Card.Header>
              <h5 className="mb-0">
                <FaTasks className="me-2" />
                Unmet Needs
              </h5>
            </Card.Header>
            <Card.Body>
              <ul className="analysis-list">
                {unmet_needs && unmet_needs.length > 0 ? (
                  unmet_needs.map((item, index) => (
                    <li 
                      key={index} 
                      className={item.supporting_evidence?.length > 0 ? 'has-evidence' : ''}
                      onClick={() => 
                        item.supporting_evidence?.length > 0 && 
                        handleEvidenceClick(`Evidence for: ${item.need}`, item.supporting_evidence)
                      }
                    >
                      <div className="list-item-content">
                        <span>{item.need}</span>
                        {item.supporting_evidence?.length > 0 && (
                          <Badge bg="danger" pill className="evidence-badge">
                            {item.supporting_evidence.length}
                          </Badge>
                        )}
                      </div>
                    </li>
                  ))
                ) : (
                  <li className="text-muted">No unmet needs found</li>
                )}
              </ul>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {/* Evidence Modal */}
      <EvidenceModal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={modalTitle}
        evidence={modalEvidence}
      />
    </div>
  );
};

export default AnalysisResults;
