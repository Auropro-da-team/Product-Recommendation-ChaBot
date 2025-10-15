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
            if "Product ID" in conversation_history:
                import re
                matches = re.findall(r"['\"]?Product ID['\"]?\s*:\s*['\"]?(P\d+)['\"]?", conversation_history)
                product_ids.extend(matches)
        except Exception as e:
            logger.error(f"Error extracting product IDs from history: {e}")
        return list(set(product_ids))
    
    def _extract_order_id_from_input(self, user_input: str, conversation_history: str) -> str:
        """Extract Order ID from user input or conversation history."""
        import re
        matches = re.findall(r'\b[Oo]\d{4,}\b', user_input + " " + conversation_history)
        return matches[0] if matches else None
    
    def _is_comparison_query_in_history(self, conversation_history: str, user_input: str) -> bool:
        """
        Check if THIS conversation has a comparison query.
        Look at recent user messages (last 3-4 exchanges).
        """
        comparison_phrases = [
            "did i buy", "have i ordered", "purchased any", "bought any of these",
            "ordered any of these", "have i bought", "did i order", "buy these",
            "ordered these", "purchase these", "bought these", "buy any of these"
        ]
        
        # Check current input
        if any(phrase in user_input.lower() for phrase in comparison_phrases):
            return True
        
        # Check last few user messages in history
        import re
        user_messages = re.findall(r'User:\s*([^\n]+)', conversation_history)
        # Check last 3 user messages
        recent_messages = user_messages[-3:] if len(user_messages) >= 3 else user_messages
        
        for msg in recent_messages:
            if any(phrase in msg.lower() for phrase in comparison_phrases):
                return True
        
        return False
    
    def process_message(
        self,
        user_input: str,
        conversation_history: str
    ) -> Tuple[Any, bool]:
        """Process user message and generate response."""
        
        previously_recommended_product_ids = self._extract_product_ids_from_history(conversation_history)
        order_id_present = self._extract_order_id_from_input(user_input, conversation_history)
        
        # CRITICAL FIX: Check conversation history for comparison intent
        is_comparison = self._is_comparison_query_in_history(conversation_history, user_input)
        
        logger.info(f"🔍 Comparison check: is_comparison={is_comparison}, recommended_products={previously_recommended_product_ids}, order_id={order_id_present}")
        
        # If it's a comparison query but no Order ID yet, ask for it
        if is_comparison and previously_recommended_product_ids and not order_id_present:
            # Check if user JUST asked the comparison question (not a follow-up)
            comparison_phrases = [
                "did i buy", "have i ordered", "purchased any", "bought any of these",
                "ordered any of these", "have i bought", "did i order", "buy these"
            ]
            user_just_asked_comparison = any(phrase in user_input.lower() for phrase in comparison_phrases)
            
            if user_just_asked_comparison:
                return {
                    "chatbot_response": "To check if you've ordered any of these products, I'll need to verify your identity for security. Could you please provide your Order ID (e.g., O1001), email address, or full name?",
                    "products": [],
                    "orders": []
                }, False
        
        prompt = f"""
You are an Essilor chatbot for sunglasses and eyewear advice.
Maintain a professional yet friendly tone. Respond in 3-4 lines. *Do not hallucinate*.

CONTEXT ANALYSIS:
- Previously recommended Product IDs: {previously_recommended_product_ids if previously_recommended_product_ids else "None"}
- Order ID detected: {order_id_present if order_id_present else "None"}
- Is this part of a comparison query: {is_comparison}

CRITICAL: If is_comparison=True AND previously_recommended_product_ids exist AND order_id_present exists:
This is a COMPARISON scenario - user wants to know if they ordered the recommended products.
Set run_retrieval_orders=true so we can compare their orders against recommendations.

ORDER RETRIEVAL RULES (SECURITY):
- run_retrieval_orders should be true when:
  1. Order ID is present (like O1001), OR
  2. Email address is present, OR  
  3. Customer Name is present
- For queries WITHOUT identifier: Set run_retrieval_orders=false and ask for Order ID/Email/Name

INVOICE RULES:
- If user wants invoice AND order ID is present: Set send_invoice_email=true AND run_retrieval_orders=true

Conversation History:
{conversation_history}

User: {user_input}

PRODUCT RETRIEVAL RULES:
- For SPECIFIC requests ("Recommend 4 glasses for trek", "sunglasses under 2000"): Set run_retrieval_products=true IMMEDIATELY
- For vague queries without criteria: Set false and ask clarifying questions

Return JSON:

{{
  "chatbot_response": "Your response here.",
  "run_retrieval_products": true or false,
  "run_retrieval_orders": true or false,
  "send_invoice_email": true or false
}}
"""
        
        raw_response = self.agent.run(prompt).content
        logger.info(f"Raw agent response: {raw_response}")
        response_json = clean_and_parse_json(raw_response)
        logger.info(f"Parsed response: {response_json}")
        
        # Ensure invoice requires order retrieval
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
                    f"Discount: {p['Discount']}%, Suitable for: {p['Activity']}, Face Shape: {p['Face Shape']}, "
                    f"Image: {p['Image URL']}, Prescription: {p['Prescription Type']}, "
                    f"Frame: {p['Frame Colour']}, Lens: {p['Lens Color']}"
                    for p in retrieved_products
                ])
                
                retrieval_prompt = f"""
Conversation history: {conversation_history}
User query: {user_input}
Retrieved products: {product_info}

Generate a conversational response (3-4 lines) recommending the best products with logical explanations.
Always include complete info: Product ID, price, discount, and why it's suitable.

Respond in JSON format:

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
                # CRITICAL FIX: Check if comparison based on conversation history
                logger.info(f"🔍 DECISION POINT: is_comparison={is_comparison}, has_recommended_products={bool(previously_recommended_product_ids)}")
                
                if is_comparison and previously_recommended_product_ids:
                    logger.info(f"🔥 COMPARISON MODE ACTIVATED")
                    logger.info(f"Recommended Product IDs: {previously_recommended_product_ids}")
                    
                    ordered_product_ids = [order.get('Product ID') for order in retrieved_orders if order.get('Product ID')]
                    matching_products = [pid for pid in previously_recommended_product_ids if pid in ordered_product_ids]
                    
                    logger.info(f"User's ordered Product IDs: {ordered_product_ids}")
                    logger.info(f"Matches found: {matching_products}")
                    
                    if matching_products:
                        # YES - user ordered some recommended products
                        matched_orders = [order for order in retrieved_orders if order.get('Product ID') in matching_products]
                        
                        order_details = "\n".join([
                            f"- {o['Product Name']} (Product ID: {o['Product ID']})\n"
                            f"  Order #{o['Order ID']}, Status: {o['Order Status']}, "
                            f"Ordered: {o['Date of Order']}, Delivery: {o['Date of Delivery']}, Quantity: {o['Quantity']}"
                            for o in matched_orders
                        ])
                        
                        comparison_prompt = f"""
