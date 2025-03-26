// results-display.js - Handles the display of analysis results

function displayResults(results) {
    console.log('Displaying results:', results);
    
    // Clear previous results
    clearPreviousResults();
    
    // Map Claude API response fields to our UI fields if needed
    const mappedResults = mapResultFields(results);
    
    // Update the result counts in the dashboard cards
    updateResultCounts(mappedResults);
    
    // Display each result section if it has content
    displayKeyInsights(mappedResults.key_insights || []);
    displayImprovementAreas(mappedResults.improvement_areas || []);
    displayUnmetNeeds(mappedResults.unmet_needs || []);
    displayCategories(mappedResults.categories || []);
    displayTopDiscussions(mappedResults.top_discussions || []);
    displayNegativeChats(mappedResults.negative_chats || []);
    
    // Update quality and satisfaction scores
    updateScores(mappedResults);
    
    // Show the analysis screen after results are ready
    const analysisResults = document.getElementById('analysisResults');
    if (analysisResults) {
        analysisResults.classList.remove('d-none');
    }
}

/**
 * Map Claude API response fields to our UI fields
 * This handles any mismatches between the API response and what our UI expects
 */
function mapResultFields(results) {
    const mapped = {...results}; // Create a copy to avoid modifying the original
    
    // Handle key_insights vs insights field name mismatch
    if (!mapped.key_insights && mapped.insights) {
        mapped.key_insights = mapped.insights;
    } else if (!mapped.key_insights && results.key_insights) {
        mapped.key_insights = results.key_insights;
    }
    
    // Handle response_quality mapping
    if (mapped.response_quality) {
        if (typeof mapped.response_quality === 'object' && mapped.response_quality.average_score) {
            mapped.quality_score = mapped.response_quality.average_score;
        } else if (typeof mapped.response_quality === 'number') {
            mapped.quality_score = mapped.response_quality;
        }
    }
    
    // Handle user_satisfaction mapping
    if (mapped.user_satisfaction) {
        if (typeof mapped.user_satisfaction === 'object' && mapped.user_satisfaction.score) {
            mapped.satisfaction_score = mapped.user_satisfaction.score;
        } else if (typeof mapped.user_satisfaction === 'number') {
            mapped.satisfaction_score = mapped.user_satisfaction;
        }
    }
    
    return mapped;
}

/**
 * Clear previous results from all sections
 */
function clearPreviousResults() {
    const insightsList = document.getElementById('insightsList');
    const improvementsList = document.getElementById('improvementsList');
    const unmetNeedsList = document.getElementById('unmetNeedsList');
    const negativeChatsList = document.getElementById('negativeChatsList');
    const categoriesList = document.getElementById('categories-list');
    
    if (insightsList) insightsList.innerHTML = '';
    if (improvementsList) improvementsList.innerHTML = '';
    if (unmetNeedsList) unmetNeedsList.innerHTML = '';
    if (negativeChatsList) negativeChatsList.innerHTML = '';
    if (categoriesList) categoriesList.innerHTML = '';
}

/**
 * Update the quality and satisfaction scores
 */
function updateScores(results) {
    const qualityScore = document.getElementById('quality-score');
    const qualityScoreBubble = document.getElementById('quality-score-bubble');
    const satisfactionScore = document.getElementById('satisfaction-score');
    const satisfactionScoreBubble = document.getElementById('satisfaction-score-bubble');
    
    // Update quality score
    if (qualityScore && results.quality_score !== undefined) {
        const score = Math.round(results.quality_score);
        qualityScore.textContent = `${score}/10`;
        if (qualityScoreBubble) qualityScoreBubble.textContent = score;
    }
    
    // Update satisfaction score
    if (satisfactionScore && results.satisfaction_score !== undefined) {
        const score = Math.round(results.satisfaction_score);
        satisfactionScore.textContent = `${score}/10`;
        if (satisfactionScoreBubble) satisfactionScoreBubble.textContent = score;
    } else if (satisfactionScore && results.user_satisfaction && 
              typeof results.user_satisfaction === 'object' && 
              results.user_satisfaction.overall_assessment) {
        // Use text assessment if no numeric score is available
        satisfactionScore.textContent = results.user_satisfaction.overall_assessment.substring(0, 15) + '...';
    }
}

