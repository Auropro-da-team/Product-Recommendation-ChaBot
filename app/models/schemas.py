from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    user_input: str = Field(..., min_length=1)

class ProductResponse(BaseModel):
    product_name: str = Field(alias="Product Name")
    brand_name: str = Field(alias="Brand Name")
    price: float = Field(alias="Price")
    discount: float = Field(alias="Discount")
    activity: str = Field(alias="Activity")
    face_shape: str = Field(alias="Face Shape")
    product_type: str = Field(alias="Product Type")
    image_url: str = Field(alias="Image URL")
    prescription_type: str = Field(alias="Prescription Type")
    frame_colour: str = Field(alias="Frame Colour")
    lens_color: str = Field(alias="Lens Color")
    similarity_score: Optional[float] = Field(None, alias="Similarity Score")

    class Config:
        populate_by_name = True

class OrderResponse(BaseModel):
    order_id: str = Field(alias="Order ID")
    email_id: str = Field(alias="Email ID")
    product_name: str = Field(alias="Product Name")
    date_of_order: str = Field(alias="Date of Order")
    order_status: str = Field(alias="Order Status")
    date_of_delivery: str = Field(alias="Date of Delivery")
    quantity: str = Field(alias="Quantity")
    customer_id: str = Field(alias="Customer ID")
    product_id: str = Field(alias="Product ID")
    customer_name: str = Field(alias="Customer Name")

    class Config:
        populate_by_name = True

class ChatResponse(BaseModel):
    response: str
    products: List[Dict[str, Any]] = []
    orders: List[Dict[str, Any]] = []
    conversation_id: str
    session_id: str
    image_url: Optional[str] = None

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str
    has_image: Optional[bool] = False
    image_url: Optional[str] = None
    image_id: Optional[str] = None
    table: Optional[List[Dict[str, Any]]] = []
    orders_table: Optional[List[Dict[str, Any]]] = []