The user originally asked: "Did I order any of these earlier?" referring to products I recommended.

RECOMMENDED PRODUCTS (what I suggested): {previously_recommended_product_ids}
ACTUAL ORDERED PRODUCTS (what they bought): {ordered_product_ids}

RESULT: MATCH FOUND! Product IDs {matching_products} appear in BOTH lists.

Matching order details:
{order_details}

Generate a friendly, conversational response (3-4 lines) that:
1. STARTS WITH "Yes!" or "Yes, you did!" to clearly confirm they DID order the recommended product(s)
2. Be specific about which recommended product they ordered
3. Provide Order ID, order status, delivery date, and quantity
4. Sound natural and helpful

Example: "Yes! You ordered the Gray Full Rim Round (Product ID: P040) that I recommended. Your order O1002 was placed on April 15th and delivered on April 19th. You ordered 2 units."

CRITICAL RULES:
- Only mention products that are in the MATCHING list: {matching_products}
- Return ALL order fields including Order ID, Date of Order, Order Status, Date of Delivery, Quantity, Product Name, Customer Name, Email ID, Customer ID, and Product ID

Respond in JSON:
{{
"chatbot_response": "Your friendly confirmation starting with YES",
"orders": [
    {{
    "Order ID": "O1002",
    "Date of Order": "2025-04-15",
    "Order Status": "Delivered",
    "Date of Delivery": "2025-04-19",
    "Quantity": "2",
    "Product Name": "Gray Full Rim Round",
    "Customer Name": "John Doe",
    "Email ID": "customer@example.com",
    "Customer ID": "CUST123",
    "Product ID": "P040"
    }}
]
}}
"""
                        response_json["chatbot_response"] = self.agent.run(comparison_prompt).content
                    else:
                        # NO - user did NOT order recommended products
                        all_order_details = "\n".join([
                            f"- {o['Product Name']} (Product ID: {o['Product ID']})\n"
                            f"  Order #{o['Order ID']}, Status: {o['Order Status']}, Date: {o['Date of Order']}"
                            for o in retrieved_orders[:3]
                        ])
                        
                        no_match_prompt = f"""
The user originally asked: "Did I order any of these earlier?" referring to products I recommended.

RECOMMENDED PRODUCTS (what I suggested): {previously_recommended_product_ids}
ACTUAL ORDERED PRODUCTS (what they bought): {ordered_product_ids}

RESULT: NO MATCH - The user did NOT order any of the products I recommended.

Their actual order history (different products):
{all_order_details}

Generate a friendly response (3-4 lines) that:
1. STARTS WITH "No, you haven't ordered" to clearly state they didn't order the RECOMMENDED products
2. Be specific: "You haven't ordered the Gray Full Rim Round (P040) or Black Full Rim Clubmaster (P025) that I recommended."
3. Then mention what they ACTUALLY ordered: "However, you did order the Light Gunmetal Full Rim Aviator (Product ID: P017) which was delivered on April 25th."
4. Optionally ask if they want more info about the recommended products

CRITICAL RULES:
- Do NOT say they didn't order something if it's in their order history
- Be clear about the distinction between RECOMMENDED products vs ACTUALLY ORDERED products
- Return ALL order fields including Order ID, Date of Order, Order Status, Date of Delivery, Quantity, Product Name, Customer Name, Email ID, Customer ID, and Product ID

