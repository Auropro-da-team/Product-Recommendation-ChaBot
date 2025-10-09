import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Email Configuration
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_HOST_USER = "findsrividyap@gmail.com"
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "wogkrqhiaccnrydj")
    
    # Firestore Configuration
    FIRESTORE_PROJECT_ID = os.getenv("FIRESTORE_PROJECT_ID", "prj-auropro-dev")
    
    # GCS Configuration
    GCS_BUCKET_NAME = "essilor-eyewear" # this bucket is for storing product images
    GCS_IMAGE_BUCKET_NAME = "essilor-eyewear-images" # this bucket is for storing user uploaded images

    # Model Configuration
    HF_TOKEN = os.getenv("HF_TOKEN")
    # MODEL_PATH = "/root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/"
    SENTENCE_TRANSFORMER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    CLIP_MODEL_NAME = "ViT-B-32"
    CLIP_PRETRAINED = "laion2b_s34b_b79k"
    
    # ChromaDB Configuration
    CHROMA_DB_PATH = "./chroma_db"
    PRODUCTS_COLLECTION_NAME = "A_2847645678"
    ORDERS_COLLECTION_NAME = "B_237676564354"
    
    # Data Paths
    PRODUCTS_CSV_PATH = "/Users/likithgannarapu/Documents/Auropro/Product-Recommendation-ChaBot/csv_files/Updated_Essilor_Products.csv"
    ORDERS_CSV_PATH = "/Users/likithgannarapu/Documents/Auropro/Product-Recommendation-ChaBot/csv_files/order table.csv"
    
    # Search Configuration
    DEFAULT_TOP_K = 3
    IMAGE_SIMILARITY_THRESHOLD = 0.45
    
    # AI Model Configuration
    GROQ_MODEL_ID = "llama-3.3-70b-versatile"
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

    # CORS Configuration
    CORS_ORIGINS = ["*"]
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_METHODS = ["*"]
    CORS_ALLOW_HEADERS = ["*"]

settings = Settings()