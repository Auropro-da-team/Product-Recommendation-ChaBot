import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Body, File, UploadFile, Form
from google.cloud import storage
from app.models.schemas import ChatRequest, ChatResponse
from app.dependencies import get_dependencies
from app.config import settings
from app.utils.parsers import clean_chatbot_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat/{session_id}/{conversation_id}", response_model=ChatResponse)
async def chat(
    session_id: str,
    conversation_id: str,
    user_input: str = Body(..., embed=True)
):
    """Handle text-based chat messages."""
    if not session_id or not conversation_id or not user_input.strip():
        raise HTTPException(
            status_code=400,
            detail="Session ID, Conversation ID, and user input are required"
        )
    
    try:
        deps = get_dependencies()
        logger.info(f"🔥 Received input: {user_input} (Session: {session_id}, Conversation: {conversation_id})")
        
        # Retrieve conversation history
        conversation_history = deps.firestore_db.get_conversation_history(
            session_id,
            conversation_id
        )
        
        # Format conversation history - INCLUDE Product ID
        formatted_history = ''.join([
            f"{m['role'].capitalize()}: {m['content']}\n"
            + (f"Products: {m.get('table', [])}\n" if m.get('table') else "")
            + (f"Orders: {m.get('orders_table', [])}\n" if m.get('orders_table') else "")
            for m in conversation_history
        ])
        
        # Store user message
        conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Generate AI response
        response, send_invoice = deps.chatbot_service.process_message(
            user_input,
            formatted_history,
            conversation_history  # Pass the actual list
        )
        
        # CRITICAL FIX: Handle response properly - it's already processed by chatbot service
        if isinstance(response, dict):
            # Response is already a structured dict from chatbot service
            chatbot_response = response.get(
                "chatbot_response",
                "I'm sorry, I couldn't understand your request."
            )
            products = response.get("products", [])
            orders = response.get("orders", [])
        elif isinstance(response, str):
            # Response is a plain string
            chatbot_response = response
            products = []
            orders = []
        else:
            # Unexpected response type
            logger.error(f"Unexpected response type: {type(response)}")
            chatbot_response = "I'm sorry, I couldn't process your request properly. Please try again."
            products = []
            orders = []
        
        # Send invoice email if requested
        if send_invoice and orders:
            try:
                deps.email_service.send_invoice_email(orders[0]['Email ID'], orders[0])
                chatbot_response += "\n An invoice email has been sent to your email address."
            except Exception as email_err:
                logger.error(f"Error sending invoice email: {str(email_err)}")
                chatbot_response += "\n There was an error sending the invoice email."
        
        # Store bot response with Product IDs
        conversation_history.append({
            "role": "bot",
            "content": chatbot_response,
            "table": products,
            "orders_table": orders,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Save conversation
        deps.firestore_db.save_conversation(
            session_id,
            conversation_id,
            conversation_history
        )
        
        return ChatResponse(
            response=chatbot_response,
            products=products,
            orders=orders,
            conversation_id=conversation_id,
            session_id=session_id
        )
    
    except Exception as e:
        logger.exception("🚨 Error processing chat request.")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/{session_id}/{conversation_id}/with-image")
async def chat_with_image(
    session_id: str,
    conversation_id: str,
    file: UploadFile = File(...),
    user_input: str = Form(...)
):
    """Handle chat messages with image uploads."""
    if not session_id or not conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID and Conversation ID are required"
        )
    
    try:
        deps = get_dependencies()
        logger.info(f"🔥 Received input with image: {user_input} (Session: {session_id}, Conversation: {conversation_id})")
        
        # Retrieve conversation history
        conversation_history = deps.firestore_db.get_conversation_history(
            session_id,
            conversation_id
        )
        
        # Format conversation history
        formatted_history = ''.join([
            f"{m['role'].capitalize()}: {m['content']}\n"
            for m in conversation_history
        ])
        
        # Read uploaded file
        contents = await file.read()
        
        # Store image in GCS
        image_url = None
        image_id = None
        try:
            image_id = str(uuid.uuid4())
            bucket_name = settings.GCS_IMAGE_BUCKET_NAME
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            blob_name = f"user_uploads/{session_id}/{image_id}.jpg"
            blob = bucket.blob(blob_name)
            blob.upload_from_string(contents, content_type=file.content_type)
            
            # Save metadata
            deps.firestore_db.save_image_metadata(
                image_id,
                session_id,
                conversation_id,
                blob_name,
                file.filename,
                file.content_type
            )
            
            image_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
            logger.info(f"✅ Image uploaded to GCS: {image_url}")
        except Exception as e:
            logger.error(f"Failed to store image: {e}")
        
        # Perform image search
        initial_results, message = deps.image_search_service.search_by_image(
            contents,
            top_k=4
        )
        
        if not initial_results:
            chatbot_response = f"I couldn't find any products similar to the image you uploaded. {message}"
            products = []
        else:
            # Create hybrid prompt with image search results
            product_info = "\n".join([
                f"🕶️ Product ID: {p.get('Product ID')}, {p['Product Name']} ({p['Brand Name']}) - Price: {p['Price']}, "
                f"Discount: {p['Discount']}, Suitable for: {p['Activity']}, "
                f"Face Shape: {p['Face Shape']} \n🌄 Image: {p['Image URL']}, "
                f"frame color: {p['Frame Colour']}, lens color: {p['Lens Color']}"
                for p in initial_results[:3]
            ])
            
            hybrid_prompt = f"""
The user uploaded an image of glasses and also provided this message: "{user_input}"

Here are the products most visually similar to their image:
{product_info}

Please analyze both the image search results and their text query to provide a helpful response.
If they're asking for modifications (like different color, shape, price range) to what they uploaded,
recommend the most appropriate products from the list above.

CRITICAL: When returning products, you MUST preserve the EXACT discount values from the search results above.
DO NOT change or recalculate discount values. Use them exactly as provided.

Return a JSON response in this exact format:

{{
  "chatbot_response": "Your helpful response here explaining your recommendations",
  "products": [
    {{
      "Product ID": "P001",
      "Product Name": "Product 1",
      "Price": 1000,
      "Brand Name": "Brand A",
      "Discount": "10.50%",
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

IMPORTANT: 
1. Copy the discount values EXACTLY as shown in the search results above
2. Keep all other product details exactly as provided
3. Only recommend products from the list above
4. Do not invent or modify any product information
"""
                            
            try:
                # Get AI response for hybrid search
                response = deps.agent.run(hybrid_prompt).content
                cleaned_response = clean_chatbot_response(response)
                
                if isinstance(cleaned_response, dict):
                    chatbot_response = cleaned_response.get(
                        "chatbot_response",
                        "I found some products similar to your image."
                    )
                    
                    # CRITICAL FIX: Merge AI response with original search results to preserve discount
                    ai_products = cleaned_response.get("products", [])
                    
                    # Create a mapping of Product ID to original product data
                    original_products_map = {p.get('Product ID'): p for p in initial_results[:3]}
                    
                    # Merge: use AI-selected products but preserve original discount values
                    final_products = []
                    for ai_prod in ai_products:
                        prod_id = ai_prod.get('Product ID')
                        if prod_id in original_products_map:
                            # Use original product data to ensure discount is correct
                            original = original_products_map[prod_id]
                            # Keep AI's response but override with original discount
                            merged_product = {**ai_prod, 'Discount': original['Discount']}
                            final_products.append(merged_product)
                        else:
                            # Fallback: use AI product as-is
                            final_products.append(ai_prod)
                    
                    products = final_products if final_products else initial_results[:3]
                    
                    logger.info(f"✅ Final products after discount preservation: {products}")
                else:
                    chatbot_response = "I found some glasses similar to your image, but I'm not sure if they match your other requirements."
                    products = initial_results[:3]
            except Exception as e:
                logger.error(f"Error processing hybrid search: {e}")
                chatbot_response = "I found some products similar to your image."
                products = initial_results[:3]
        
        # Store user message with image metadata
        conversation_history.append({
            "role": "user",
            "content": f"[Image uploaded] {user_input}",
            "timestamp": datetime.utcnow().isoformat(),
            "has_image": True,
            "image_url": image_url,
            "image_id": image_id
        })
        
        # Store bot response
        conversation_history.append({
            "role": "bot",
            "content": chatbot_response,
            "table": products,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Save conversation to Firestore
        deps.firestore_db.save_conversation(
            session_id,
            conversation_id,
            conversation_history
        )
        
        logger.info(f"✅ Image search completed for {session_id}/{conversation_id}")
        
        return {
            "response": chatbot_response,
            "products": products,
            "orders": [],
            "conversation_id": conversation_id,
            "session_id": session_id,
            "image_url": image_url
        }
    
    except Exception as e:
        logger.exception("🚨 Error processing chat with image request.")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_id}/{conversation_id}")
async def get_chat(session_id: str, conversation_id: str):
    """Get conversation history."""
    try:
        deps = get_dependencies()
        data = deps.firestore_db.get_chat(session_id, conversation_id)
        logger.info(f"✅ Retrieved chat history for {session_id}/{conversation_id}")
        return data
    except Exception as e:
        logger.exception("🚨 Error fetching chat history.")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_id}/get_conversation")
async def get_conversation(session_id: str):
    """Get conversation ID for a session."""
    try:
        deps = get_dependencies()
        conversation_id = deps.firestore_db.get_conversation_id(session_id)
        return {"conversation_id": conversation_id}
    except Exception as e:
        logger.exception("🚨 Error getting conversation ID.")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/{session_id}/{conversation_id}")
async def delete_chat(session_id: str, conversation_id: str):
    """Delete a conversation."""
    try:
        deps = get_dependencies()
        deleted = deps.firestore_db.delete_chat(session_id, conversation_id)
        if deleted:
            logger.info(f"✅ Deleted chat {session_id}/{conversation_id}")
            return {"message": "Chat deleted successfully"}
        raise HTTPException(status_code=404, detail="Chat not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("🚨 Error deleting chat.")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_id}/conversations")
async def list_conversations(session_id: str):
    """List all conversations for a session."""
    try:
        deps = get_dependencies()
        conversations_ref = (
            deps.firestore_db.db.collection("chat_sessions")
            .document(session_id)
            .collection("conversations")
        )
        
        conversations = []
        for doc in conversations_ref.stream():
            data = doc.to_dict()
            conversations.append({
                "conversation_id": doc.id,
                "title": data.get("title", f"Conversation {doc.id}"),
                "timestamp": data.get("timestamp"),
                "message_count": len(data.get("messages", []))
            })
        
        logger.info(f"✅ Retrieved {len(conversations)} conversations for {session_id}")
        return {"conversations": conversations}
    except Exception as e:
        logger.exception("🚨 Error listing conversations.")
        raise HTTPException(status_code=500, detail=str(e))