Example response:
"No, you haven't ordered the Gray Full Rim Round (P040) or Black Full Rim Clubmaster (P025) that I recommended. However, according to your order history, you previously ordered the Light Gunmetal Full Rim Aviator (Product ID: P017) on April 15th, which was delivered on April 25th. Would you like to know more about my recommended products?"

Respond in JSON:
{{
"chatbot_response": "Your clear, accurate response",
"orders": [
    {{
    "Order ID": "O1001",
    "Date of Order": "2025-04-15",
    "Order Status": "Delivered",
    "Date of Delivery": "2025-04-25",
    "Quantity": "1",
    "Product Name": "Light Gunmetal Full Rim Aviator",
    "Customer Name": "John Doe",
    "Email ID": "likith@example.com",
    "Customer ID": "CUST001",
    "Product ID": "P017"
    }}
]
}}
"""
                        response_json["chatbot_response"] = self.agent.run(no_match_prompt).content
                else:
                    # Regular order query (not comparison)
                    logger.info("📦 REGULAR ORDER QUERY MODE (not comparison)")
                    
                    order_info = "\n".join([
                        f"📦 Order #{o['Order ID']} - Product: {o['Product Name']} (Product ID: {o.get('Product ID', 'N/A')}), "
                        f"Customer: {o['Customer Name']}, Email: {o['Email ID']}, "
                        f"Ordered: {o['Date of Order']}, Status: {o['Order Status']}, "
                        f"Delivery: {o['Date of Delivery']}, Qty: {o['Quantity']}"
                        for o in retrieved_orders
                    ])
                    
                    order_retrieval_prompt = f"""
Conversation history: {conversation_history}
User query: {user_input}
Retrieved orders: {order_info}

Generate a conversational response (3-4 lines) summarizing order information.
Include Product ID, Order ID, status, and delivery date.
Be natural and helpful.

CRITICAL: Return ALL order fields in the response including Order ID, Date of Order, Order Status, Date of Delivery, Quantity, Product Name, Customer Name, Email ID, Customer ID, and Product ID.

Respond in JSON:
{{
"chatbot_response": "Here's your order information:",
"orders": [
    {{
    "Order ID": "O1010",
    "Date of Order": "2025-04-01",
    "Order Status": "Delivered",
    "Date of Delivery": "2025-04-10",
    "Quantity": "1",
    "Product Name": "Product 1",
    "Customer Name": "John Doe",
    "Email ID": "customer@example.com",
    "Customer ID": "CUST123",
    "Product ID": "P001"
    }}
]
}}
"""
                    
                    response_json["chatbot_response"] = self.agent.run(order_retrieval_prompt).content
                    logger.info(f"Order retrieval response: {response_json['chatbot_response']}")
            else:
                # No orders found
                logger.warning("No orders found - likely incorrect Order ID or missing identifier")
                
                import re
                order_id_match = re.search(r'\b[Oo]\d{4,}\b', user_input + " " + conversation_history)
                provided_order_id = order_id_match.group(0) if order_id_match else None
                
                if is_comparison:
                    if provided_order_id:
                        response_json["chatbot_response"] = f"I couldn't find any orders with Order ID {provided_order_id}. Please double-check your Order ID (format: O1001)."
                    else:
                        response_json["chatbot_response"] = "To check if you've ordered these products, please provide your Order ID, email, or full name for security."
                elif response_json.get("send_invoice_email", False):
                    response_json["send_invoice_email"] = False
                    if provided_order_id:
                        response_json["chatbot_response"] = f"I couldn't find any orders with Order ID {provided_order_id}. Please verify your Order ID (format: O1001)."
                    else:
                        response_json["chatbot_response"] = "To send your invoice, I need your Order ID (e.g., O1001). Could you provide it?"
                else:
                    if provided_order_id:
                        response_json["chatbot_response"] = f"I couldn't find any orders with Order ID {provided_order_id}. Please check if the Order ID is correct (format: O1001)."
                    else:
                        response_json["chatbot_response"] = "I'd be happy to help with your order! Please provide your Order ID (e.g., O1001), email, or full name for security."
        
        chatbot_response = response_json.get(
            "chatbot_response",
            "I'm sorry, I couldn't understand your request. Can you please clarify?"
        )
        
        # Clean response
        if response_json.get("run_retrieval_products", False) or response_json.get("run_retrieval_orders", False):
            cleaned_response = clean_chatbot_response(chatbot_response)
        else:
            cleaned_response = chatbot_response
        
        # Log results
        if isinstance(cleaned_response, dict) and "products" in cleaned_response:
            logger.info(cleaned_response["chatbot_response"])
            logger.info(format_product_table(cleaned_response["products"]))
        
        if isinstance(cleaned_response, dict) and "orders" in cleaned_response:
            logger.info(cleaned_response["chatbot_response"])
            logger.info(format_order_table(cleaned_response["orders"]))
        
        # Only send invoice if we have order data
        send_invoice = response_json.get("send_invoice_email", False) and len(retrieved_orders) > 0
        
        return cleaned_response, send_invoice