import logging
from typing import Dict, Any, Tuple, List
from app.utils.parsers import clean_and_parse_json, clean_chatbot_response
from app.utils.formatters import format_product_table, format_order_table

logger = logging.getLogger(__name__)

class ChatbotService:
    def __init__(self, agent, search_service):
        self.agent = agent
        self.search_service = search_service
    
    def _extract_product_ids_from_history(self, conversation_history: str) -> List[str]:
        """Extract Product IDs from conversation history."""
        product_ids = []
        try:
            # Look for product recommendations in history
            if "Product ID" in conversation_history:
                import re
                # Match patterns like "Product ID: P019" or "'Product ID': 'P019'"
                matches = re.findall(r"['\"]?Product ID['\"]?\s*:\s*['\"]?(P\d+)['\"]?", conversation_history)
                product_ids.extend(matches)
        except Exception as e:
            logger.error(f"Error extracting product IDs from history: {e}")
        return list(set(product_ids))  # Remove duplicates
    
    def _extract_order_id_from_input(self, user_input: str, conversation_history: str) -> str:
        """Extract Order ID from user input or conversation history."""
        import re
        # Look for order ID patterns like O1001, o1023, etc.
        matches = re.findall(r'\b[Oo]\d{4,}\b', user_input + " " + conversation_history)
        return matches[0] if matches else None
    
    def process_message(
        self,
        user_input: str,
        conversation_history: str
    ) -> Tuple[Any, bool]:
        """
        Process user message and generate response.
        
        Args:
            user_input: User's message
            conversation_history: Formatted conversation history
            
        Returns:
            Tuple of (response, send_invoice_flag)
        """
        
        # Extract previously recommended Product IDs from conversation history
        previously_recommended_product_ids = self._extract_product_ids_from_history(conversation_history)
        
        # Check if there's an Order ID in the input or history
        order_id_present = self._extract_order_id_from_input(user_input, conversation_history)
        
        prompt = f"""
You are an Essilor chatbot, a company that provides expert advice on sunglasses and eyewear.
Maintain a professional yet friendly tone. Personalize responses based on the user's needs. *Do not hallucinate*. Respond to the user in 3-4 lines.
You should be able to answer basic trivia questions about glasses, about outfit choices that would match your products and other similar functions using your knowledge. Be creative.
*Do not repeat yourself when the user's query changes.*
You should be able to answer all kinds of questions about a product, including price, discount, more information, etc.
You can also answer questions about orders, including order status, delivery date, and other order-related information.

You need to extract the order id from user queries, the order id is of the form "o1001", "O1001" and product id is of the form "p001" or "P011"

IMPORTANT: If the user asks questions like "Did I buy any of these?", "Have I ordered this before?", or similar queries about previously recommended products:
- Previously recommended Product IDs: {previously_recommended_product_ids if previously_recommended_product_ids else "None"}
- Order ID detected in conversation: {order_id_present if order_id_present else "None"}
- ONLY set run_retrieval_orders=true if BOTH conditions are met:
  1. Previously recommended Product IDs exist
  2. You need to check if user ordered those specific products
- If there's no Order ID in the conversation, set run_retrieval_orders=false and ask the user for their Order ID

CRITICAL ORDER RETRIEVAL RULES (SECURITY):
- run_retrieval_orders should ONLY be true when AT LEAST ONE of these identifiers is present:
  1. An explicit Order ID (like O1001, O1023) is mentioned in the current input OR conversation history
  2. OR an explicit Email address is mentioned in the current input OR conversation history
  3. OR an explicit Customer Name is mentioned in the current input OR conversation history
- For ALL order-related queries WITHOUT any identifier (including "Did I order these?", "show my orders", "my last order"):
  * Set run_retrieval_orders=false
  * Ask the user to provide their Order ID, Email, or Name for security reasons
- NEVER set run_retrieval_orders=true without explicit user identification (Order ID, Email, or Name)
- This is a CRITICAL SECURITY requirement to protect customer privacy

If the user expresses that they want to get their invoice, follow these rules:
- If the order ID *is present* in the conversation history, set send_invoice_email: true and run_retrieval_orders: true
- When the user asks for an invoice, remember the conversation history when they provide their order ID.

If the user input can be answered from the conversation history, don't run retrieval.

Conversation History:
{conversation_history}

User: {user_input}

Before responding, determine if the user is asking about glasses/products or about orders.

Only set run_retrieval_orders=true AND send_invoice_email=true when you have an actual order ID to search for (like O1001, O1023, etc.).

For vague order queries like "my last order", "show my orders", "what did I order", or "did I order these", set run_retrieval_orders = false and ask for their Order ID, Email, or Name for security verification.

When the user asks for an invoice AND their order ID is NOT in conversation history, you need to ask the user for their order ID and set send_invoice_email=false AND run_retrieval_orders=false

IMPORTANT: For "Did I buy any of these?" or similar comparison queries, you MUST ask for Order ID, Email, or Name first. Set run_retrieval_orders=false until they provide identification.

Before responding, make sure that the product or order the user is looking for is actually in the database when run_retrieval_products or run_retrieval_orders = true. *Do not hallucinate*.

Return a JSON response in the *exact* format below:

{{
  "chatbot_response": "Your response here.",
  "run_retrieval_products": true or false,
  "run_retrieval_orders": true or false,
  "send_invoice_email": true or false
}}

CRITICAL RULES FOR run_retrieval_products:
- If the user asks for SPECIFIC product recommendations with clear criteria (like "Recommend 4 glasses for trek", "sunglasses under 2000", "Ray-Ban aviators", "glasses for oval face", "top 3 glasses for X"), ALWAYS set "run_retrieval_products": true IMMEDIATELY. DO NOT ask clarifying questions.
- The words "recommend", "show me", "find", "suggest" combined with specific use cases (trek, vacation, sports, beach, etc.) or numbers (top 3, 4 glasses, etc.) are SPECIFIC queries.
- Only set "run_retrieval_products": false for extremely vague queries like "I need glasses" or "tell me about eyewear" WITHOUT any specific criteria.
- If user says "yes" after you asked if they want recommendations, set "run_retrieval_products": true.

For vague queries WITHOUT specific criteria, set "run_retrieval_products": false and ask ONE clarifying question.

If the user is asking about orders (like order status, delivery date, specific order ID), set "run_retrieval_orders": true ONLY if an Order ID is present.

IMPORTANT: If the user asks for product recommendations for fashion/outfit matching (like "glasses for grey suit", "sunglasses for beach outfit"), treat this as a SPECIFIC product query and set "run_retrieval_products": true.

For general trivia questions NOT related to product recommendations (like "who invented sunglasses?", "how to clean glasses?"), set both to false.
"""
        
        raw_response = self.agent.run(prompt).content
        logger.info(f"Raw agent response: {raw_response}")
        response_json = clean_and_parse_json(raw_response)
        logger.info(f"Parsed response: {response_json}")
        
        # IMPORTANT FIX: Ensure run_retrieval_orders is true if send_invoice_email is true
        if response_json.get("send_invoice_email", False) and not response_json.get("run_retrieval_orders", False):
            response_json["run_retrieval_orders"] = True
            logger.info("Setting run_retrieval_orders to True because send_invoice_email is True")
        
        retrieved_products = []
        retrieved_orders = []
        
        # Process product retrieval
        if response_json.get("run_retrieval_products", False):
            retrieved_products = self.search_service.search_products(user_input)
            
            if retrieved_products and len(retrieved_products) > 0:
                product_info = "\n".join([
                    f"🕶 Product ID: {p.get('Product ID', 'N/A')}, {p['Product Name']} ({p['Brand Name']}) - Price: {p['Price']} INR, "
                    f"Discount: {p['Discount']}%, Suitable for: {p['Activity']}, "
                    f"Face Shape: {p['Face Shape']} \n🌄 Image: {p['Image URL']}, "
                    f"lens prescription type: {p['Prescription Type']}, "
                    f"frame color: {p['Frame Colour']}, lens color: {p['Lens Color']}"
                    for p in retrieved_products
                ])
                
                retrieval_prompt = f"""
You have the following conversation history: {conversation_history}. Using that, once you've retrieved the product {product_info}
Based on {conversation_history} and {user_input}, give the best and most relevant responses from {product_info}.
 - Always give the complete info about the products, including their Product ID, price, and other details.
- You should give very human-like responses and need to be conversational.
- When you recommend a product to a user, you need to logically explain why you're recommending the product in 1-2 lines.
- Given this information, generate a conversational response summarizing the best product options for the user in 3-4 lines. *Do not hallucinate.*
If a product does not exist in the database, tell the user that and then give a similar product recommendation.

- Respond in JSON format with a list of products having the following structure (MUST include Product ID):

{{
"chatbot_response": "Ok, I have found a few products for you:",
"products": [
    {{
    "Product ID": "P001",
    "Product Name": "Product 1",
    "Price": 1000,
    "Brand Name": "Brand A",
    "Discount": "10%",
    "Activity": "Outdoor",
    "Face Shape": "Round",
    "Product Type": "Sunglasses",
    "Image URL": "http://example.com/image1.jpg",
    "Prescription Type": "Single Vision",
    "Frame Colour": "Black",
    "Lens Color": "Gray"
    }}
]
}}
"""
                
                response_json["chatbot_response"] = self.agent.run(retrieval_prompt).content
        
        # Process order retrieval
        if response_json.get("run_retrieval_orders", False):
            retrieved_orders = self.search_service.search_orders(conversation_history, user_input)
            logger.info(f"Retrieved orders count: {len(retrieved_orders)}")
            
            if retrieved_orders:
                # Check if this is a comparison query
                is_comparison_query = any(phrase in user_input.lower() for phrase in [
                    "did i buy", "have i ordered", "purchased any", "bought any of these",
                    "ordered any of these", "have i bought", "did i order"
                ])
                
                # ALWAYS check for comparison if there are previously recommended products
                if previously_recommended_product_ids and (is_comparison_query or "these" in user_input.lower() or "recommended" in user_input.lower()):
                    # This is a comparison query - compare Product IDs
                    ordered_product_ids = [order.get('Product ID') for order in retrieved_orders if order.get('Product ID')]
                    matching_products = [pid for pid in previously_recommended_product_ids if pid in ordered_product_ids]
                    
                    logger.info(f"Previously recommended: {previously_recommended_product_ids}")
                    logger.info(f"User's ordered products: {ordered_product_ids}")
                    logger.info(f"Matches found: {matching_products}")
                    
                    if matching_products:
                        # Found matches - user DID order some recommended products
                        matched_orders = [order for order in retrieved_orders if order.get('Product ID') in matching_products]
                        
                        order_info = "\n".join([
                            f"📦 Order #{o['Order ID']} - Product: {o['Product Name']} (Product ID: {o['Product ID']}), "
                            f"Customer: {o['Customer Name']}, Email: {o['Email ID']}, "
                            f"Ordered on: {o['Date of Order']}, Status: {o['Order Status']}, "
                            f"Delivery date: {o['Date of Delivery']}, Quantity: {o['Quantity']}"
                            for o in matched_orders
                        ])
                        
                        comparison_prompt = f"""
The user asked: "{user_input}"

Previously recommended Product IDs: {previously_recommended_product_ids}
User's order history shows they purchased products: {ordered_product_ids}
Matching products found: {matching_products}

Matching order details:
{order_info}

Generate a friendly response (3-4 lines) that:
1. Starts with "Yes!" to confirm they ordered some recommended products
2. Mentions which specific product(s) they bought (by name and Product ID)
3. Provides key order details (order ID, status, delivery date)

Respond in JSON format with the matching orders:

{{
"chatbot_response": "Yes! You've ordered [Product Name] (Product ID: [PID]) from my recommendations. Your order [Order ID] was [status] on [date].",
"orders": [matching orders here]
}}
"""
                        response_json["chatbot_response"] = self.agent.run(comparison_prompt).content
                    else:
                        # No matches - user did NOT order any recommended products
                        order_info = "\n".join([
                            f"📦 Order #{o['Order ID']} - Product: {o['Product Name']} (Product ID: {o['Product ID']}), "
                            f"Customer: {o['Customer Name']}, Email: {o['Email ID']}, "
                            f"Ordered on: {o['Date of Order']}, Status: {o['Order Status']}, "
                            f"Delivery date: {o['Date of Delivery']}, Quantity: {o['Quantity']}"
                            for o in retrieved_orders
                        ])
                        
                        no_match_prompt = f"""
The user asked: "{user_input}"

Previously recommended Product IDs: {previously_recommended_product_ids}
User's order history shows they purchased products: {ordered_product_ids}
NO matches were found between recommended products and their actual orders.

Their actual order details:
{order_info}

Generate a friendly response (3-4 lines) that:
1. Starts with "No" to clearly state they haven't ordered the recommended products
2. Mentions what they actually ordered instead (product name and Product ID)
3. Provides the order details for transparency
4. Optionally suggests they might like the recommended products

Respond in JSON format:

{{
"chatbot_response": "No, you haven't ordered any of the products I recommended (P012, P016). However, you did order [Product Name] (Product ID: [PID]). Your order [Order ID] was [status]. Would you like to know more about the products I recommended?",
"orders": [all their orders here for reference]
}}
"""
                        response_json["chatbot_response"] = self.agent.run(no_match_prompt).content
                else:
                    # Regular order query - just show order details without comparison
                    order_info = "\n".join([
                    f"📦 Order #{o['Order ID']} - Product: {o['Product Name']} (Product ID: {o.get('Product ID', 'N/A')}), "
                    f"Customer: {o['Customer Name']}, Email: {o['Email ID']}, "
                    f"Ordered on: {o['Date of Order']}, Status: {o['Order Status']}, "
                    f"Delivery date: {o['Date of Delivery']}, Quantity: {o['Quantity']}"
                    for o in retrieved_orders
                ])
                logger.info(f"Order info: {order_info}")
                
                # Check if this is a comparison query
                is_comparison_query = any(phrase in user_input.lower() for phrase in [
                    "did i buy", "have i ordered", "purchased any", "bought any of these",
                    "ordered any of these", "have i bought", "did i order"
                ])
                
                if is_comparison_query and previously_recommended_product_ids:
                    # Compare Product IDs from their orders with recommended products
                    ordered_product_ids = [order.get('Product ID') for order in retrieved_orders if order.get('Product ID')]
                    matching_products = [pid for pid in previously_recommended_product_ids if pid in ordered_product_ids]
                    
                    logger.info(f"Previously recommended: {previously_recommended_product_ids}")
                    logger.info(f"User's ordered products: {ordered_product_ids}")
                    logger.info(f"Matches found: {matching_products}")
                    
                    if matching_products:
                        # Found matches
                        matched_orders = [order for order in retrieved_orders if order.get('Product ID') in matching_products]
                        
                        comparison_prompt = f"""
The user asked: "{user_input}"

Previously recommended Product IDs: {previously_recommended_product_ids}
User's order history (their orders only): {order_info}
Matching products: {matching_products}

Generate a friendly response (3-4 lines) that confirms they've purchased some of the recommended products and provides the order details.

Respond in JSON format with the matching orders:

{{
"chatbot_response": "Yes! I can see you've purchased some of the products I recommended...",
"orders": [...]
}}
"""
                        response_json["chatbot_response"] = self.agent.run(comparison_prompt).content
                    else:
                        # No matches - they haven't ordered the recommended products
                        response_json["chatbot_response"] = "Based on your order history, you haven't purchased any of the products I recommended yet. Would you like to know more about them?"
                        response_json["orders"] = []
                else:
                    # Regular order query - show their order details
                    order_retrieval_prompt = f"""
You have the following conversation history: {conversation_history}. Using that, once you've retrieved the order information: {order_info}
Based on {conversation_history} and {user_input}, give the best and most relevant responses from {order_info}.
- Always give complete info about the orders, including Product ID, status and delivery date.
- You will have to extract the order id (e.g, O1001, o1001), customer id (e.g, c001, C001) and other important fields from the user input

- You should give very human-like responses and need to be conversational.
- Given this information, generate a conversational response summarizing the order information for the user in 3-4 lines. *Do not hallucinate.*
If an order does not exist in the database, tell the user that politely.

- Respond in JSON format with a list of orders having the following structure (MUST include Product ID):

{{
"chatbot_response": "Here's the order information you requested:",
"orders": [
    {{
    "Order ID": "ORD12345",
    "Email ID": "customer@example.com",
    "Product Name": "Product 1",
    "Product ID": "P001",
    "Date of Order": "2025-04-01",
    "Order Status": "Delivered",
    "Date of Delivery": "2025-04-10",
    "Quantity": "1",
    "Customer ID": "CUST123",
    "Customer Name": "John Doe"
    }}
]
}}
"""
                    
                    response_json["chatbot_response"] = self.agent.run(order_retrieval_prompt).content
                    logger.info(f"Order retrieval response: {response_json['chatbot_response']}")
            else:
                # No orders found - likely missing Order ID or Email
                logger.info("No orders found - asking for Order ID or Email")
                
                # Check if this is a comparison query
                is_comparison_query = any(phrase in user_input.lower() for phrase in [
                    "did i buy", "have i ordered", "purchased any", "bought any of these",
                    "ordered any of these", "have i bought", "did i order"
                ])
                
                if is_comparison_query:
                    response_json["chatbot_response"] = "To check if you've ordered any of these products, I'll need to verify your identity for security reasons. Could you please provide your Order ID, email address, or full name?"
                elif response_json.get("send_invoice_email", False):
                    response_json["send_invoice_email"] = False
                    response_json["chatbot_response"] = "To send your invoice, I'll need your Order ID. Could you please provide it? (e.g., O1001)"
                else:
                    response_json["chatbot_response"] = "I'd be happy to help you with your order! For security reasons, could you please provide your Order ID (e.g., O1001), email address, or full name?"
        
        chatbot_response = response_json.get(
            "chatbot_response",
            "I'm sorry, I couldn't understand your request. Can you please clarify?"
        )
        
        # Process the response based on retrieval
        if response_json.get("run_retrieval_products", False) or response_json.get("run_retrieval_orders", False):
            cleaned_response = clean_chatbot_response(chatbot_response)
        else:
            cleaned_response = chatbot_response
        
        # Log product/order results
        if isinstance(cleaned_response, dict) and "products" in cleaned_response:
            logger.info(cleaned_response["chatbot_response"])
            logger.info(format_product_table(cleaned_response["products"]))
        
        if isinstance(cleaned_response, dict) and "orders" in cleaned_response:
            logger.info(cleaned_response["chatbot_response"])
            logger.info(format_order_table(cleaned_response["orders"]))
        
        # Only send invoice if we have order data
        send_invoice = response_json.get("send_invoice_email", False) and len(retrieved_orders) > 0
        
        return cleaned_response, send_invoice