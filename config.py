import os
import sys
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
def get_env(key, default=None, required=False):
    value = os.getenv(key, default)
    if required and not value:
        logging.critical(f"FATAL: Missing required environment variable: {key}")
        sys.exit(1)
    return value


UNSUBSCRIBE_URL = get_env("UNSUBSCRIBE_URL")

# --- Discord Bot ---
TOKEN = get_env("TOKEN")
ADMIN_CHANNEL_ID = int(
    get_env("ADMIN_CHANNEL_ID", 1406306662826119449)
)  # Default provided in original code
GUILD_ID = int(
    get_env("GUILD_ID", 1304508522305683496)
)  # Default provided in original code

# --- Webhook ---
WEBHOOK_SECRET_KEY = get_env("WEBHOOK_SECRET_KEY", required=True)
WEB_SERVER_PORT = int(get_env("PORT", 8080))

# --- Database ---
DATABASE_URL = get_env("DATABASE_URL", required=True)

# --- Website ---
SITE_URL = get_env("SITE_URL", "http://localhost:3000")
REVALIDATION_SECRET = get_env("REVALIDATION_SECRET", "replace-me")

# --- Gmail API ---
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
# Path inside the project directory to store the generated token.pickle
GMAIL_TOKEN_PICKLE_PATH = "key/token.pickle"
# Base64 encoded token for initial setup, loaded from env
GMAIL_API_TOKEN_BASE64 = get_env("GMAIL_API_TOKEN_BASE64")
SENDER_EMAIL = "me"  # Uses the authenticated user's email

# --- Invite Content ---
WHATSAPP_URL = get_env("WHATSAPP_URL", "#")
CLUSTER_INVITE_URL = "https://discord.gg/g2MHZGpdrc"
# Role to be assigned upon successful /verify
VERIFY_ROLE_ID = int(get_env("VERIFY_ROLE_ID", 1350132344417157140))

# --- Column Names ---
COL_EMAIL = "email"
COL_FIRST_NAME = "firstName"
COL_LAST_NAME = "lastName"
COL_PHONE = "phone"
COL_COLLEGE = "college"
COL_YEAR = "year"
COL_INTERESTS = "interests"
COL_MOTIVATION = "motivation"
COL_ACCEPTED = "accepted"
COL_RESPONDED = "responded"
COL_ROLE_CLAIMED = "roleClaimed"

# --- College Application Column Names ---
COL_COLLEGE_NAME = "collegeName"
COL_COMMUNITY_NAME = "communityName"
COL_REP_NAME = "repName"
COL_REP_POSITION = "repPosition"
COL_REP_EMAIL = "repEmail"
COL_REP_PHONE = "repPhone"
COL_FACULTY_NAME = "facultyName"
COL_FACULTY_EMAIL = "facultyEmail"
COL_COMMUNITY_SIZE = "communitySize"
COL_COMMUNITY_ACTIVITIES = "communityActivities"
COL_EXPECTATIONS = "expectations"
