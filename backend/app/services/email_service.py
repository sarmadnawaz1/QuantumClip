"""Email service for sending verification and password reset emails."""

import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from jinja2 import Template
from datetime import datetime, timedelta
import random
import string

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))


def get_email_template(verification_code: str, purpose: str = "verification") -> str:
    """Get HTML email template with website theme."""
    if purpose == "verification":
        title = "Verify Your Email Address"
        message = f"Your verification code is: <strong style='font-size: 32px; color: #6241ff; letter-spacing: 4px;'>{verification_code}</strong>"
        description = "Please enter this code to verify your email address and activate your QuantumClip account."
    elif purpose == "password_reset":
        title = "Reset Your Password"
        message = f"Your password reset code is: <strong style='font-size: 32px; color: #6241ff; letter-spacing: 4px;'>{verification_code}</strong>"
        description = "Please enter this code to reset your password. This code will expire in 15 minutes."
    else:
        title = "Verification Code"
        message = f"Your code is: <strong style='font-size: 32px; color: #6241ff; letter-spacing: 4px;'>{verification_code}</strong>"
        description = "Please use this code to complete your request."
    
    template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);">
    <table role="presentation" style="width: 100%; border-collapse: collapse; background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background: rgba(255, 255, 255, 0.05); border-radius: 16px; overflow: hidden; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #4287ff 0%, #6241ff 50%, #9f3cff 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: 700; letter-spacing: -0.5px;">QuantumClip</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 14px; font-weight: 500; text-transform: uppercase; letter-spacing: 2px;">AI Video Engine</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 50px 40px; text-align: center;">
                            <h2 style="margin: 0 0 20px 0; color: #ffffff; font-size: 24px; font-weight: 600;">{title}</h2>
                            <p style="margin: 0 0 30px 0; color: rgba(255, 255, 255, 0.8); font-size: 16px; line-height: 1.6;">
                                {description}
                            </p>
                            
                            <!-- Code Box -->
                            <div style="background: rgba(98, 65, 255, 0.1); border: 2px solid rgba(98, 65, 255, 0.3); border-radius: 12px; padding: 30px; margin: 30px 0;">
                                <p style="margin: 0 0 15px 0; color: rgba(255, 255, 255, 0.7); font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Verification Code</p>
                                {message}
                            </div>
                            
                            <p style="margin: 30px 0 0 0; color: rgba(255, 255, 255, 0.6); font-size: 14px; line-height: 1.6;">
                                If you didn't request this code, you can safely ignore this email.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px 40px; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.1);">
                            <p style="margin: 0 0 10px 0; color: rgba(255, 255, 255, 0.5); font-size: 12px;">
                                © {datetime.now().year} QuantumClip. All rights reserved.
                            </p>
                            <p style="margin: 0; color: rgba(255, 255, 255, 0.4); font-size: 11px;">
                                This is an automated email. Please do not reply.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return template


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """Send an email using SMTP."""
    try:
        if not settings.smtp_password:
            logger.warning("SMTP password not configured. Email sending disabled.")
            return False
        
        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add text version if provided
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)
        
        # Add HTML version
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=True,
        )
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
        return False


async def send_verification_email(email: str, verification_code: str) -> bool:
    """Send email verification code."""
    html_content = get_email_template(verification_code, "verification")
    text_content = f"Your QuantumClip verification code is: {verification_code}\n\nPlease enter this code to verify your email address."
    subject = "Verify Your QuantumClip Email Address"
    
    return await send_email(email, subject, html_content, text_content)


async def send_password_reset_email(email: str, reset_code: str) -> bool:
    """Send password reset code."""
    html_content = get_email_template(reset_code, "password_reset")
    text_content = f"Your QuantumClip password reset code is: {reset_code}\n\nPlease enter this code to reset your password. This code will expire in 15 minutes."
    subject = "Reset Your QuantumClip Password"
    
    return await send_email(email, subject, html_content, text_content)

