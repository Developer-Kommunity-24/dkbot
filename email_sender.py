import base64
import pickle
import os
import sys
import asyncio
from email.mime.text import MIMEText
from functools import partial

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging

import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_gmail_service():
    """Authenticates with the Gmail API and returns the service object."""
    creds = None

    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists(config.GMAIL_TOKEN_PICKLE_PATH):
        with open(config.GMAIL_TOKEN_PICKLE_PATH, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, try to load from environment variable.
    if not creds:
        encoded_token = config.GMAIL_API_TOKEN_BASE64
        if encoded_token:
            os.makedirs(os.path.dirname(config.GMAIL_TOKEN_PICKLE_PATH), exist_ok=True)
            try:
                decoded_token = base64.b64decode(encoded_token)
                creds = pickle.loads(decoded_token)
                with open(config.GMAIL_TOKEN_PICKLE_PATH, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                logging.info(f"Initial Gmail token loaded from environment and saved to {config.GMAIL_TOKEN_PICKLE_PATH}")
            except (pickle.UnpicklingError, base64.binascii.Error) as e:
                logging.error(f"Failed to decode or unpickle the GMAIL_API_TOKEN_BASE64: {e}")
                sys.exit(1)
        else:
            logging.error("Gmail token not found. Set GMAIL_API_TOKEN_BASE64 for initial setup.")
            sys.exit(1)

    # If credentials are not valid, refresh them.
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(config.GMAIL_TOKEN_PICKLE_PATH, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                logging.info(f"Gmail token refreshed and saved to {config.GMAIL_TOKEN_PICKLE_PATH}")
            except Exception as e:
                logging.error(f"Error refreshing Gmail token: {e}")
                return None
        else:
            logging.error("Gmail token is invalid and cannot be refreshed.")
            return None
            
    return build('gmail', 'v1', credentials=creds)

def _create_message(sender, to, subject, message_text):
    """Creates a MIMEText message for the Gmail API."""
    message = MIMEText(message_text, 'html')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def _send_email_sync(recipient_email: str, name: str) -> bool:
    """Internal synchronous function to send email."""
    service = get_gmail_service()
    if not service:
        logging.error("Could not get Gmail service. Email not sent.")
        return False

    html_content = f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color:#f5f7fa; padding:20px;">
    <div style="max-width:600px; margin:auto; background:white; border-radius:12px; padding:30px; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
      <div style="text-align:center;">
        <img src="https://dk24.org/logo_new.png" alt="DK24 Logo" width="100" style="margin-bottom:15px;">
        <h2 style="color:#2b2d42;">You're Invited to Join the DK24 Cluster 🎉</h2>
      </div>
      <p style="color:#333; font-size:15px;">
        Hi {name}, we’re excited to welcome you to the <b>DK24 Discord Community and DK24 Cluster WhatsApp Group</b> - a collaborative hub for students and developers from partner communities.
        Click below to join and be part of our amazing network! Once joined use <code>/verify your-email</code> command with your registered email to claim your cluster role.
      </p>
      <table border="0" cellpadding="0" cellspacing="0" width="100%" style="text-align:center; margin:30px 0;">
        <tr>
          <td align="center" style="padding-bottom: 10px;">
            <a href="{config.CLUSTER_INVITE_URL}"
               style="background:#5865F2; color:white; text-decoration:none; padding:12px 24px; border-radius:6px; font-weight:bold; display:inline-block; width:80%; max-width:300px;">
               Join Discord Server
            </a>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding-top: 10px;">
            <a href="{config.WHATSAPP_URL}"
               style="background:#25D366; color:white; text-decoration:none; padding:12px 24px; border-radius:6px; font-weight:bold; display:inline-block; width:80%; max-width:300px;">
               Join WhatsApp Group
            </a>
          </td>
        </tr>
      </table>
      <p style="font-size:13px; color:#555; text-align:center;">
        Please use the <b>/verify</b> command on Discord with your email to claim your cluster role once joined.
      </p>
      <hr style="border:none; border-top:1px solid #eee; margin:20px 0;">
      <p style="text-align:center; font-size:12px; color:#777;">
        DK24 | Connecting College Tech Communities
      </p>
    </div>
  </body>
</html>
"""
    message = _create_message(
        config.SENDER_EMAIL,
        recipient_email,
        "🎉 Congratulations! You are selected for DK24 Cluster. 🎉",
        html_content
    )
    try:
        sent_message = service.users().messages().send(userId=config.SENDER_EMAIL, body=message).execute()
        logging.info(f"✅ Sent invite email to {recipient_email}, Message ID: {sent_message['id']}")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to send email to {recipient_email}: {e}")
        return False

async def send_invite_email(recipient_email: str, name: str) -> bool:
    """
    Sends a pre-formatted invitation email asynchronously.
    Returns True on success, False on failure.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_send_email_sync, recipient_email, name))
