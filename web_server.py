from aiohttp import web
import logging
import config

async def handle_get_approved_events(request):
    """Returns approved events for public calendar consumption."""
    try:
        sheets_client = request.app['sheets_client']
        events = await sheets_client.async_get_approved_events()
        return web.json_response({'events': events, 'count': len(events)})
    except Exception as e:
        logging.error(f"Error fetching approved events: {e}")
        return web.json_response(
            {'error': 'Failed to fetch approved events'},
            status=500,
        )

async def handle_new_applicant_webhook(request):
    """Handles incoming webhooks with new applicant data."""
    # Verify the secret key
    secret_key = request.headers.get('X-Secret-Key')
    if secret_key != config.WEBHOOK_SECRET_KEY:
        logging.warning("Received webhook with invalid secret key.")
        return web.Response(status=401, text="Unauthorized")

    try:
        data = await request.json()
        logging.info(f"Received valid webhook with data: {data}")

        # The bot and sheets_client instances are available via the web.Application
        bot = request.app['bot']
        sheets_client = request.app['sheets_client']
        
        # Extract required fields
        email = data.get(config.COL_EMAIL)
        first_name = data.get(config.COL_FIRST_NAME)

        if not email or not first_name:
            logging.error("Webhook data is missing required fields (email, firstName).")
            return web.Response(status=400, text="Bad Request: Missing required fields.")

        # Add to Google Sheet (Async)
        await sheets_client.async_add_individual_applicant(data)

        # Pass the data to the Cog to handle the Discord message
        cog = bot.get_cog('Applications')
        if cog:
            await cog.post_approval_card(data)
        else:
            logging.error("Applications Cog not found!")

        return web.Response(status=200, text="OK")

    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return web.Response(status=500, text="Internal Server Error")


async def handle_new_college_applicant_webhook(request):
    """Handles incoming webhooks with new college applicant data."""
    # Verify the secret key
    secret_key = request.headers.get('X-Secret-Key')
    if secret_key != config.WEBHOOK_SECRET_KEY:
        logging.warning("Received webhook with invalid secret key.")
        return web.Response(status=401, text="Unauthorized")

    try:
        data = await request.json()
        logging.info(f"Received valid webhook with college applicant data: {data}")

        # The bot instance is available via the web.Application
        bot = request.app['bot']
        sheets_client = request.app['sheets_client']

        # Add to Google Sheet (Async)
        await sheets_client.async_add_college_applicant(data)
        
        # Pass the data to the Cog to handle the Discord message
        cog = bot.get_cog('Applications')
        if cog:
            await cog.post_college_applicant_card(data)
        else:
            logging.error("Applications Cog not found!")

        return web.Response(status=200, text="OK")

    except Exception as e:
        logging.error(f"Error processing college applicant webhook: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_new_event_webhook(request):
    """Handles incoming webhooks with new event data."""
    # Verify the secret key
    secret_key = request.headers.get('X-Secret-Key')
    if secret_key != config.WEBHOOK_SECRET_KEY:
        logging.warning("Received event webhook with invalid secret key.")
        return web.Response(status=401, text="Unauthorized")

    try:
        data = await request.json()
        logging.info(f"Received valid event webhook with data: {data}")

        bot = request.app['bot']
        sheets_client = request.app['sheets_client']

        # Add to Google Sheet and get the unique ID (Async)
        event_id = await sheets_client.async_add_event_submission(data)

        if event_id:
            # Pass the data and ID to the Cog to handle the Discord message
            cog = bot.get_cog('Events')
            if cog:
                await cog.post_event_approval_card(data, event_id)
            else:
                logging.error("Events Cog not found!")
                
            return web.Response(status=200, text="OK")
        else:
            return web.Response(status=500, text="Internal Server Error: Failed to add event to sheet.")

    except Exception as e:
        logging.error(f"Error processing event webhook: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def start_web_server(bot, sheets_client):
    """Initializes and starts the aiohttp web server."""
    app = web.Application()
    app['bot'] = bot  # Make the bot instance available to request handlers
    app['sheets_client'] = sheets_client # Make the sheets_client instance available
    app.router.add_get('/api/events', handle_get_approved_events)
    app.router.add_post('/api/new-applicant', handle_new_applicant_webhook)
    app.router.add_post('/api/new-college-applicant', handle_new_college_applicant_webhook)
    app.router.add_post('/api/new-event', handle_new_event_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.WEB_SERVER_PORT)
    
    try:
        await site.start()
        logging.info(f"✅ Web server started on port {config.WEB_SERVER_PORT}")
    except Exception as e:
        logging.error(f"❌ Failed to start web server: {e}")
