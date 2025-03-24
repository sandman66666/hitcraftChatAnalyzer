import os
import json
import requests
import time
from typing import List, Dict, Any

def analyze_chunks(chunks: List[str], api_key: str = None, use_mock: bool = False) -> List[Dict[str, Any]]:
    """
    Analyze text chunks using Claude AI and return analysis results
    
    Args:
        chunks: List of text chunks to analyze
        api_key: Claude API key (optional if use_mock is True)
        use_mock: If True, return mock data instead of calling Claude API
        
    Returns:
        List of analysis results, one for each chunk
    """
    results = []
    
    # If mock mode is enabled, return realistic mock data
    if use_mock:
        print("Using mock data instead of calling Claude AI...")
        return [generate_mock_analysis()]
    
    # Ensure API key is provided if not in mock mode
    if not api_key:
        raise ValueError("Claude API key is required when not using mock mode")
    
    for i, chunk in enumerate(chunks):
        print(f"Analyzing chunk {i+1} of {len(chunks)}...")
        
        try:
            # Send to Claude for analysis and get results
            analysis = analyze_with_claude(chunk, api_key)
            results.append(analysis)
            
            # Avoid rate limiting
            if i < len(chunks) - 1:
                time.sleep(1)
                
        except Exception as e:
            print(f"Error analyzing chunk {i+1}: {str(e)}")
            # Add partial result to maintain chunk order
            results.append({
                "error": str(e),
                "chunk_index": i,
                "partial_analysis": {}
            })
    
    return results

def generate_mock_analysis() -> Dict[str, Any]:
    """Generate realistic mock analysis data for demonstration"""
    return {
        "categories": [
            "Music Production Assistance",
            "Songwriting Help",
            "Music Theory Questions",
            "Licensing & Copyright",
            "Music Business",
            "Genre Exploration"
        ],
        "top_discussions": [
            {"topic": "Song Structure Development", "count": 8},
            {"topic": "Genre Transformation", "count": 7},
            {"topic": "Lyric Writing", "count": 6},
            {"topic": "Production References", "count": 5},
            {"topic": "Music Licensing", "count": 4}
        ],
        "response_quality": {
            "average_score": 8.5,
            "good_examples": [
                "In response to a user request for music licensing information, the assistant provided a comprehensive breakdown of different types of licenses, why they're important, and next steps.",
                "When asked about songwriting, the assistant provided personalized lyric suggestions and offered clear next steps for refining them.",
                "The assistant effectively guided a user through choosing a production reference, asking clarifying questions to better understand their needs."
            ],
            "poor_examples": [
                "In one conversation, the assistant seemed confused by a request for specific drum patterns and provided overly generic advice.",
                "When faced with a request in a non-English language, the assistant responded in English without acknowledging the language difference."
            ]
        },
        "improvement_areas": [
            "More specialized knowledge in music theory concepts",
            "Better handling of non-English inquiries",
            "More detailed guidance on technical aspects of music production",
            "More personalized responses based on user's skill level",
            "Better continuity between conversations with the same user"
        ],
        "user_satisfaction": {
            "overall_assessment": "Users generally appear satisfied with the service, particularly when getting specific guidance on song structure, genre transformation, and lyric writing. However, satisfaction appears lower when technical production questions aren't fully addressed.",
            "positive_indicators": [
                "Users often continue conversations after initial responses",
                "Multiple users engage in multi-message threads",
                "Users frequently adopt assistant suggestions",
                "Several users return for additional help on their projects"
            ],
            "negative_indicators": [
                "Some abandoned conversations after unclear responses",
                "Occasional repetition of questions suggesting the initial answer wasn't satisfactory",
                "Some users seeking more technical production details than provided"
            ]
        },
        "unmet_needs": [
            "Deeper technical production guidance",
            "Support for multiple languages",
            "More personalized feedback on uploaded music",
            "Better understanding of specific musical genres",
            "More detailed music business advice"
        ],
        "product_effectiveness": {
            "assessment": "HitCraft effectively serves as a helpful music production and songwriting assistant, particularly excelling at lyric generation, song structure guidance, and basic music business advice. It provides accessible support for users at various skill levels but could improve in technical depth.",
            "strengths": [
                "Personalized songwriting assistance",
                "Accessible explanations of music concepts",
                "Helpful guidance for genre exploration",
                "Good at maintaining engagement through conversation"
            ],
            "weaknesses": [
                "Limited technical depth for advanced producers",
                "Occasional misunderstanding of specific genre contexts",
                "Inconsistent handling of non-English requests"
            ]
        },
        "key_insights": [
            "Users most frequently seek help with song structure and genre transformation, suggesting these are challenging areas for musicians.",
            "The conversational format works well for songwriting assistance, where an iterative approach helps users refine their ideas.",
            "Users appreciate personalized feedback but want more technical depth in production guidance.",
            "There's significant interest in music business topics like licensing and copyright, indicating users are concerned about the business side of their music.",
            "The ability to process and provide feedback on uploaded music is highly valued by users."
        ]
    }

