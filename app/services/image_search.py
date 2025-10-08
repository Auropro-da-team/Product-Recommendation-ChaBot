import logging
import numpy as np
import torch
import uuid
from io import BytesIO
from PIL import Image
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from google.cloud import storage
from app.config import settings

logger = logging.getLogger(__name__)

class ImageSearchService:
    def __init__(self, clip_model, clip_preprocess, device, embeddings_manager):
        self.clip_model = clip_model
        self.clip_preprocess = clip_preprocess
        self.device = device
        self.embeddings_manager = embeddings_manager
    
    def search_by_image(
        self,
        image_file: bytes,
        top_k: int = 3,
        similarity_threshold: float = 0.45
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Search for similar products using image similarity.
        
        Args:
            image_file: Image file bytes
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            Tuple of (results list, status message)
        """
        image_features_db = self.embeddings_manager.get_embeddings_db()
        
        if image_features_db is None:
            return [], "Image database initialization failed"
        
        try:
            # Open and preprocess the uploaded image
            img = Image.open(BytesIO(image_file)).convert("RGB")
            img_tensor = self.clip_preprocess(img).unsqueeze(0).to(self.device)
            
            # Save the uploaded image to GCS for reference
            try:
                bucket_name = settings.GCS_BUCKET_NAME
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                blob_name = f"uploads/search_{timestamp}_{unique_id}.jpg"
                
                blob = bucket.blob(blob_name)
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                blob.upload_from_string(buffer.getvalue(), content_type="image/jpeg")
                
                logger.info(f"Uploaded search image to GCS: {blob_name}")
            except Exception as e:
                logger.warning(f"Failed to upload search image to GCS: {e}")
            
            # Encode the image with CLIP
            with torch.no_grad():
                user_emb = self.clip_model.encode_image(img_tensor).cpu().numpy()
            
            # Compute similarities
            db_embs = image_features_db['embeddings']
            db_meta = image_features_db['meta'].tolist()
            sims = cosine_similarity(user_emb, db_embs)[0]
            
            # Get top matches
            top_indices = np.argsort(sims)[::-1]
            
            results = []
            for idx in top_indices:
                if sims[idx] >= similarity_threshold:
                    meta = db_meta[idx]
                    
                    # Use GCS URL if available
                    image_url = meta.get("GCS_Image_URL", meta["Image URL"])
                    
                    results.append({
                        "Product Name": meta["Product Name"],
                        "Brand Name": meta["Brand Name"],
                        "Price": meta["Price"],
                        "Discount": meta["Dicount"],
                        "Activity": meta["Activity"],
                        "Face Shape": meta["Face Shape"],
                        "Product Type": meta["Product Type"],
                        "Image URL": image_url,
                        "Prescription Type": meta["Prescription Type"],
                        "Frame Colour": meta["Frame Colour"],
                        "Lens Color": meta["Lens Color"],
                        "Similarity Score": float(sims[idx])
                    })
                if len(results) == top_k:
                    break
            
            if not results:
                return [], "No matching products found"
            
            return results, "Success"
        except Exception as e:
            logger.exception(f"Error in image search: {e}")
            return [], f"Error processing image: {str(e)}"
