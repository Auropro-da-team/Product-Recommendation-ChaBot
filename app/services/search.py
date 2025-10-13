import logging
import pandas as pd
from typing import List, Dict, Any
from app.config import settings
from app.utils.parsers import clean_chatbot_response

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, model, chroma_manager, agent):
        self.model = model
        self.chroma_manager = chroma_manager
        self.agent = agent
    
    def search_products(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for products using semantic similarity.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            
        Returns:
            List of product dictionaries
        """
        query_embedding = self.model.encode(query, convert_to_numpy=True).tolist()
        results = self.chroma_manager.query_products(query_embedding, top_k)
        
        if not results["metadatas"][0]:
            return []
        
        products = results["metadatas"][0]
        scores = results["distances"][0]
        
        results_df = pd.DataFrame(products)
        results_df["Similarity Score"] = [1 / (1 + score) for score in scores]
        
        # Handle price prioritization
        words = query.split()
        price_query = next((float(w) for w in words if w.replace('.', '').isdigit()), None)
        
        if price_query:
            results_df["Price Difference"] = abs(results_df["Price"] - price_query)
            results_df = results_df.sort_values(
                by=["Price Difference", "Similarity Score"],
                ascending=[True, False]
            )
            results_df.drop(columns=["Price Difference"], inplace=True)
        
        return results_df[[
            'Product ID', 'Product Name', 'Price', 'Brand Name', 'Discount', 
            'Activity', 'Face Shape', 'Product Type', 'Image URL', 
            'Prescription Type', 'Frame Colour', 'Lens Color', 'Similarity Score'
        ]].to_dict(orient="records")
    
    def search_orders(
        self,
        conversation_history: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for orders using entity extraction and filtering.
        SECURITY: Only fetch orders if Order ID, Email, or Customer Name is explicitly provided.
        
        Args:
            conversation_history: Formatted conversation history
            query: User query string
            top_k: Number of top results
            
        Returns:
            List of order dictionaries (empty if no identifier provided)
        """
        # Entity extraction via LLM
        extraction_prompt = f"""
Given this query about orders: {query} and the conversation history: {conversation_history}

Extract the following information:

- **Order ID**: Extract strings that look like order IDs (e.g., "O1001", "o1023") even if the word "order" is not used.
- **Customer Name**: Extract if a specific person's name is clearly mentioned (e.g., "John Doe", "Likith", "Asrith").
- **Customer Email**: Extract if an email address is directly stated (e.g., "user@example.com").

CRITICAL: Do NOT infer or hallucinate information that is not EXPLICITLY present in the query or conversation history.

Return your answer as a JSON with the following format:

{{
  "order_id": "The specific order ID mentioned (or null if none)",
  "customer_name": "The specific customer name mentioned (or null if none)",
  "email": "The specific email mentioned (or null if none)"
}}
"""
        
        entity_extraction_response = self.agent.run(extraction_prompt).content
        extracted_entities = clean_chatbot_response(entity_extraction_response)
        
        logger.info(f"Extracted entities: {extracted_entities}")
        
        # Normalize order_id into a list
        order_ids = extracted_entities.get("order_id")
        if order_ids and order_ids != "null":
            if isinstance(order_ids, str):
                order_ids = [order_ids]
            elif not isinstance(order_ids, list):
                order_ids = []
        else:
            order_ids = []
        
        # Extract customer name
        customer_name = extracted_entities.get("customer_name")
        if customer_name and customer_name != "null" and isinstance(customer_name, str):
            customer_name = customer_name.strip()
        else:
            customer_name = None
        
        # Extract email
        email = extracted_entities.get("email")
        if email and email != "null" and isinstance(email, str):
            email = email.strip()
        else:
            email = None
        
        # SECURITY FIX: Only proceed if we have at least ONE explicit identifier
        if not order_ids and not email and not customer_name:
            logger.warning("Order search attempted without any identifier (Order ID, Email, or Customer Name) - returning empty for security")
            return []
        
        logger.info(f"Searching orders with - Order IDs: {order_ids}, Email: {email}, Customer Name: {customer_name}")
        
        # Fetch all orders for filtering
        all_matches = self.chroma_manager.get_all_orders()
        matched_orders = []
        
        if not all_matches or "metadatas" not in all_matches:
            return []
        
        # Filter by Order ID (highest priority)
        if order_ids:
            for metadata in all_matches["metadatas"]:
                if metadata and "Order ID" in metadata:
                    for oid in order_ids:
                        if oid.lower() in metadata["Order ID"].lower():
                            matched_orders.append(metadata)
            logger.info(f"Found {len(matched_orders)} orders matching Order IDs: {order_ids}")
            return matched_orders
        
        # Filter by Email
        if email:
            for metadata in all_matches["metadatas"]:
                if metadata and "Email ID" in metadata:
                    if email.lower() in metadata["Email ID"].lower():
                        matched_orders.append(metadata)
            logger.info(f"Found {len(matched_orders)} orders matching Email: {email}")
            if matched_orders:
                return matched_orders
        
        # Filter by Customer Name
        if customer_name:
            for metadata in all_matches["metadatas"]:
                if metadata and "Customer Name" in metadata:
                    # Case-insensitive partial match for names
                    if customer_name.lower() in metadata["Customer Name"].lower():
                        matched_orders.append(metadata)
            logger.info(f"Found {len(matched_orders)} orders matching Customer Name: {customer_name}")
            if matched_orders:
                return matched_orders
        
        return []