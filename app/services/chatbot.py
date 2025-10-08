import logging
from typing import Dict, Any, Tuple, List
from app.utils.parsers import clean_and_parse_json, clean_chatbot_response
from app.utils.formatters import format_product_table, format_order_table

logger = logging.getLogger(__name__)

class ChatbotService:
    def __init__(self, agent, search_service):
        self.agent = agent
        self.search_service = search_service
    
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
        prompt = f"""
You are an Essilor chatbot, a company that provides expert advice on sunglasses and eyewear.
Maintain a professional yet friendly tone. Personalize responses based on the user's needs. *Do not hallucinate*. Respond to the user in 3-4 lines.
You should be able to answer basic trivia questions about glasses, about outfit choices that would match your products and other similar functions using your knowledge. Be creative.
*Do not repeat yourself when the user's query changes.*
You should be able to answer all kinds of questions about a product, including price, discount, more information, etc.
You can also answer questions about orders, including order status, delivery date, and other order-related information.

You need to extract the order id from user queries, the order id is of the form "o1001", "O1001" and product id is of the form "p001" or "P011"

If the user expresses that they want to get their invoice, follow these rules:
- If the order ID *is present* in the conversation history, set send_invoice_email: true and run_retrieval_orders: true
- When the user asks for an invoice, remember the conversation history when they provide their order ID.

If the user input can be answered from the conversation history, don't run retrieval.

Conversation History:
{conversation_history}

User: {user_input}

Before responding, determine if the user is asking about glasses/products or about orders.
When the user asks something about an order, set run_retrieval_orders = true. 
When the user asks for an invoice AND their order ID is NOT in conversation history, you need to ask the user for their order ID and set send_invoice_email=true AND run_retrieval_orders=true

Before responding, make sure that the product or order the user is looking for is actually in the database when run_retrieval_products or run_retrieval_orders = true. *Do not hallucinate*.

Return a JSON response in the *exact* format below:

{{
  "chatbot_response": "Your response here.",
  "run_retrieval_products": true or false,
  "run_retrieval_orders": true or false,
  "send_invoice_email": true or false
}}

If the user is asking about products (like styles, prices, specific glasses), set "run_retrieval_products": true.
If the user is asking about orders (like order status, delivery date, specific order ID), set "run_retrieval_orders": true.
If the user asks a general query about something like a fashion choice related to some particular glasses OR trivia questions, then set both to false.
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
            
            if retrieved_products:
                product_info = "\n".join([
                    f"🕶 {p['Product Name']} ({p['Brand Name']}) - Price: {p['Price']} INR, "
                    f"Discount: {p['Discount']}%, Suitable for: {p['Activity']}, "
                    f"Face Shape: {p['Face Shape']} \n🌄 Image: {p['Image URL']}, "
                    f"lens prescription type: {p['Prescription Type']}, "
                    f"frame color: {p['Frame Colour']}, lens color: {p['Lens Color']}"
                    for p in retrieved_products
                ])
                
                retrieval_prompt = f"""
You have the following conversation history: {conversation_history}. Using that, once you've retrieved the product {product_info}
Based on {conversation_history} and {user_input}, give the best and most relevant responses from {product_info}.
 - Always give the complete info about the products, also their price.
- You should give very human-like responses and need to be conversational.
- When you recommend a product to a user, you need to logically explain why you're recommending the product in 1-2 lines.
- Given this information, generate a conversational response summarizing the best product options for the user in 3-4 lines. *Do not hallucinate.*
If a product does not exist in the database, tell the user that and then give a similar product recommendation.

- Respond in JSON format with a list of products having the following structure:

{{
"chatbot_response": "Ok, I have found a few products for you:",
"products": [
    {{
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
            logger.info(f"Retrieved orders: {retrieved_orders}")
            
            if retrieved_orders:
                order_info = "\n".join([
                    f"📦 Order #{o['Order ID']} - Product: {o['Product Name']}, "
                    f"Customer: {o['Customer Name']}, Email: {o['Email ID']}, "
                    f"Ordered on: {o['Date of Order']}, Status: {o['Order Status']}, "
                    f"Delivery date: {o['Date of Delivery']}, Quantity: {o['Quantity']}"
                    for o in retrieved_orders
                ])
                logger.info(f"Order info: {order_info}")
                
                order_retrieval_prompt = f"""
You have the following conversation history: {conversation_history}. Using that, once you've retrieved the order information: {order_info}
Based on {conversation_history} and {user_input}, give the best and most relevant responses from {order_info}.
- Always give complete info about the orders, including status and delivery date.
- You will have to extract the order id (e.g, O1001, o1001), customer id (e.g, c001, C001) and other important fields from the user input

- You should give very human-like responses and need to be conversational.
- Given this information, generate a conversational response summarizing the order information for the user in 3-4 lines. *Do not hallucinate.*
If an order does not exist in the database, tell the user that politely.

- Respond in JSON format with a list of orders having the following structure:

{{
"chatbot_response": "Here's the order information you requested:",
"orders": [
    {{
    "Order ID": "ORD12345",
    "Email ID": "customer@example.com",
    "Product Name": "Product 1",
    "Date of Order": "2025-04-01",
    "Order Status": "Delivered",
    "Date of Delivery": "2025-04-10",
    "Quantity": "1",
    "Customer ID": "CUST123",
    "Product ID": "PROD456",
    "Customer Name": "John Doe"
    }}
]
}}
"""
                
                response_json["chatbot_response"] = self.agent.run(order_retrieval_prompt).content
                logger.info(f"Order retrieval response: {response_json['chatbot_response']}")
            else:
                # If no orders found but invoice was requested
                if response_json.get("send_invoice_email", False):
                    invoice_error_prompt = """
Ask the user politely for their order ID.
Keep the response conversational and helpful in 3-4 lines.
"""
                    response_json["chatbot_response"] = self.agent.run(invoice_error_prompt).content
                    response_json["send_invoice_email"] = False
                    logger.info("Order retrieval for invoice sending failed - no orders found")
        
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
