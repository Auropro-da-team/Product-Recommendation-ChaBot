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
    """Format orders as a string table."""
    if not orders:
        return "No orders found"
    df = pd.DataFrame(orders)
    return df.to_string(index=False)

