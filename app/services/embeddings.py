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
                
                self.image_features_db = np.load(in_memory_file, allow_pickle=True)
                logger.info("Successfully loaded image embeddings from GCS")
                return
        except Exception as e:
            logger.warning(f"Could not load embeddings from GCS: {e}")
        
        # Create new embeddings
        logger.info("Processing images and creating embeddings...")
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
                    product_data = {k: v for k, v in row.items()}
                    product_data['GCS_Image_URL'] = gcs_url
                    meta_data.append(product_data)
                    logger.info(f"Processed image for {product_name}")
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
                    self.image_features_db = np.load(in_memory_file, allow_pickle=True)
                    logger.info(f"Saved {len(meta_data)} image embeddings")
            except Exception as e:
                logger.error(f"Failed to save or upload embeddings: {e}")
        else:
            logger.error("No images were processed successfully")
    
    def get_embeddings_db(self) -> Optional[np.ndarray]:
        """Get the image embeddings database."""
        if self.image_features_db is None:
            self.initialize_image_embeddings()
        return self.image_features_db
