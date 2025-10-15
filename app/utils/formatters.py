import pandas as pd
from typing import List, Dict, Any

def format_description_v2(row: pd.Series) -> str:
    """Format product description for embedding."""
    return (
        f"{row['Product Name']}, {row['Product Type']}, {row['Brand Name']}, "
        f"suitable for {row['Activity']}, face shape {row['Face Shape']}, "
        f"price {row['Price']} with a discount of {row['Discount']}%. "
        f"Image: {row['Image URL']}, "
        f"frame color {row['Frame Colour']} and lens color {row['Lens Color']}"
    )

def format_order_description(row: pd.Series) -> str:
    """Format order description for embedding."""
    return (
        f"Order ID: {row['Order ID']}, Product: {row['Product Name']}, "
        f"Customer: {row['Customer Name']}, Email: {row['Email ID']}, "
        f"Ordered on {row['Date of Order']}, Status: {row['Order Status']}, "
        f"Delivery date: {row['Date of Delivery']}, Quantity: {row['Quantity']}"
    )

def format_product_table(products: List[Dict[str, Any]]) -> str:
    """Format products as a string table."""
    if not products:
        return "No products found"
    df = pd.DataFrame(products)
    return df.to_string(index=False)

def format_order_table(orders: List[Dict[str, Any]]) -> str:
    """
    Format orders as a string table with ALL required fields.
    Required fields: Order ID, Date of Order, Order Status, Date of Delivery,
                     Quantity, Product Name, Customer Name
    """
    if not orders:
        return "No orders found"
    df = pd.DataFrame(orders)
    
    required_columns = [
        'Order ID',
        'Date of Order',
        'Order Status',
        'Date of Delivery',
        'Quantity',
        'Product Name',
        'Customer Name'
    ]
    
    available_columns = [col for col in required_columns if col in df.columns]
    
    if not available_columns:
        # Fallback: show all columns if required ones are missing
        return df.to_string(index=False)
    
    # Return formatted table with required columns
    return df[available_columns].to_string(index=False)