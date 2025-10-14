import logging
import chromadb
import pandas as pd
from typing import List, Dict, Any, Optional
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
    
    def _safe_str(self, value: Any, default: str = "N/A") -> str:
        """Safely convert value to string with fallback."""
        if pd.isna(value) or value is None:
            return default
        return str(value)
    
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float with fallback."""
        try:
            if pd.isna(value) or value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def populate_products(self, df: pd.DataFrame) -> None:
        """Populate products collection from DataFrame."""
        if self.products_collection.count() == 0:
            logger.info("Populating ChromaDB with product data...")
            logger.info(f"CSV Columns: {df.columns.tolist()}")
            
            # Verify required columns exist
            required_columns = [
                'Product ID', 'Product Name', 'Brand Name', 'Price', 'Discount',
                'Activity', 'Face Shape', 'Product Type', 'Image URL',
                'Prescription Type', 'Frame Colour', 'Lens Color'
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                raise ValueError(f"CSV missing columns: {missing_columns}")

            for i, row in df.iterrows():
                try:
                    description = format_description_v2(row)
                    embedding = self.model.encode(description, convert_to_numpy=True).tolist()
                    
                    # Build metadata with safe type conversion
                    metadata = {
                        "Product ID": self._safe_str(row["Product ID"]),
                        "Product Name": self._safe_str(row["Product Name"]),
                        "Brand Name": self._safe_str(row["Brand Name"]),
                        "Price": self._safe_float(row["Price"]),
                        "Discount": self._safe_float(row["Discount"]),
                        "Activity": self._safe_str(row["Activity"]),
                        "Face Shape": self._safe_str(row["Face Shape"]),
                        "Product Type": self._safe_str(row["Product Type"]),
                        "Image URL": self._safe_str(row["Image URL"]),
                        "Prescription Type": self._safe_str(row["Prescription Type"]),
                        "Frame Colour": self._safe_str(row["Frame Colour"]),
                        "Lens Color": self._safe_str(row["Lens Color"])
                    }
                    
                    if i == 0:  # Log first product to verify
                        logger.info(f"First product metadata: {metadata}")
                    
                    self.products_collection.add(
                        ids=[str(i)],
                        embeddings=[embedding],
                        metadatas=[metadata]
                    )
                except Exception as e:
                    logger.error(f"Error adding product at index {i}: {e}")
                    logger.error(f"Row data: {row.to_dict()}")
                    continue
            
            logger.info(f"✅ Total products in collection: {self.products_collection.count()}")
        else:
            logger.info(f"ChromaDB already contains {self.products_collection.count()} products")
    
    def populate_orders(self, df: pd.DataFrame) -> None:
        """Populate orders collection from DataFrame."""
        if self.orders_collection.count() == 0 and not df.empty:
            logger.info("Populating ChromaDB with orders data...")
            
            # Verify required columns
            required_columns = [
                'Order ID', 'Email ID', 'Product Name', 'Date of Order',
                'Order Status', 'Date of Delivery', 'Quantity',
                'Customer ID', 'Product ID', 'Customer Name'
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required order columns: {missing_columns}")
                raise ValueError(f"Orders CSV missing columns: {missing_columns}")
            
            for i, row in df.iterrows():
                try:
                    description = format_order_description(row)
                    embedding = self.model.encode(description, convert_to_numpy=True).tolist()
                    
                    metadata = {
                        "Order ID": self._safe_str(row["Order ID"]),
                        "Email ID": self._safe_str(row["Email ID"]),
                        "Product Name": self._safe_str(row["Product Name"]),
                        "Date of Order": self._safe_str(row["Date of Order"]),
                        "Order Status": self._safe_str(row["Order Status"]),
                        "Date of Delivery": self._safe_str(row["Date of Delivery"]),
                        "Quantity": self._safe_str(row["Quantity"]),
                        "Customer ID": self._safe_str(row["Customer ID"]),
                        "Product ID": self._safe_str(row["Product ID"]),
                        "Customer Name": self._safe_str(row["Customer Name"])
                    }
                    
                    self.orders_collection.add(
                        ids=[str(i)],
                        embeddings=[embedding],
                        metadatas=[metadata]
                    )
                except Exception as e:
                    logger.error(f"Error adding order at index {i}: {e}")
                    logger.error(f"Row data: {row.to_dict()}")
                    continue
            
            logger.info(f"✅ Total orders in collection: {self.orders_collection.count()}")
        else:
            logger.info(f"ChromaDB already contains {self.orders_collection.count()} orders")
    
    def query_products(self, query_embedding: List[float], top_k: int = 3) -> Dict[str, Any]:
        """Query products collection."""
        try:
            return self.products_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
        except Exception as e:
            logger.error(f"Error querying products: {e}")
            return {"metadatas": [[]], "distances": [[]], "ids": [[]]}
    
    def get_all_orders(self) -> Dict[str, Any]:
        """Get all orders from collection."""
        try:
            return self.orders_collection.get(include=["metadatas"])
        except Exception as e:
            logger.error(f"Error getting all orders: {e}")
            return {"metadatas": []}
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific product by Product ID."""
        try:
            all_products = self.products_collection.get(include=["metadatas"])
            for metadata in all_products.get("metadatas", []):
                if metadata and metadata.get("Product ID") == product_id:
                    return metadata
            logger.warning(f"Product ID {product_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting product by ID {product_id}: {e}")
            return None
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about the collections."""
        return {
            "products_count": self.products_collection.count(),
            "orders_count": self.orders_collection.count()
        }