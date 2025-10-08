import smtplib
import logging
from email.mime.text import MIMEText
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_invoice_email(email: str, order_details: Dict[str, Any]) -> None:
        """
        Sends an invoice email.
        
        Args:
            email: The recipient's email address
            order_details: Dictionary containing order information
        """
        try:
            subject = f"Essilor Order Confirmation - Order ID: {order_details['Order ID']}"
            body = f"""
Dear {order_details['Customer Name']},

Thank you for your order with Essilor! Here are the details:

Order ID: {order_details['Order ID']}
Product: {order_details['Product Name']}
Quantity: {order_details['Quantity']}
Order Date: {order_details['Date of Order']}
Delivery Date: {order_details['Date of Delivery']}
Order Status: {order_details['Order Status']}

If you have any questions, please contact our support team.

Best regards,
The Essilor Team
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = settings.EMAIL_HOST_USER
            msg['To'] = email
            
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                server.connect(settings.EMAIL_HOST, settings.EMAIL_PORT)
                server.starttls()
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                server.sendmail(settings.EMAIL_HOST_USER, email, msg.as_string())
            
            logger.info(f"Invoice email sent to {email} for Order ID: {order_details['Order ID']}")
        
        except Exception as e:
            logger.error(f"Error sending invoice email to {email}: {e}")
            raise