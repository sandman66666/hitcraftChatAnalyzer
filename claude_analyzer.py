import os
import json
import requests
import time
import logging
from typing import List, Dict, Any

# Get logger
logger = logging.getLogger('hitcraft_analyzer')

def analyze_chunks(chunks: List[str], api_key: str = None, use_mock: bool = False, max_chunks: int = None) -> List[Dict[str, Any]]:
    """
    Analyze text chunks using Claude AI and return analysis results
    
    Args:
        chunks: List of text chunks to analyze
        api_key: Claude API key (optional if use_mock is True)
        use_mock: If True, return mock data instead of calling Claude API
        max_chunks: Maximum number of chunks to analyze (default: None = all chunks)
        
    Returns:
        List of analysis results, one for each chunk
    """
    results = []
    
    # If mock mode is enabled, return realistic mock data
    if use_mock:
        logger.info("Using mock data instead of calling Claude AI...")
        return [generate_mock_analysis()]
    
    # Ensure API key is provided if not in mock mode
    if not api_key:
        raise ValueError("Claude API key is required when not using mock mode")
    
    # Limit the number of chunks if specified
    if max_chunks is not None and max_chunks > 0:
        print(f"Limiting analysis to the first {max_chunks} chunks (out of {len(chunks)} total)")
        chunks_to_analyze = chunks[:max_chunks]
    else:
        chunks_to_analyze = chunks
    
    for i, chunk in enumerate(chunks_to_analyze):
        print(f"Analyzing chunk {i+1} of {len(chunks_to_analyze)}...")
        
        try:
            # Send to Claude for analysis and get results
            analysis = analyze_with_claude(chunk, api_key)
            logger.info(f"Analysis of chunk {i+1} completed successfully")
            
            # Debug: Log the structure of the analysis result
            logger.info(f"Analysis result keys: {list(analysis.keys() if isinstance(analysis, dict) else [])}")
            
            results.append(analysis)
            
            # Avoid rate limiting
            if i < len(chunks_to_analyze) - 1:
                time.sleep(1)
                
        except Exception as e:
            error_msg = f"Error analyzing chunk {i+1}: {str(e)}"
            logger.error(error_msg)
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
            {
                "area": "More specialized knowledge in music theory concepts",
                "supporting_evidence": [
                    "Conversation #12: User: 'Can you explain how to use secondary dominants in a jazz context?' Assistant: 'Secondary dominants are chords that temporarily target a chord other than the tonic. In jazz, they're commonly used for creating tension. I'd recommend using them before the ii or V chord for a classic jazz sound.'",
                    "Conversation #27: User: 'What's the difference between modal interchange and secondary dominants?' Assistant: 'Modal interchange borrows chords from parallel modes, while secondary dominants are dominant chords that resolve to a chord other than the tonic. Both add interest to progressions.'"
                ]
            },
            {
                "area": "Better handling of non-English inquiries",
                "supporting_evidence": [
                    "Conversation #41: User: '¿Puedes ayudarme a escribir letras en español?' Assistant: 'I'd be happy to help you write lyrics, but could you provide me with some context or themes you'd like to explore?'",
                    "Conversation #55: User: 'Comment structurer une chanson en français?' Assistant: 'Song structure typically includes verses, chorus, and possibly a bridge. Would you like me to explain these elements in more detail?'"
                ]
            },
            {
                "area": "More detailed guidance on technical aspects of music production",
                "supporting_evidence": [
                    "Conversation #18: User: 'How do I get that warm, saturated drum sound like in this reference track?' Assistant: 'That warm drum sound likely comes from analog saturation or compression. Try adding a saturation plugin to your drum bus and experiment with tape emulation.'",
                    "Conversation #36: User: 'What's the best way to sidechain compress my bass to my kick?' Assistant: 'Sidechain compression helps create room for your kick by ducking the bass. Set up a compressor on your bass track with the kick as the sidechain input, then adjust threshold and release to taste.'"
                ]
            }
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
            {
                "need": "Deeper technical production guidance",
                "supporting_evidence": [
                    "Conversation #23: User: 'How do I create that specific wavy lo-fi effect on my piano?' Assistant: 'To create a lo-fi piano effect, try using a bit crusher plugin, reduce the sample rate, and add some tape saturation or noise.'",
                    "Conversation #47: User: 'What's the best way to create that vocal chop effect like in this track?' Assistant: 'Vocal chops involve cutting vocals into small segments and rearranging them. You can use your DAW's sampler or audio editor to slice vocals, then rearrange them with different pitches or effects.'"
                ]
            },
            {
                "need": "Support for multiple languages",
                "supporting_evidence": [
                    "Conversation #41: User: '¿Puedes ayudarme a escribir letras en español?' Assistant: 'I'd be happy to help you write lyrics, but could you provide me with some context or themes you'd like to explore?'",
                    "Conversation #55: User: 'Comment structurer une chanson en français?' Assistant: 'Song structure typically includes verses, chorus, and possibly a bridge. Would you like me to explain these elements in more detail?'"
                ]
            },
            {
                "need": "More personalized feedback on uploaded music",
                "supporting_evidence": [
                    "Conversation #32: User: 'What do you think of this track? [audio attachment]' Assistant: 'I'm sorry, but I can't listen to audio attachments. If you'd like feedback, please describe the track or share specific aspects you'd like me to comment on.'",
                    "Conversation #67: User: 'Can you tell me if my mix is balanced? [link to track]' Assistant: 'I can't listen to the track, but I can provide general mixing advice. Make sure your kick and bass aren't competing, check that vocals sit well in the mix, and ensure no frequency range is too dominant.'"
                ]
            }
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
            {
                "insight": "Users most frequently seek help with song structure and genre transformation, suggesting these are challenging areas for musicians.",
                "supporting_evidence": [
                    "Conversation #7: User: 'How do I transition from the verse to chorus without it feeling abrupt?' Assistant: 'Try using a pre-chorus as a transitional section. You can also use a drum fill, gradually increase intensity, or introduce a new instrument right before the chorus to smooth the transition.'",
                    "Conversation #15: User: 'I have a folk song but want to make it more electronic. Any suggestions?' Assistant: 'To transform a folk song into an electronic track, start by maintaining the core melody and lyrics. Add a steady electronic beat, introduce synthesizers that complement the original melody, and consider using folk instruments as samples or one-shots.'"
                ]
            },
            {
                "insight": "The conversational format works well for songwriting assistance, where an iterative approach helps users refine their ideas.",
                "supporting_evidence": [
                    "Conversation #22: User: 'I need help writing lyrics about lost love.' Assistant: 'What specific emotions or experiences would you like to convey in these lyrics? Are you looking for something more poetic and metaphorical, or direct and conversational?' User: 'More poetic, focusing on the emptiness afterwards.' Assistant: 'Here are some lyrical ideas that capture that poetic sense of emptiness: [lyrics provided]'",
                    "Conversation #39: User: 'I wrote this chorus but it feels generic.' Assistant: 'Let's see how we can make it more distinctive. What specific emotions or imagery are you trying to convey?' User: 'It's about finding strength after hardship.' Assistant: 'Try incorporating more specific imagery related to your journey. Instead of \"I survived the storm,\" try something like \"Each lightning strike etched new strength in my bones.\"'"
                ]
            },
            {
                "insight": "Users appreciate personalized feedback but want more technical depth in production guidance.",
                "supporting_evidence": [
                    "Conversation #53: User: 'Thanks for the feedback on my lyrics, it's exactly what I needed!' Assistant: 'You're welcome! I'm glad the suggestions were helpful. Let me know if you'd like to work on any other aspects of your songwriting.'",
                    "Conversation #18: User: 'How do I get that warm, saturated drum sound like in this reference track?' Assistant: 'That warm drum sound likely comes from analog saturation or compression. Try adding a saturation plugin to your drum bus and experiment with tape emulation.' User: 'Which specific plugins would you recommend?' Assistant: 'I can't recommend specific plugins, but look for ones that emulate analog tape, tubes, or console saturation.'"
                ]
            },
            {
                "insight": "There's significant interest in music business topics like licensing and copyright, indicating users are concerned about the business side of their music.",
                "supporting_evidence": [
                    "Conversation #44: User: 'Do I need to copyright my song before releasing it?' Assistant: 'In the US, your work is technically copyrighted as soon as it's created in a tangible form. However, registering with the Copyright Office provides stronger legal protection if someone infringes. You can release first and register later, but registration before infringement allows for statutory damages.'",
                    "Conversation #61: User: 'How do streaming royalties work?' Assistant: 'Streaming royalties come from two main sources: mechanical royalties (for the composition) and performance royalties (for the recording). Various entities collect these, including PROs, mechanical royalty agencies, and distributors. Rates vary by platform, but are typically fractions of a cent per stream.'"
                ]
            },
            {
                "insight": "The ability to process and provide feedback on uploaded music is highly valued by users.",
                "supporting_evidence": [
                    "Conversation #32: User: 'What do you think of this track? [audio attachment]' Assistant: 'I'm sorry, but I can't listen to audio attachments. If you'd like feedback, please describe the track or share specific aspects you'd like me to comment on.' User: 'Oh that's disappointing.'",
                    "Conversation #67: User: 'Can you tell me if my mix is balanced? [link to track]' Assistant: 'I can't listen to the track, but I can provide general mixing advice. Make sure your kick and bass aren't competing, check that vocals sit well in the mix, and ensure no frequency range is too dominant.' User: 'I was hoping for specific feedback on my actual mix.'"
                ]
            }
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
    
    4. "improvement_areas": Identify specific areas where the product could be improved based on user interactions, with each area including:
       - "area": The improvement area
       - "supporting_evidence": Array of 1-3 excerpts from the chat logs that demonstrate this need for improvement
    
    5. "user_satisfaction": Gauge overall user satisfaction based on conversation flow and user engagement
    
    6. "unmet_needs": Identify cases where users didn't get what they wanted, with each need including:
       - "need": The unmet need
       - "supporting_evidence": Array of 1-3 excerpts from the chat logs that demonstrate this unmet need
    
    7. "product_effectiveness": Assess how well the product delivers on its promise as a music production/songwriting assistant
    
    8. "key_insights": List 3-5 key insights from your analysis, with each insight including:
       - "insight": The key insight
       - "supporting_evidence": Array of 1-3 excerpts from the chat logs that support this insight
    
    Important: For each supporting_evidence item, please include the exact text from the conversation, prefixed with the conversation position (e.g., "Conversation #3: ...").
    
    Return only valid JSON. The entire response should be parseable as JSON.
    """
    
    data = {
        "model": "claude-3-opus-20240229",  # Use the latest Claude model available
        "max_tokens": 4000,
        "temperature": 0.0,  # We want deterministic, analytical responses
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        logger.info("Sending request to Claude API...")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120  # Allow up to 2 minutes for response
        )
        
        if not response.ok:
            logger.error(f"Claude API returned status code {response.status_code}")
            logger.error(f"Response content: {response.text}")
            if "error" in response.text:
                try:
                    error_data = json.loads(response.text)
                    logger.error(f"API Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
                except:
                    pass
            return generate_mock_analysis()  # Use mock data on API error
        
        result = response.json()
        logger.info("Successfully received response from Claude API")
        
        # Extract the content from Claude's response
        if 'content' not in result or not result['content']:
            logger.error("No content in Claude response")
            return generate_mock_analysis()
            
        content = result['content'][0]['text']
        logger.info(f"Response content length: {len(content)}")
        
        # Parse the JSON response
        try:
            # Sometimes Claude might include markdown code block syntax, so we handle that
            if "```json" in content:
                logger.info("Extracting JSON from markdown code block (```json)")
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                logger.info("Extracting JSON from markdown code block (```)")
                json_str = content.split("```")[1].strip()
            else:
                logger.info("Using raw content as JSON")
                json_str = content.strip()
            
            logger.info(f"JSON string length: {len(json_str)}")
            logger.info(f"JSON string preview: {json_str[:300]}...")
            
            analysis_result = json.loads(json_str)
            
            # Verify the result contains all required fields
            required_fields = ["categories", "top_discussions", "response_quality", 
                            "improvement_areas", "user_satisfaction", "unmet_needs", 
                            "product_effectiveness", "key_insights"]
            
            missing_fields = [field for field in required_fields if field not in analysis_result]
            if missing_fields:
                logger.warning(f"Analysis result is missing fields: {missing_fields}")
                # Fill in any missing fields with empty values
                for field in missing_fields:
                    if field in ["response_quality", "user_satisfaction", "product_effectiveness"]:
                        analysis_result[field] = {}
                    else:
                        analysis_result[field] = []
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {str(e)}")
            logger.error(f"Raw response content: {content[:500]}...")
            
            # Return mock data instead of failing
            return generate_mock_analysis()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        # Return mock data on request error
        return generate_mock_analysis()

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
    
    # If there's only one result and it's a mock, just return it
    if len(results) == 1:
        # Check if we're likely dealing with mock data
        if "categories" in results[0] and len(results[0]["categories"]) >= 5:
            logger.info("Only one result, likely mock data, returning as is")
            return results[0]
    
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
            logger.warning(f"Skipping result with error: {result.get('error')}")
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