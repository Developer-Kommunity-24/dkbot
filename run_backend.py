import asyncio
import logging
from db_client import DatabaseClient
import web_server
import config

logging.basicConfig(level=logging.INFO)

class DummyBot:
    def get_cog(self, name): return None

async def main():
    db = DatabaseClient()
    await db.async_init()
    
    # Seed fake events if empty or just unconditionally for testing
    fake_event = {
        "eventName": "TechBot Developer Meetup",
        "startDateTime": "2026-07-15T18:00:00",
        "endDateTime": "2026-07-15T20:00:00",
        "organizationName": "DK24",
        "eventLocation": "Mangalore Innovation Hub",
        "eventDescription": "Join us for an amazing developer meetup filled with tech talks and networking!"
    }
    fake_event_2 = {
        "eventName": "FOSS Hackathon",
        "startDateTime": "2026-08-10T09:00:00",
        "endDateTime": "2026-08-11T18:00:00",
        "organizationName": "FOSS United",
        "eventLocation": "Online",
        "eventDescription": "A 36-hour hackathon to build amazing open source tools."
    }
    
    # Add and approve them
    id1 = await db.async_add_event_submission(fake_event)
    await db.async_accept_event_submission(id1)
    
    id2 = await db.async_add_event_submission(fake_event_2)
    await db.async_accept_event_submission(id2)
    
    logging.info("Fake events have been seeded.")
    
    await web_server.start_web_server(DummyBot(), db)
    
    # keep alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