/**
 * Update the count badges on dashboard cards
 * @param {Object} results - Analysis results
 */
function updateResultCounts(results) {
    const insightsCount = document.getElementById('insights-count');
    const improvementsCount = document.getElementById('improvements-count');
    const unmetNeedsCount = document.getElementById('unmet-needs-count');
    const negativeChatsCount = document.getElementById('negative-chats-count');
    
    if (insightsCount) insightsCount.textContent = (results.key_insights || []).length;
    if (improvementsCount) improvementsCount.textContent = (results.improvement_areas || []).length;
    if (unmetNeedsCount) unmetNeedsCount.textContent = (results.unmet_needs || []).length;
    
    // For negative chats, count the total across all categories
    let negativeChatCount = 0;
    if (results.negative_chats && results.negative_chats.categories) {
        results.negative_chats.categories.forEach(category => {
            negativeChatCount += category.count || 0;
        });
    }
    if (negativeChatsCount) negativeChatsCount.textContent = negativeChatCount;
}

/**
 * Display categories in the UI
 */
function displayCategories(categories) {
    const categoriesList = document.getElementById('categories-list');
    if (!categoriesList) return;
    
    if (!categories || categories.length === 0) {
        return;
    }
    
    categories.forEach(category => {
        let categoryText = category;
        if (typeof category === 'object' && category.category) {
            categoryText = category.category;
        }
        
        const badge = document.createElement('span');
        badge.className = 'category-badge';
        badge.textContent = categoryText;
        categoriesList.appendChild(badge);
    });
}

/**
 * Display top discussions in the UI
 */
function displayTopDiscussions(discussions) {
    // This could be implemented if you have a section for this in your UI
    console.log('Top discussions:', discussions);
}

/**
 * Display key insights in the UI
 */
function displayKeyInsights(insights) {
    const insightsList = document.getElementById('insightsList');
    
    if (!insights || insights.length === 0) {
        // Empty state
        const insightsElement = document.getElementById('insights');
        if (insightsElement) {
            insightsElement.classList.add('empty-state');
        }
        return;
    }
    
    // Show the insights section
    const insightsSection = document.getElementById('insights');
    if (insightsSection) {
        insightsSection.classList.remove('d-none');
        insightsSection.classList.remove('empty-state');
    }
    
    // Display each insight using the new card design
    insights.forEach((insight, index) => {
        // Handle different formats of insight data
        let insightText = '';
        let supportingEvidence = [];
        
        if (typeof insight === 'string') {
            insightText = insight;
        } else if (typeof insight === 'object') {
            insightText = insight.insight || insight.text || '';
            supportingEvidence = insight.supporting_evidence || [];
        }
        
        const hasEvidence = supportingEvidence && supportingEvidence.length > 0;
        
        const card = document.createElement('div');
        card.className = 'insight-card';
        
        card.innerHTML = `
            <div class="card-content">
                <div class="d-flex align-items-start">
                    <div class="insight-number">${index + 1}</div>
                    <div class="ms-3 flex-grow-1">
                        <p>${insightText}</p>
                        ${hasEvidence ? `
                            <button class="btn btn-sm btn-outline-primary evidence-btn" 
                                data-bs-toggle="modal" data-bs-target="#evidenceModal"
                                data-type="insight" data-index="${index}">
                                <i class="bi bi-chat-left-quote"></i> View Evidence
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        // Add click handler for evidence button if needed
        if (hasEvidence) {
            const evidenceButton = card.querySelector('.evidence-btn');
            if (evidenceButton) {
                evidenceButton.addEventListener('click', function() {
                    showEvidence(supportingEvidence, `Evidence for Insight ${index + 1}`);
                });
            }
        }
        
        if (insightsList) {
            insightsList.appendChild(card);
        }
    });
}

