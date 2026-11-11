
import asyncio
import logging

import config
from db_client import DatabaseClient
from digest_email import send_event_digest


async def main():
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing")

    if not config.GMAIL_API_TOKEN_BASE64:
        raise RuntimeError("GMAIL_API_TOKEN_BASE64 is missing")

    if not config.UNSUBSCRIBE_URL:
        raise RuntimeError("UNSUBSCRIBE_URL is missing")

    if not config.UNSUBSCRIBE_URL.startswith("https://"):
        raise RuntimeError("UNSUBSCRIBE_URL must use HTTPS")

    database = DatabaseClient()

    try:
        await database.async_init()
        await send_event_digest(database)
    finally:
        if database.pool:
            database.pool.closeall()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
