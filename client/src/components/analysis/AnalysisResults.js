import React from 'react';
import { Row, Col, Card, Badge, Button, ProgressBar } from 'react-bootstrap';
import { FaLightbulb, FaArrowAltCircleUp, FaTasks, FaSearchPlus, FaFileAlt, FaExclamationTriangle, FaThumbsUp, FaThumbsDown, FaComments, FaChartLine } from 'react-icons/fa';
import './AnalysisResults.css';

const AnalysisResults = ({ results, onInsightClick }) => {
  // Add debugging information to console
  console.log('Rendering AnalysisResults with:', results);
  
  if (!results) {
    return (
      <div className="text-center mt-5">
        <h4>No analysis results available</h4>
        <p className="text-muted">Upload a file and run analysis to view results</p>
      </div>
    );
  }

  // Extract all needed data from results
  const insights = results.insights || results.key_insights || [];
  const categories = results.categories || [];
  const discussions = results.top_discussions || [];
  const userSatisfaction = results.user_satisfaction || {};
  const productEffectiveness = results.product_effectiveness || {};
  const unmetNeeds = results.unmet_needs || [];
  const improvementAreas = results.improvement_areas || [];
  const responseQuality = results.response_quality || {};
  const negativeChats = results.negative_chats || {};
  
  // Get overall quality score (out of 10)
  const qualityScore = responseQuality.average_score || 0;
  
  // Limit arrays to top items
  const topDiscussions = discussions.slice(0, 5);
  const topInsights = insights.slice(0, 10);
  const topImprovements = improvementAreas.slice(0, 10);
  const topNegatives = negativeChats.categories?.slice(0, 10) || [];
  
  // Helper function to generate color based on score
  const getScoreColor = (score) => {
    if (score >= 8) return 'success';
    if (score >= 6) return 'info';
    if (score >= 4) return 'warning';
    return 'danger';
  };

  return (
    <div className="analysis-results">
      {/* Quality Score Section - Always at top */}
      <Card className="mb-4 score-card">
        <Card.Header>
          <h5 className="mb-0"><FaChartLine className="me-2" />Overall Chat Quality</h5>
        </Card.Header>
        <Card.Body>
          <div className="text-center">
            <div className="score-display">
              <h1 className={`score-value text-${getScoreColor(qualityScore)}`}>
                {qualityScore}/10
              </h1>
            </div>
            
            <ProgressBar 
              now={qualityScore * 10} 
              variant={getScoreColor(qualityScore)} 
              className="mb-3" 
              style={{height: '10px'}}
            />
            
            {productEffectiveness && productEffectiveness.assessment && (
              <p className="assessment-text">{productEffectiveness.assessment}</p>
            )}
          </div>
        </Card.Body>
      </Card>
      
      {/* Top 5 Discussion Topics - Key Metrics Row */}
      {topDiscussions && topDiscussions.length > 0 && (
        <Card className="mb-4">
          <Card.Header className="bg-primary text-white">
            <h5 className="mb-0"><FaComments className="me-2" />Top 5 User Discussion Topics</h5>
          </Card.Header>
          <Card.Body>
            <div className="top-discussions">
              {topDiscussions.map((item, index) => (
                <div key={index} className="discussion-item">
                  <div className="d-flex justify-content-between align-items-center">
                    <h5 className="mb-1">
                      {index + 1}. {item.topic || 'Topic'}
                    </h5>
                    {item.count && <Badge bg="primary" pill>{item.count}</Badge>}
                  </div>
                  
                  {item.instances && item.instances.length > 0 && (
                    <Button 
                      variant="outline-primary" 
                      size="sm"
                      className="mt-1"
                      onClick={() => onInsightClick({
                        title: item.topic,
                        supporting_evidence: item.instances.map(i => i.context)
                      }, 'discussions')}
                    >
                      <FaSearchPlus className="me-1" />
                      View {item.instances.length} examples
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </Card.Body>
        </Card>
      )}
      
      {/* 3-Column Layout for Insights, Improvements and Negatives */}
      <Row className="mb-4">
        {/* Top 10 Positive Insights */}
        <Col lg={4} md={12} className="mb-4 mb-lg-0">
          <Card className="h-100 positive-card">
            <Card.Header className="bg-success text-white">
              <h5 className="mb-0"><FaThumbsUp className="me-2" />Top 10 Positive Insights</h5>
            </Card.Header>
            <Card.Body>
              {topInsights && topInsights.length > 0 ? (
                <ol className="insights-list">
                  {topInsights.map((insight, index) => (
                    <li key={insight.key || index} className="insight-item">
                      <div className="insight-content">
                        <h6>{insight.insight || insight.title}</h6>
                        {(insight.evidence_threads && insight.evidence_threads.length > 0) || 
                         (insight.supporting_evidence && insight.supporting_evidence.length > 0) ? (
                          <Button 
                            variant="outline-success" 
                            size="sm"
                            className="mt-1"
                            onClick={() => onInsightClick(insight, 'insights')}
                          >
                            <FaFileAlt className="me-1" />
                            View evidence
                          </Button>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-muted text-center">No key insights identified</p>
              )}
            </Card.Body>
          </Card>
        </Col>
        
        {/* Top 10 Improvement Areas */}
        <Col lg={4} md={12} className="mb-4 mb-lg-0">
          <Card className="h-100 improvement-card">
            <Card.Header className="bg-info text-white">
              <h5 className="mb-0"><FaArrowAltCircleUp className="me-2" />Top 10 Improvement Areas</h5>
            </Card.Header>
            <Card.Body>
              {topImprovements && topImprovements.length > 0 ? (
                <ol className="improvement-list">
                  {topImprovements.map((area, index) => (
                    <li key={index} className="improvement-item">
                      <div className="improvement-content">
                        <h6>{typeof area === 'string' ? area : area.area || 'Unknown Area'}</h6>
                        {area.supporting_evidence && area.supporting_evidence.length > 0 && (
                          <Button 
                            variant="outline-info" 
                            size="sm"
                            className="mt-1"
                            onClick={() => onInsightClick({
                              title: typeof area === 'string' ? area : area.area,
                              supporting_evidence: area.supporting_evidence
                            }, 'improvement_areas')}
                          >
                            <FaFileAlt className="me-1" />
                            View evidence
                          </Button>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-muted text-center">No improvement areas identified</p>
              )}
            </Card.Body>
          </Card>
        </Col>
        
        {/* Top 10 Negative Chat Categories */}
        <Col lg={4} md={12}>
          <Card className="h-100 negative-card">
            <Card.Header className="bg-warning text-dark">
              <h5 className="mb-0"><FaExclamationTriangle className="me-2" />Top 10 Negative Chats</h5>
            </Card.Header>
            <Card.Body>
              {topNegatives && topNegatives.length > 0 ? (
                <ol className="negative-list">
                  {topNegatives.map((cat, index) => (
                    <li key={index} className="negative-item">
                      <div className="negative-content">
                        <h6>{cat.category}</h6>
                        {cat.count && <Badge bg="warning" text="dark">{cat.count}</Badge>}
                        {cat.examples && cat.examples.length > 0 && (
                          <Button 
                            variant="outline-warning" 
                            size="sm"
                            className="mt-1"
                            onClick={() => onInsightClick({
                              title: cat.category,
                              supporting_evidence: cat.examples.map(e => e.context)
                            }, 'negative_chats')}
                          >
                            <FaFileAlt className="me-1" />
                            View examples
                          </Button>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-muted text-center">No negative chat categories identified</p>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {/* Good and Bad Examples Row */}
      {(responseQuality.good_examples?.length > 0 || responseQuality.poor_examples?.length > 0) && (
        <Row className="mb-4">
          {/* Good Examples */}
          {responseQuality.good_examples && responseQuality.good_examples.length > 0 && (
            <Col md={6}>
              <Card className="h-100">
                <Card.Header className="bg-success text-white">
                  <h5 className="mb-0"><FaThumbsUp className="me-2" />Best Practices</h5>
                </Card.Header>
                <Card.Body>
                  <ul className="example-list">
                    {responseQuality.good_examples.map((example, index) => (
                      <li key={index} className="example-item">
                        <div className="example-content">
                          <p>{example}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </Card.Body>
              </Card>
            </Col>
          )}
          
          {/* Poor Examples */}
          {responseQuality.poor_examples && responseQuality.poor_examples.length > 0 && (
            <Col md={6}>
              <Card className="h-100">
                <Card.Header className="bg-danger text-white">
                  <h5 className="mb-0"><FaThumbsDown className="me-2" />Opportunities for Improvement</h5>
                </Card.Header>
                <Card.Body>
                  <ul className="example-list">
                    {responseQuality.poor_examples.map((example, index) => (
                      <li key={index} className="example-item">
                        <div className="example-content">
                          <p>{example}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </Card.Body>
              </Card>
            </Col>
          )}
        </Row>
      )}
      
      {/* Additional Categories Row */}
      {categories && categories.length > 0 && (
        <Card className="mb-4">
          <Card.Header>
            <h5 className="mb-0">All Discussion Categories</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              {categories.map((cat, index) => (
                <Col key={index} md={3} sm={6} className="mb-3">
                  <div className="category-item p-2 border rounded">
                    <h6>{typeof cat === 'string' ? cat : cat.category || 'Unknown'}</h6>
                    {cat.count && <small className="text-muted">{cat.count} instances</small>}
                  </div>
                </Col>
              ))}
            </Row>
          </Card.Body>
        </Card>
      )}
      
      {/* Unmet Needs - at bottom since you mentioned other sections are more important */}
      {unmetNeeds && unmetNeeds.length > 0 && (
        <Card className="mb-4">
          <Card.Header>
            <h5 className="mb-0"><FaTasks className="me-2" />Unmet Needs</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              {unmetNeeds.map((need, index) => (
                <Col key={index} md={4} className="mb-3">
                  <div className="unmet-need-item p-3 border rounded">
                    <h6>{typeof need === 'string' ? need : need.need}</h6>
                    {need.supporting_evidence && need.supporting_evidence.length > 0 && (
                      <Button 
                        variant="outline-secondary" 
                        size="sm"
                        onClick={() => onInsightClick({
                          title: typeof need === 'string' ? need : need.need,
                          supporting_evidence: need.supporting_evidence
                        }, 'unmet_needs')}
                      >
                        <FaSearchPlus className="me-1" />
                        View evidence
                      </Button>
                    )}
                  </div>
                </Col>
              ))}
            </Row>
          </Card.Body>
        </Card>
      )}
    </div>
  );
};

export default AnalysisResults;
