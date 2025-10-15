import json
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def clean_chatbot_response(response: str) -> Dict[str, Any]:
    """
    Cleans and extracts JSON from a chatbot response.
    
    Args:
        response: Raw chatbot response containing JSON
        
    Returns:
        Parsed JSON if valid, otherwise an error message
    """
    if not isinstance(response, str) or not response.strip():
        return {"error": "Empty or invalid response"}
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        response = json_match.group(1).strip()
    
    # Try to extract JSON object
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON"}
    
    return {"error": "No valid JSON found in response"}

def clean_and_parse_json(response: str) -> Dict[str, Any]:
    """
    Parse JSON response with default fallback values.
    
    Args:
        response: Raw response string
        
    Returns:
        Dictionary with chatbot response and flags
    """
    default_response = {
        "chatbot_response": "",
        "run_retrieval_products": False,
        "run_retrieval_orders": False,
        "send_invoice_email": False
    }
    
    if not isinstance(response, str) or not response.strip():
        return default_response
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        response = json_match.group(1).strip()
    
    # Try to extract JSON object
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON")
    
    # If parsing fails, return response as plain text
    default_response["chatbot_response"] = response.strip()
    return default_response
