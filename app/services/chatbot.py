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
            import re
            direct_matches = re.findall(r'\bP\d{3,4}\b', conversation_history)
            product_ids.extend(direct_matches)
            json_matches = re.findall(r'["\']?Product ID["\']?\s*:\s*["\']?(P\d{3,4})["\']?', conversation_history)
            product_ids.extend(json_matches)
            dict_matches = re.findall(r"'Product ID':\s*'(P\d{3,4})'", conversation_history)
            product_ids.extend(dict_matches)
            logger.info(f"📋 Extracted Product IDs from history: {list(set(product_ids))}")
        except Exception as e:
            logger.error(f"Error extracting product IDs from history: {e}")
        return list(set(product_ids))
    
    def _extract_product_ids_from_messages(self, conversation_history_list: List[Dict]) -> List[str]:
        """Extract Product IDs directly from conversation message objects."""
        product_ids = []
        try:
            for message in conversation_history_list:
                if message.get('role') == 'bot' and message.get('table'):
                    products = message.get('table', [])
                    for product in products:
                        if isinstance(product, dict) and 'Product ID' in product:
                            product_ids.append(product['Product ID'])
            logger.info(f"📋 Extracted Product IDs from message objects: {list(set(product_ids))}")
        except Exception as e:
            logger.error(f"Error extracting product IDs from messages: {e}")
        return list(set(product_ids))
    
    def _extract_order_id_from_input(self, user_input: str, conversation_history: str) -> str:
        """Extract Order ID from user input or conversation history."""
        import re
        matches = re.findall(r'\b[Oo]\d{4,}\b', user_input + " " + conversation_history)
        return matches[0] if matches else None
    
    def _is_comparison_query_in_history(self, conversation_history: str, user_input: str) -> bool:
        """Check if THIS conversation has a comparison query."""
        comparison_phrases = [
            "did i buy", "have i ordered", "purchased any", "bought any of these",
            "ordered any of these", "have i bought", "did i order", "buy these",
            "ordered these", "purchase these", "bought these", "buy any of these",
            "did i purchase", "have i purchased"
        ]
        
        if any(phrase in user_input.lower() for phrase in comparison_phrases):
            return True
        
        import re
        user_messages = re.findall(r'User:\s*([^\n]+)', conversation_history)
        recent_messages = user_messages[-3:] if len(user_messages) >= 3 else user_messages
        
        for msg in recent_messages:
            if any(phrase in msg.lower() for phrase in comparison_phrases):
                return True
        return False
    
    def _ensure_complete_order_data(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure all order records have complete required fields.
        Fill missing fields with 'N/A' to prevent null entries.
        """
        required_fields = [
            'Order ID', 'Date of Order', 'Order Status', 'Date of Delivery',
            'Quantity', 'Product Name', 'Customer Name', 'Email ID',
            'Customer ID', 'Product ID'
        ]
        
        complete_orders = []
        for order in orders:
            complete_order = {}
            for field in required_fields:
                complete_order[field] = order.get(field, 'N/A')
            complete_orders.append(complete_order)
        
        return complete_orders
    
    def process_message(
        self,
        user_input: str,
        conversation_history: str,
        conversation_history_list: List[Dict] = None
    ) -> Tuple[Any, bool]:
        """Process user message and generate response."""
        
        if conversation_history_list:
            previously_recommended_product_ids = self._extract_product_ids_from_messages(conversation_history_list)
        else:
            previously_recommended_product_ids = self._extract_product_ids_from_history(conversation_history)
        
        order_id_present = self._extract_order_id_from_input(user_input, conversation_history)
        is_comparison = self._is_comparison_query_in_history(conversation_history, user_input)
        
        logger.info(f"🔍 Comparison check: is_comparison={is_comparison}, recommended_products={previously_recommended_product_ids}, order_id={order_id_present}")
        
        if is_comparison and previously_recommended_product_ids and not order_id_present:
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
- For SPECIFIC requests: Set run_retrieval_products=true IMMEDIATELY
- For vague queries: Set false and ask clarifying questions

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

Respond in JSON format with products array.
"""
                
                response_json["chatbot_response"] = self.agent.run(retrieval_prompt).content
        
        # Process order retrieval
        if response_json.get("run_retrieval_orders", False):
            retrieved_orders = self.search_service.search_orders(conversation_history, user_input)
            logger.info(f"Retrieved orders count: {len(retrieved_orders)}")
            
            # CRITICAL FIX: Ensure complete order data
            retrieved_orders = self._ensure_complete_order_data(retrieved_orders)
            logger.info(f"✅ Orders after ensuring complete data: {retrieved_orders}")
            
            if retrieved_orders:
                logger.info(f"🔍 DECISION POINT: is_comparison={is_comparison}, has_recommended_products={bool(previously_recommended_product_ids)}")
                
                if is_comparison and previously_recommended_product_ids:
                    logger.info(f"🔥 COMPARISON MODE ACTIVATED")
                    logger.info(f"Recommended Product IDs: {previously_recommended_product_ids}")
                    
                    ordered_product_ids = [order.get('Product ID') for order in retrieved_orders if order.get('Product ID') and order.get('Product ID') != 'N/A']
                    matching_products = [pid for pid in previously_recommended_product_ids if pid in ordered_product_ids]
                    
                    logger.info(f"User's ordered Product IDs: {ordered_product_ids}")
                    logger.info(f"🎯 Matches found (recommended AND ordered): {matching_products}")
                    
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
The user asked: "Did I buy any of these before?"
Then provided Order ID: {order_id_present}

Previously recommended Product IDs: {previously_recommended_product_ids}
User's order history shows Product IDs: {ordered_product_ids}
MATCHES FOUND: {matching_products}

Matching order details:
{order_details}

Generate a friendly response (3-4 lines) that:
1. STARTS WITH "Yes!" to confirm they ordered recommended products
2. Mentions product name and Product ID
3. Provides Order ID, status, and dates
4. Sounds natural

Respond in JSON with complete order details:
{{
"chatbot_response": "Your YES response",
"orders": [
    {{
    "Order ID": "O1001",
    "Date of Order": "15/04/25",
    "Order Status": "Delivered",
    "Date of Delivery": "20/04/25",
    "Quantity": "1",
    "Product Name": "Product Name",
    "Customer Name": "Customer Name",
    "Email ID": "email@example.com",
    "Product ID": "P001",
    "Customer ID": "C001"
    }}
]
}}

CRITICAL: Include ALL order fields in the response, not just chatbot_response.
"""
                        comparison_result = self.agent.run(comparison_prompt).content
                        parsed_result = clean_chatbot_response(comparison_result)
                        
                        if isinstance(parsed_result, dict):
                            response_json["chatbot_response"] = parsed_result.get("chatbot_response", "Yes! You ordered some of the recommended products.")
                            # Use matched_orders to ensure we have complete data
                            response_json["orders"] = parsed_result.get("orders", matched_orders)
                        else:
                            response_json["chatbot_response"] = comparison_result
                            response_json["orders"] = matched_orders
                    else:
                        # NO - user did NOT order recommended products
                        all_order_details = "\n".join([
                            f"- {o['Product Name']} (Product ID: {o['Product ID']})\n"
                            f"  Order #{o['Order ID']}, Status: {o['Order Status']}, "
                            f"Ordered: {o['Date of Order']}, Delivered: {o['Date of Delivery']}"
                            for o in retrieved_orders[:3]
                        ])
                        
                        no_match_prompt = f"""
The user asked: "Did I buy any of these before?"
Then provided Order ID: {order_id_present}

Previously recommended Product IDs: {previously_recommended_product_ids}
User's actual order history Product IDs: {ordered_product_ids}
NO MATCHES - they didn't order any recommended products

Their actual orders:
{all_order_details}

Generate a friendly response (3-4 lines) that:
1. STARTS WITH "No" or "No, you haven't" to clearly state they didn't order recommended products
2. Mentions what they actually ordered (product name and Product ID)
3. Provides their Order ID and order status
4. Optionally offers more info about recommended products

Example: "No, you haven't ordered the Silver Full Rim Clubmaster or Gray Transparent Full Rim Aviator that I recommended. However, you did order the Gray Full Rim Round which was delivered on April 19th. Would you like to know more about my other recommendations?"


Respond in JSON with complete order details:
{{
"chatbot_response": "Your friendly response starting with NO",
"orders": [their actual orders for reference]
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

Respond in JSON with ALL order fields:
{{
"chatbot_response": "Your response",
"orders": [complete order objects with all fields]
}}
"""
                    
                    order_result = self.agent.run(order_retrieval_prompt).content
                    parsed_result = clean_chatbot_response(order_result)
                    
                    if isinstance(parsed_result, dict):
                        response_json["chatbot_response"] = parsed_result.get("chatbot_response", "Here's your order information:")
                        response_json["orders"] = parsed_result.get("orders", retrieved_orders)
                    else:
                        response_json["chatbot_response"] = order_result
                        response_json["orders"] = retrieved_orders
            else:
                # No orders found
                logger.warning("No orders found")
                
                import re
                order_id_match = re.search(r'\b[Oo]\d{4,}\b', user_input + " " + conversation_history)
                provided_order_id = order_id_match.group(0) if order_id_match else None
                
                if is_comparison:
                    if provided_order_id:
                        response_json["chatbot_response"] = f"I couldn't find any orders with Order ID {provided_order_id}. Please double-check your Order ID (format: O1001)."
                    else:
                        response_json["chatbot_response"] = "To check if you've ordered these products, please provide your Order ID, email, or full name."
                elif response_json.get("send_invoice_email", False):
                    response_json["send_invoice_email"] = False
                    if provided_order_id:
                        response_json["chatbot_response"] = f"I couldn't find any orders with Order ID {provided_order_id}. Please verify your Order ID."
                    else:
                        response_json["chatbot_response"] = "To send your invoice, I need your Order ID (e.g., O1001)."
                else:
                    if provided_order_id:
                        response_json["chatbot_response"] = f"I couldn't find any orders with Order ID {provided_order_id}. Please check if the Order ID is correct."
                    else:
                        response_json["chatbot_response"] = "Please provide your Order ID, email, or full name to look up your order."
        
        chatbot_response = response_json.get(
            "chatbot_response",
            "I'm sorry, I couldn't understand your request."
        )
        
        # Clean response
        if response_json.get("run_retrieval_products", False) or response_json.get("run_retrieval_orders", False):
            cleaned_response = clean_chatbot_response(chatbot_response)
            
            # CRITICAL: Ensure cleaned_response is always a dict structure
            if not isinstance(cleaned_response, dict):
                cleaned_response = {
                    "chatbot_response": str(cleaned_response),
                    "products": retrieved_products,
                    "orders": retrieved_orders
                }
            else:
                # Ensure products and orders are in the response
                if "products" not in cleaned_response:
                    cleaned_response["products"] = retrieved_products
                if "orders" not in cleaned_response:
                    cleaned_response["orders"] = retrieved_orders
        else:
            cleaned_response = {
                "chatbot_response": chatbot_response,
                "products": [],
                "orders": []
            }
        
        # Log results
        if isinstance(cleaned_response, dict):
            if "products" in cleaned_response:
                logger.info(cleaned_response.get("chatbot_response", "Response generated"))
                logger.info(format_product_table(cleaned_response["products"]))
            
            if "orders" in cleaned_response:
                logger.info(cleaned_response.get("chatbot_response", "Response generated"))
                logger.info(format_order_table(cleaned_response["orders"]))
        else:
            # If cleaned_response is a string, log it directly
            logger.info(f"Response: {cleaned_response}")
        
        send_invoice = response_json.get("send_invoice_email", False) and len(retrieved_orders) > 0
        
        return cleaned_response, send_invoice