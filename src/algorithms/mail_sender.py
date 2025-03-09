""" 
    Written by Juan Pablo Gutiérrez
    11 09 2024
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from typing import List
import os
import smtplib
import logging

load_dotenv()

def send_email(subject: str, body: str, to_email: list):
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

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = ", ".join(to_email)  # Join all email addresses with commas
    msg['Subject'] = subject

    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        
        # Send the email to all recipients
        server.send_message(msg, from_addr=from_email, to_addrs=to_email)  # Pass the list directly
        logging.info(f"Email sent successfully to {', '.join(to_email)}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
    finally:
        server.quit()
    return False