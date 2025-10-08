import logging
import chromadb
import pandas as pd
from typing import List, Dict, Any
from app.config import settings
from app.utils.formatters import format_description_v2, format_order_description

logger = logging.getLogger(__name__)

class ChromaDBManager:
    def __init__(self, model):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.products_collection = self.client.get_or_create_collection(
            name=settings.PRODUCTS_COLLECTION_NAME
        )
        self.orders_collection = self.client.get_or_create_collection(
            name=settings.ORDERS_COLLECTION_NAME
        )
        self.model = model
        logger.info("ChromaDB collections initialized")
    
    def populate_products(self, df: pd.DataFrame) -> None:
        """Populate products collection from DataFrame."""
        if self.products_collection.count() == 0:
            logger.info("Populating ChromaDB with product data...")
            for i, row in df.iterrows():
                description = format_description_v2(row)
                embedding = self.model.encode(description, convert_to_numpy=True).tolist()
                self.products_collection.add(
                    ids=[str(i)],
                    embeddings=[embedding],
                    metadatas=[{
                        "Product Name": row["Product Name"],
                        "Brand Name": row["Brand Name"],
                        "Price": row["Price"],
                        "Discount": row["Dicount"],
                        "Activity": row["Activity"],
                        "Face Shape": row["Face Shape"],
                        "Product Type": row["Product Type"],
                        "Image URL": row["Image URL"],
                        "Prescription Type": row["Prescription Type"],
                        "Frame Colour": row["Frame Colour"],
                        "Lens Color": row["Lens Color"]
                    }]
                )
            logger.info(f"Total products in collection: {self.products_collection.count()}")
        else:
            logger.info(f"ChromaDB already contains {self.products_collection.count()} products")
    
    def populate_orders(self, df: pd.DataFrame) -> None:
        """Populate orders collection from DataFrame."""
        if self.orders_collection.count() == 0 and not df.empty:
            logger.info("Populating ChromaDB with orders data...")
            for i, row in df.iterrows():
                description = format_order_description(row)
                embedding = self.model.encode(description, convert_to_numpy=True).tolist()
                self.orders_collection.add(
                    ids=[str(i)],
                    embeddings=[embedding],
                    metadatas=[{
                        "Order ID": str(row["Order ID"]),
                        "Email ID": str(row["Email ID"]),
                        "Product Name": str(row["Product Name"]),
                        "Date of Order": str(row["Date of Order"]),
                        "Order Status": str(row["Order Status"]),
                        "Date of Delivery": str(row["Date of Delivery"]),
                        "Quantity": str(row["Quantity"]),
                        "Customer ID": str(row["Customer ID"]),
                        "Product ID": str(row["Product ID"]),
                        "Customer Name": str(row["Customer Name"])
                    }]
                )
            logger.info(f"Total orders in collection: {self.orders_collection.count()}")
        else:
            logger.info(f"ChromaDB already contains {self.orders_collection.count()} orders")
    
    def query_products(self, query_embedding: List[float], top_k: int = 3) -> Dict[str, Any]:
        """Query products collection."""
        return self.products_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
    
    def get_all_orders(self) -> Dict[str, Any]:
        """Get all orders from collection."""
        return self.orders_collection.get(include=["metadatas"])

