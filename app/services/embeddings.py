import logging
import numpy as np
import torch
import requests
from io import BytesIO
from PIL import Image
from datetime import datetime
from typing import Optional
from google.cloud import storage
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingsManager:
    def __init__(self, df, clip_model, clip_preprocess, device):
        self.df = df
        self.clip_model = clip_model
        self.clip_preprocess = clip_preprocess
        self.device = device
        self.image_features_db: Optional[np.ndarray] = None
    
    def _format_discount(self, discount_value) -> str:
        """
        Format discount value to percentage string.
        Handles various input formats (float, int, string with %).
        """
        try:
            # Handle None or NaN
            if discount_value is None or (isinstance(discount_value, float) and np.isnan(discount_value)):
                return "0%"
            
            # If already a string with %, just return it as-is (already formatted)
            if isinstance(discount_value, str):
                if '%' in discount_value:
                    # Already has %, just clean and return
                    return discount_value.strip()
                else:
                    # String without %, convert to float and format
                    discount_float = float(discount_value)
            else:
                # Numeric value, convert to float
                discount_float = float(discount_value)
            
            # Format numeric values
            if discount_float == int(discount_float):
                return f"{int(discount_float)}%"
            else:
                # Keep up to 2 decimal places, remove trailing zeros
                formatted = f"{discount_float:.2f}".rstrip('0').rstrip('.')
                return f"{formatted}%"
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not format discount value '{discount_value}': {e}")
            return "0%"
    
    def initialize_image_embeddings(self) -> None:
        """Initialize or load image embeddings from GCS."""
        bucket_name = settings.GCS_BUCKET_NAME
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Check if embeddings exist in GCS
        try:
            blob = bucket.blob("embeddings/image_features_db.npz")
            if blob.exists():
                logger.info("Loading image embeddings from GCS")
                
                in_memory_file = BytesIO()
                blob.download_to_file(in_memory_file)
                in_memory_file.seek(0)
                
                # Load the npz file and convert to dictionary
                npz_data = np.load(in_memory_file, allow_pickle=True)
                self.image_features_db = {
                    'embeddings': npz_data['embeddings'],
                    'meta': npz_data['meta']
                }
                npz_data.close()
                
                logger.info("Successfully loaded image embeddings from GCS")
                
                # Log sample discount values to verify
                if len(self.image_features_db['meta']) > 0:
                    sample_discount = self.image_features_db['meta'][0].get('Discount', 'N/A')
                    logger.info(f"Sample discount from loaded embeddings: {sample_discount}")
                
                return
        except Exception as e:
            logger.warning(f"Could not load embeddings from GCS: {e}")
        
        # Create new embeddings
        logger.info("Processing images and creating embeddings...")
        logger.info(f"CSV columns: {self.df.columns.tolist()}")
        
        # Log sample discount values from CSV
        if len(self.df) > 0:
            sample_csv_discount = self.df.iloc[0]['Discount']
            logger.info(f"Sample discount from CSV (raw): {sample_csv_discount} (type: {type(sample_csv_discount)})")
            logger.info(f"Sample discount formatted: {self._format_discount(sample_csv_discount)}")
        
        image_features = []
        meta_data = []
        
        for i, row in self.df.iterrows():
            product_name = row['Product Name']
            image_url = row['Image URL']
            
            try:
                # Download image
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content)).convert("RGB")
                    
                    # Save image to GCS
                    blob_name = f"images/{i}_{product_name[:20].replace('/', '-').replace(' ', '_')}.jpg"
                    blob = bucket.blob(blob_name)
                    
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG")
                    buffer.seek(0)
                    blob.upload_from_string(buffer.getvalue(), content_type="image/jpeg")
                    
                    gcs_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
                    
                    # Process image with CLIP
                    img_tensor = self.clip_preprocess(img).unsqueeze(0).to(self.device)
                    with torch.no_grad():
                        emb = self.clip_model.encode_image(img_tensor).cpu().numpy()
                    
                    image_features.append(emb)
                    
                    # Build product metadata - CRITICAL: Format discount correctly
                    product_data = {k: v for k, v in row.items()}
                    product_data['GCS_Image_URL'] = gcs_url
                    
                    # CRITICAL FIX: Ensure discount is formatted as percentage string
                    raw_discount = row.get('Discount', 0)
                    product_data['Discount'] = self._format_discount(raw_discount)
                    
                    meta_data.append(product_data)
                    
                    if i == 0:  # Log first product to verify
                        logger.info(f"First product metadata - Discount: {product_data['Discount']}")
                    
                    logger.info(f"Processed image for {product_name} (Discount: {product_data['Discount']})")
            except Exception as e:
                logger.error(f"Error processing image for {product_name}: {e}")
        
        # Save embeddings to GCS
        if image_features:
            try:
                image_features = np.vstack(image_features)
                
                with BytesIO() as in_memory_file:
                    np.savez(in_memory_file, embeddings=image_features, meta=meta_data)
                    in_memory_file.seek(0)
                    
                    blob = bucket.blob("embeddings/image_features_db.npz")
                    blob.upload_from_file(in_memory_file, content_type="application/octet-stream")
                    logger.info("Uploaded image embeddings to GCS")
                    
                    in_memory_file.seek(0)
                    npz_data = np.load(in_memory_file, allow_pickle=True)
                    self.image_features_db = {
                        'embeddings': npz_data['embeddings'],
                        'meta': npz_data['meta']
                    }
                    npz_data.close()
                    
                    logger.info(f"Saved {len(meta_data)} image embeddings")
                    
                    # Log sample to verify discount was saved correctly
                    if len(self.image_features_db['meta']) > 0:
                        sample_discount = self.image_features_db['meta'][0].get('Discount', 'N/A')
                        logger.info(f"✅ Verified sample discount in saved embeddings: {sample_discount}")
            except Exception as e:
                logger.error(f"Failed to save or upload embeddings: {e}")
        else:
            logger.error("No images were processed successfully")
    
    def get_embeddings_db(self) -> Optional[np.ndarray]:
        """Get the image embeddings database."""
        if self.image_features_db is None:
            self.initialize_image_embeddings()
        return self.image_features_db