function displayImprovementAreas(improvements) {
    const improvementsList = document.getElementById('improvementsList');
    
    if (!improvements || improvements.length === 0) {
        // Empty state
        const improvementAreasElement = document.getElementById('improvement-areas');
        if (improvementAreasElement) {
            improvementAreasElement.classList.add('empty-state');
        }
        return;
    }
    
    // Show the improvements section
    const improvementAreasSection = document.getElementById('improvement-areas');
    if (improvementAreasSection) {
        improvementAreasSection.classList.remove('d-none');
        improvementAreasSection.classList.remove('empty-state');
    }
    
    // Display each improvement area using the new card design
    improvements.forEach((improvement, index) => {
        // Handle different formats of improvement data
        let improvementText = '';
        let supportingEvidence = [];
        
        if (typeof improvement === 'string') {
            improvementText = improvement;
        } else if (typeof improvement === 'object') {
            improvementText = improvement.area || improvement.text || '';
            supportingEvidence = improvement.supporting_evidence || [];
        }
        
        const hasEvidence = supportingEvidence && supportingEvidence.length > 0;
        
        const card = document.createElement('div');
        card.className = 'improvement-card';
        
        card.innerHTML = `
            <div class="card-content">
                <div class="d-flex align-items-start">
                    <div class="improvement-number">${index + 1}</div>
                    <div class="ms-3 flex-grow-1">
                        <p>${improvementText}</p>
                        ${hasEvidence ? `
                            <button class="btn btn-sm btn-outline-primary evidence-btn" 
                                data-bs-toggle="modal" data-bs-target="#evidenceModal"
                                data-type="improvement" data-index="${index}">
                                <i class="bi bi-chat-left-quote"></i> View Evidence
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        // Add click handler for evidence button if needed
        if (hasEvidence) {
            const evidenceButton = card.querySelector('.evidence-btn');
            if (evidenceButton) {
                evidenceButton.addEventListener('click', function() {
                    showEvidence(supportingEvidence, `Evidence for Improvement ${index + 1}`);
                });
            }
        }
        
        if (improvementsList) {
            improvementsList.appendChild(card);
        }
    });
}

function displayUnmetNeeds(needs) {
    const unmetNeedsList = document.getElementById('unmetNeedsList');
    
    if (!needs || needs.length === 0) {
        // Empty state
        const unmetNeedsElement = document.getElementById('unmet-needs');
        if (unmetNeedsElement) {
            unmetNeedsElement.classList.add('empty-state');
        }
        return;
    }
    
    // Show the unmet needs section
    const unmetNeedsSection = document.getElementById('unmet-needs');
    if (unmetNeedsSection) {
        unmetNeedsSection.classList.remove('d-none');
        unmetNeedsSection.classList.remove('empty-state');
    }
    
    // Display each unmet need using the new card design
    needs.forEach((need, index) => {
        // Handle different formats of need data
        let needText = '';
        let supportingEvidence = [];
        
        if (typeof need === 'string') {
            needText = need;
        } else if (typeof need === 'object') {
            needText = need.need || need.text || '';
            supportingEvidence = need.supporting_evidence || [];
        }
        
        const hasEvidence = supportingEvidence && supportingEvidence.length > 0;
        
        const card = document.createElement('div');
        card.className = 'unmet-need-card';
        
        card.innerHTML = `
            <div class="card-content">
                <div class="d-flex align-items-start">
                    <div class="unmet-need-number">${index + 1}</div>
                    <div class="ms-3 flex-grow-1">
                        <p>${needText}</p>
                        ${hasEvidence ? `
                            <button class="btn btn-sm btn-outline-primary evidence-btn" 
                                data-bs-toggle="modal" data-bs-target="#evidenceModal"
                                data-type="unmet-need" data-index="${index}">
                                <i class="bi bi-chat-left-quote"></i> View Evidence
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        // Add click handler for evidence button if needed
        if (hasEvidence) {
            const evidenceButton = card.querySelector('.evidence-btn');
            if (evidenceButton) {
                evidenceButton.addEventListener('click', function() {
                    showEvidence(supportingEvidence, `Evidence for Unmet Need ${index + 1}`);
                });
            }
        }
        
        if (unmetNeedsList) {
            unmetNeedsList.appendChild(card);
        }
    });
}

