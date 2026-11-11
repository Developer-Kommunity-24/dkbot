import asyncio
import logging

from aiohttp import web

import config
from db_client import DatabaseClient
import web_server


logging.basicConfig(level=logging.INFO)


async def main():
    database = DatabaseClient()
    await database.async_init()

    app = web.Application()
    app["sheets_client"] = database

    app.router.add_post(
        "/api/email-subscriptions",
        web_server.handle_subscribe_email
    )
    app.router.add_get(
        "/api/email-subscriptions",
        web_server.handle_get_active_subscribers
    )
    app.router.add_post(
        "/api/email-subscriptions/digest-recipients",
        web_server.handle_get_digest_recipients
    )
    app.router.add_get(
        "/api/email-subscriptions/unsubscribe",
        web_server.handle_unsubscribe_email
    )
    app.router.add_post(
        "/api/email-subscriptions/unsubscribe",
        web_server.handle_unsubscribe_email_post
    )

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
         "0.0.0.0",
        config.WEB_SERVER_PORT
    )

    await site.start()

    logging.info(
        "Email API server running on port %s",
        config.WEB_SERVER_PORT
    )

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        database.pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
