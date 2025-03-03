""" 
    Written by Juan Pablo Gutiérrez
    11 09 2024
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

def send_email(subject: str, body: str, to_email: List[str]) -> bool:
    """Send an email using Gmail SMTP.
    
    Args:
        subject: Email subject
        body: Email body text
        to_email: List of recipient email addresses
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    from_email = os.getenv("SENDER_EMAIL")
    password = os.getenv("SENDER_PASSWORD")

    if not from_email or not password:
        print("Error: Email credentials not found in environment variables")
        return False

    # Ensure to_email is a list
    if isinstance(to_email, str):
        to_email = [to_email]

    try:
        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = ", ".join(to_email)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, password)
            
            # Send the email
            server.send_message(msg)
            print("Email sent successfully!")
            return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False