function displayNegativeChats(negativeChats) {
    const negativeChatsList = document.getElementById('negativeChatsList');
    
    // Handle both array format and object format
    let categories = [];
    if (Array.isArray(negativeChats)) {
        categories = negativeChats;
    } else if (negativeChats && negativeChats.categories) {
        categories = negativeChats.categories;
    }
    
    if (!categories || categories.length === 0) {
        // Empty state
        const negativeChatsElement = document.getElementById('negative-chats');
        if (negativeChatsElement) {
            negativeChatsElement.classList.add('empty-state');
        }
        return;
    }
    
    // Show the negative chats section
    const negativeChatsSection = document.getElementById('negative-chats');
    if (negativeChatsSection) {
        negativeChatsSection.classList.remove('d-none');
        negativeChatsSection.classList.remove('empty-state');
    }
    
    // Display each category of negative chats
    categories.forEach((category, index) => {
        const categoryName = category.category || 'Issue Category';
        const examples = category.examples || [];
        const count = category.count || examples.length;
        
        const card = document.createElement('div');
        card.className = 'negative-chat-card';
        
        card.innerHTML = `
            <div class="card-content">
                <div class="d-flex align-items-start justify-content-between">
                    <div class="d-flex">
                        <div class="negative-chat-number">${index + 1}</div>
                        <div class="ms-3">
                            <h4>${categoryName} <span class="badge rounded-pill bg-danger ms-2">${count}</span></h4>
                            <div class="examples-list">
                                ${examples.slice(0, 2).map(example => {
                                    const context = typeof example === 'string' ? example : (example.context || '');
                                    return `<div class="example-item">${context}</div>`;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        if (negativeChatsList) {
            negativeChatsList.appendChild(card);
        }
    });
}

function showEvidence(evidence, title) {
    const modal = document.getElementById('evidenceModal');
    if (!modal) return;
    
    // Set title
    const modalTitle = modal.querySelector('.modal-title');
    if (modalTitle) {
        modalTitle.textContent = title;
    }
    
    // Clear previous content
    const modalBody = modal.querySelector('.modal-body');
    if (modalBody) {
        modalBody.innerHTML = '';
        
        // Format and add evidence
        evidence.forEach((item, index) => {
            const context = typeof item === 'string' ? item : (item.context || '');
            
            const evidenceItem = document.createElement('div');
            evidenceItem.className = 'evidence-item';
            
            // Format the conversation with styling
            let formattedContext = context;
            if (context.includes('USER:') || context.includes('ASSISTANT:')) {
                formattedContext = formatConversation(context);
            }
            
            evidenceItem.innerHTML = `
                <div class="evidence-number">${index + 1}</div>
                <div class="evidence-content">${formattedContext}</div>
            `;
            
            modalBody.appendChild(evidenceItem);
        });
    }
}

function formatConversation(context) {
    // This function could be implemented to format the conversation with styling
    return context;
}

// Initialize event handlers when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set up accordion behavior for dashboard cards
    setupDashboardAccordions();
});

/**
 * Set up accordion behavior for dashboard cards
 */
function setupDashboardAccordions() {
    // Find all card headers
    const cardHeaders = document.querySelectorAll('.card-header-custom');
    
    cardHeaders.forEach(header => {
        header.addEventListener('click', function() {
            // Find the card body associated with this header
            const card = this.closest('.dashboard-card');
            if (!card) return;
            
            const cardBody = card.querySelector('.card-body');
            if (!cardBody) return;
            
            // Toggle the expanded state
            card.classList.toggle('expanded');
            
            // Update the chevron icon
            const chevron = this.querySelector('.bi-chevron-down, .bi-chevron-up');
            if (chevron) {
                chevron.classList.toggle('bi-chevron-down');
                chevron.classList.toggle('bi-chevron-up');
            }
        });
    });
}
