import logging
from google.cloud import firestore
from datetime import datetime
from typing import Dict, List, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class FirestoreDB:
    def __init__(self):
        self.db = firestore.Client(project=settings.FIRESTORE_PROJECT_ID)
        logger.info(f"Firestore client initialized for project: {settings.FIRESTORE_PROJECT_ID}")
    
    def get_conversation_history(self, session_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history from Firestore."""
        try:
            conversation_ref = (
                self.db.collection("chat_sessions")
                .document(session_id)
                .collection("conversations")
                .document(conversation_id)
            )
            doc = conversation_ref.get()
            data = doc.to_dict() if doc.exists else {}
            conversation_history = data.get("messages", [])
            
            if not isinstance(conversation_history, list):
                conversation_history = []
            
            return conversation_history
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def save_conversation(
        self,
        session_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        title: Optional[str] = None
    ) -> None:
        """Save conversation to Firestore."""
        try:
            session_ref = self.db.collection("chat_sessions").document(session_id)
            conversation_ref = session_ref.collection("conversations").document(conversation_id)
            
            # Ensure session exists
            session_ref.set({"created_at": firestore.SERVER_TIMESTAMP}, merge=True)
            
            # Save conversation
            conversation_data = {
                "messages": messages,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "last_updated": firestore.SERVER_TIMESTAMP
            }
            
            if title:
                conversation_data["title"] = title
            else:
                # Get existing title or create default
                doc = conversation_ref.get()
                if doc.exists:
                    existing_title = doc.to_dict().get("title")
                    if existing_title:
                        conversation_data["title"] = existing_title
                    else:
                        conversation_data["title"] = f"Conversation {conversation_id}"
                else:
                    conversation_data["title"] = f"Conversation {conversation_id}"
            
            conversation_ref.set(conversation_data, merge=True)
            logger.info(f"✅ Firestore: Updated conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            raise
    
    def save_image_metadata(
        self,
        image_id: str,
        session_id: str,
        conversation_id: str,
        blob_path: str,
        original_filename: str,
        content_type: str
    ) -> None:
        """Save image metadata to Firestore."""
        try:
            image_ref = self.db.collection("user_images").document(image_id)
            image_ref.set({
                "session_id": session_id,
                "conversation_id": conversation_id,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "blob_path": blob_path,
                "original_filename": original_filename,
                "content_type": content_type
            })
            logger.info(f"Stored image metadata with ID: {image_id}")
        except Exception as e:
            logger.error(f"Error saving image metadata: {e}")
            raise
    
    def get_chat(self, session_id: str, conversation_id: str) -> Dict[str, Any]:
        """Get a specific chat conversation."""
        try:
            conversation_ref = (
                self.db.collection("chat_sessions")
                .document(session_id)
                .collection("conversations")
                .document(conversation_id)
            )
            doc = conversation_ref.get()
            data = doc.to_dict() if doc.exists else {}
            
            return {
                "messages": data.get("messages", []),
                "title": data.get("title", ""),
                "timestamp": data.get("timestamp", None),
                "products": data.get("table", []),
                "orders": data.get("orders_table", [])
            }
        except Exception as e:
            logger.error(f"Error fetching chat: {e}")
            raise
    
    def delete_chat(self, session_id: str, conversation_id: str) -> bool:
        """Delete a chat conversation."""
        try:
            conversation_ref = (
                self.db.collection("chat_sessions")
                .document(session_id)
                .collection("conversations")
                .document(conversation_id)
            )
            if conversation_ref.get().exists:
                conversation_ref.delete()
                logger.info(f"Deleted conversation {conversation_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting chat: {e}")
            raise
    
    def get_conversation_id(self, session_id: str) -> Optional[str]:
        """Get conversation ID for a session."""
        try:
            users_ref = self.db.collection("users").document(session_id)
            doc = users_ref.get()
            if doc.exists and "conversation_id" in doc.to_dict():
                return doc.to_dict()["conversation_id"]
            return None
        except Exception as e:
            logger.error(f"Error getting conversation ID: {e}")
            return None
