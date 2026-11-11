import logging
import config
from datetime import datetime, timedelta
from html import escape

from email_sender import send_html_email

from zoneinfo import ZoneInfo
from urllib.parse import quote

IST = ZoneInfo("Asia/Kolkata")

logger = logging.getLogger(__name__)

def _parse_event_datetime(value):
    event_datetime = datetime.fromisoformat(value)

    if event_datetime.tzinfo is None:
        return event_datetime.replace(tzinfo=IST)

    return event_datetime.astimezone(IST)

def generate_digest_html(events, unsubscribe_url):
    event_cards = []

    for event in events:
        title = escape(event.get("title", "Untitled Event"))
        description = escape(event.get("description", ""))
        location = escape(event.get("location", "Location not specified"))
        organization = escape(event.get("organizationName", "DK24"))

        start_date = _parse_event_datetime(event["startDateTime"])
        date = start_date.strftime("%d %B %Y")
        time = start_date.strftime("%I:%M %p")

        registration_link = event.get("registrationLink")
        button = ""

        if registration_link:
            button = f'<a href="{escape(registration_link, quote=True)}">Register Now</a>'

        event_cards.append(f"""
            <div style="padding:20px;border:1px solid #ddd;border-radius:8px;margin-bottom:16px;">
                <h2>{title}</h2>
                <p>{date} · {time}</p>
                <p>{location}</p>
                <p>{organization}</p>
                <p>{description}</p>
                {button}
            </div>
        """)

    events_html = "".join(event_cards)

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto;padding:20px;">
        <h1>DK24 Upcoming Events</h1>
        <p>Here are the upcoming community events for the next 15 days.</p>
        {events_html}
        <hr>
        <p style="font-size:12px;color:#777;">
            You received this email because you subscribed to DK24 event updates.
        </p>
        <a href="{escape(unsubscribe_url, quote=True)}">Unsubscribe</a>
    </body>
    </html>
    """


async def send_event_digest(database):
    now = datetime.now(IST)
    end_date = now + timedelta(days=15)

    events = await database.async_get_approved_events()

    upcoming_events = []

    for event in events:
        start_date = _parse_event_datetime(event["startDateTime"])

        if now <= start_date <= end_date:
            upcoming_events.append(event)

    if not upcoming_events:
        logger.info("No upcoming events found. Digest not sent.")
        return

    recipients = await database.async_get_digest_recipients()

    for recipient in recipients:
        email = recipient["email"]
        token = recipient["unsubscribe_token"]

        separator = "&" if "?" in config.UNSUBSCRIBE_URL else "?"
        unsubscribe_url = (
            f"{config.UNSUBSCRIBE_URL}{separator}token={quote(token, safe='')}"
        )

        html_content = generate_digest_html(upcoming_events, unsubscribe_url)

        sent = await send_html_email(
            email,
            "DK24 Upcoming Community Events",
            html_content
        )

        if sent:
            logger.info("Digest sent to %s", email)
        else:
            logger.error("Failed to send digest to %s", email)

    logger.info("Event digest processing completed.")
