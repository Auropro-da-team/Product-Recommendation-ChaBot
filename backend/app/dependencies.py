import logging
import pandas as pd
import torch
import open_clip
from sentence_transformers import SentenceTransformer
from agno.agent import Agent
# from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from google.cloud import storage
from app.config import settings
from app.database.firestore import FirestoreDB
from app.database.chromadb import ChromaDBManager
from app.services.embeddings import EmbeddingsManager
from app.services.image_search import ImageSearchService
from app.services.search import SearchService
from app.services.chatbot import ChatbotService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class Dependencies:
    """Container for all application dependencies."""
    
    def __init__(self):
        # Initialize device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Initialize AI agent
        # self.agent = Agent(model=Groq(id=settings.GROQ_MODEL_ID), markdown=True)
        self.agent = Agent(model=OpenAIChat(api_key=settings.OPENAI_API_KEY), markdown=True)

        logger.info("AI Agent initialized")
        
        # Initialize Sentence Transformer
        self.model = SentenceTransformer(
            settings.SENTENCE_TRANSFORMER_MODEL,
            use_auth_token=settings.HF_TOKEN
        )
        logger.info("Sentence Transformer loaded")
        
        # Initialize CLIP model
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
            settings.CLIP_MODEL_NAME,
            pretrained=settings.CLIP_PRETRAINED
        )
        self.clip_model = self.clip_model.to(self.device).eval()
        logger.info("CLIP model loaded")
        
        # Load product data
        self.products_df = pd.read_csv(settings.PRODUCTS_CSV_PATH)
        logger.info(f"Loaded {len(self.products_df)} products")
        
        # Load orders data
        try:
            self.orders_df = pd.read_csv(settings.ORDERS_CSV_PATH)
            logger.info(f"Loaded {len(self.orders_df)} orders")
        except Exception as e:
            logger.error(f"Error loading orders data: {e}")
            self.orders_df = pd.DataFrame(columns=[
                "Order ID", "Email ID", "Product Name", "Date of Order",
                "Order Status", "Date of Delivery", "Quantity",
                "Customer ID", "Product ID", "Customer Name"
            ])
        
        # Initialize databases
        self.firestore_db = FirestoreDB()
        self.chroma_manager = ChromaDBManager(self.model)
        
        # Populate ChromaDB
        self.chroma_manager.populate_products(self.products_df)
        self.chroma_manager.populate_orders(self.orders_df)
        
        # Initialize embeddings manager
        self.embeddings_manager = EmbeddingsManager(
            self.products_df,
            self.clip_model,
            self.clip_preprocess,
            self.device
        )
        self.embeddings_manager.initialize_image_embeddings()
        
        # Initialize services
        self.image_search_service = ImageSearchService(
            self.clip_model,
            self.clip_preprocess,
            self.device,
            self.embeddings_manager
        )
        
        self.search_service = SearchService(
            self.model,
            self.chroma_manager,
            self.agent
        )
        
        self.chatbot_service = ChatbotService(
            self.agent,
            self.search_service
        )
        
        self.email_service = EmailService()
        
        logger.info("All dependencies initialized successfully")

# Global dependencies instance
_deps = None

def get_dependencies() -> Dependencies:
    """Get or create dependencies instance."""
    global _deps
    if _deps is None:
        _deps = Dependencies()
    return _deps