def analyze_with_claude(text: str, api_key: str) -> Dict[str, Any]:
    """
    Send text to Claude AI for analysis
    
    Args:
        text: Text content to analyze
        api_key: Claude API key
        
    Returns:
        Analysis results from Claude
    """
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"  # Using the Anthropic API version, update as needed
    }
    
    prompt = f"""
    You are an expert conversation analyst. I will provide you with chat logs from a product called HitCraft, which appears to be a music production and songwriting assistant. 
    
    Here is a sample of chat logs:
    
    ```
    {text}
    ```
    
    Please analyze these conversations and provide insights in the following JSON format:
    
    1. "categories": List the main categories of conversations you observe (e.g., song production, music theory, etc.)
    
    2. "top_discussions": Identify the top 5 most common discussion topics, with counts if possible
    
    3. "response_quality": Evaluate the quality of the assistant's responses (scale 1-10) with specific examples of good and poor responses
    
    4. "improvement_areas": Identify specific areas where the product could be improved based on user interactions
    
    5. "user_satisfaction": Gauge overall user satisfaction based on conversation flow and user engagement
    
    6. "unmet_needs": Identify cases where users didn't get what they wanted
    
    7. "product_effectiveness": Assess how well the product delivers on its promise as a music production/songwriting assistant
    
    8. "key_insights": List 3-5 key insights from your analysis
    
    Important: Return only valid JSON. The entire response should be parseable as JSON.
    """
    
    data = {
        "model": "claude-3-opus-20240229",  # Use the latest Claude model available
        "max_tokens": 4000,
        "temperature": 0.0,  # We want deterministic, analytical responses
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120  # Allow up to 2 minutes for response
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Extract the content from Claude's response
        content = result['content'][0]['text']
        
        # Parse the JSON response
        try:
            # Sometimes Claude might include markdown code block syntax, so we handle that
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content.strip()
            
            analysis_result = json.loads(json_str)
            return analysis_result
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text
            return {"error": "Failed to parse JSON from Claude response", "raw_response": content}
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error calling Claude API: {str(e)}")

def combine_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine analysis results from multiple chunks into a single comprehensive analysis
    
    Args:
        results: List of analysis results from individual chunks
        
    Returns:
        Combined analysis
    """
    if not results:
        return {"error": "No analysis results to combine"}
    
    # Initialize combined analysis structure
    combined = {
        "categories": [],
        "top_discussions": [],
        "response_quality": {
            "average_score": 0,
            "good_examples": [],
            "poor_examples": []
        },
        "improvement_areas": [],
        "user_satisfaction": {
            "overall_assessment": "",
            "positive_indicators": [],
            "negative_indicators": []
        },
        "unmet_needs": [],
        "product_effectiveness": {
            "assessment": "",
            "strengths": [],
            "weaknesses": []
        },
        "key_insights": []
    }
    
    # Counter for averaging scores
    quality_scores = []
    chunk_count = 0
    
    # Process each chunk's analysis
    for result in results:
        if "error" in result:
            continue
        
        chunk_count += 1
        
        # Aggregate categories
        if "categories" in result:
            combined["categories"].extend([cat for cat in result["categories"] 
                                         if cat not in combined["categories"]])
        
        # Aggregate top discussions
        if "top_discussions" in result:
            # Add unique discussion topics
            for topic in result["top_discussions"]:
                if isinstance(topic, dict) and "topic" in topic:
                    # Handle case where topics are objects with counts
                    existing = next((t for t in combined["top_discussions"] 
                                    if isinstance(t, dict) and t.get("topic") == topic["topic"]), None)
                    if existing:
                        existing["count"] = existing.get("count", 0) + topic.get("count", 1)
                    else:
                        combined["top_discussions"].append(topic)
                elif topic not in combined["top_discussions"]:
                    # Handle case where topics are simple strings
                    combined["top_discussions"].append(topic)
        
        # Aggregate response quality
        if "response_quality" in result:
            if isinstance(result["response_quality"], dict):
                if "score" in result["response_quality"]:
                    quality_scores.append(result["response_quality"]["score"])
                elif "average_score" in result["response_quality"]:
                    quality_scores.append(result["response_quality"]["average_score"])
                
                # Add unique examples
                if "good_examples" in result["response_quality"]:
                    combined["response_quality"]["good_examples"].extend(
                        [ex for ex in result["response_quality"]["good_examples"] 
                         if ex not in combined["response_quality"]["good_examples"]]
                    )
                if "poor_examples" in result["response_quality"]:
                    combined["response_quality"]["poor_examples"].extend(
                        [ex for ex in result["response_quality"]["poor_examples"] 
                         if ex not in combined["response_quality"]["poor_examples"]]
                    )
            elif isinstance(result["response_quality"], (int, float)):
                quality_scores.append(result["response_quality"])
        
        # Aggregate improvement areas
        if "improvement_areas" in result:
            combined["improvement_areas"].extend(
                [area for area in result["improvement_areas"] 
                 if area not in combined["improvement_areas"]]
            )
        
        # Aggregate user satisfaction
        if "user_satisfaction" in result:
            if isinstance(result["user_satisfaction"], dict):
                # Add assessment text
                if "overall_assessment" in result["user_satisfaction"] and result["user_satisfaction"]["overall_assessment"]:
                    if combined["user_satisfaction"]["overall_assessment"]:
                        combined["user_satisfaction"]["overall_assessment"] += " " + result["user_satisfaction"]["overall_assessment"]
                    else:
                        combined["user_satisfaction"]["overall_assessment"] = result["user_satisfaction"]["overall_assessment"]
                
                # Add indicators
                if "positive_indicators" in result["user_satisfaction"]:
                    combined["user_satisfaction"]["positive_indicators"].extend(
                        [ind for ind in result["user_satisfaction"]["positive_indicators"] 
                         if ind not in combined["user_satisfaction"]["positive_indicators"]]
                    )
                if "negative_indicators" in result["user_satisfaction"]:
                    combined["user_satisfaction"]["negative_indicators"].extend(
                        [ind for ind in result["user_satisfaction"]["negative_indicators"] 
                         if ind not in combined["user_satisfaction"]["negative_indicators"]]
                    )
            elif isinstance(result["user_satisfaction"], str):
                if combined["user_satisfaction"]["overall_assessment"]:
                    combined["user_satisfaction"]["overall_assessment"] += " " + result["user_satisfaction"]
                else:
                    combined["user_satisfaction"]["overall_assessment"] = result["user_satisfaction"]
        
        # Aggregate unmet needs
        if "unmet_needs" in result:
            combined["unmet_needs"].extend(
                [need for need in result["unmet_needs"] 
                 if need not in combined["unmet_needs"]]
            )
        
        # Aggregate product effectiveness
        if "product_effectiveness" in result:
            if isinstance(result["product_effectiveness"], dict):
                # Add assessment text
                if "assessment" in result["product_effectiveness"] and result["product_effectiveness"]["assessment"]:
                    if combined["product_effectiveness"]["assessment"]:
                        combined["product_effectiveness"]["assessment"] += " " + result["product_effectiveness"]["assessment"]
                    else:
                        combined["product_effectiveness"]["assessment"] = result["product_effectiveness"]["assessment"]
                
                # Add strengths and weaknesses
                if "strengths" in result["product_effectiveness"]:
                    combined["product_effectiveness"]["strengths"].extend(
                        [s for s in result["product_effectiveness"]["strengths"] 
                         if s not in combined["product_effectiveness"]["strengths"]]
                    )
                if "weaknesses" in result["product_effectiveness"]:
                    combined["product_effectiveness"]["weaknesses"].extend(
                        [w for w in result["product_effectiveness"]["weaknesses"] 
                         if w not in combined["product_effectiveness"]["weaknesses"]]
                    )
            elif isinstance(result["product_effectiveness"], str):
                if combined["product_effectiveness"]["assessment"]:
                    combined["product_effectiveness"]["assessment"] += " " + result["product_effectiveness"]
                else:
                    combined["product_effectiveness"]["assessment"] = result["product_effectiveness"]
        
        # Aggregate key insights
        if "key_insights" in result:
            combined["key_insights"].extend(
                [insight for insight in result["key_insights"] 
                 if insight not in combined["key_insights"]]
            )
    
    # Calculate average response quality score
    if quality_scores:
        combined["response_quality"]["average_score"] = sum(quality_scores) / len(quality_scores)
    
    # Sort top discussions by count if they have count attributes
    if all(isinstance(topic, dict) and "count" in topic for topic in combined["top_discussions"]):
        combined["top_discussions"] = sorted(
            combined["top_discussions"], 
            key=lambda x: x.get("count", 0), 
            reverse=True
        )
    
    # Limit top discussions to 5
    combined["top_discussions"] = combined["top_discussions"][:5]
    
    # Limit examples to avoid overwhelming results
    combined["response_quality"]["good_examples"] = combined["response_quality"]["good_examples"][:3]
    combined["response_quality"]["poor_examples"] = combined["response_quality"]["poor_examples"][:3]
    
    # Limit key insights to the top 5
    combined["key_insights"] = combined["key_insights"][:5]
    
    return combined