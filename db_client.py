import logging
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
import json
import config
import string
import random
import asyncio
from datetime import datetime
from urllib.parse import urlparse, unquote
import hashlib
import secrets
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_random_id(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def _parse_tags(raw_tags):
    if isinstance(raw_tags, list):
        return [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    if isinstance(raw_tags, str):
        return [tag.strip() for tag in raw_tags.split(',') if tag.strip()]
    return []

def _to_public_event(row):
    if not row:
        return None

    data = row['data']
    if isinstance(data, str):
        data = json.loads(data)

    start_date_time = data.get('startDateTime')
    end_date_time = data.get('endDateTime')
    organization_name = data.get('organizationName', '')
    is_dk24 = organization_name == 'DK24'

    try:
        start_dt = datetime.fromisoformat(start_date_time)
        end_dt = datetime.fromisoformat(end_date_time)
    except (TypeError, ValueError):
        return None

    return {
        'id': row['id'],
        'title': data.get('eventName', ''),
        'startDateTime': start_dt.isoformat(),
        'endDateTime': end_dt.isoformat(),
        'time': start_dt.strftime('%H:%M'),
        'location': data.get('eventLocation', ''),
        'description': data.get('eventDescription', ''),
        'registrationLink': data.get('registrationLink', '') or '',
        'joinLink': data.get('eventWebsite', '') or '',
        'icon': 'calendar',
        'highlight': is_dk24,
        'youtubeLink': '',
        'color': 'green' if is_dk24 else 'gray',
        'organizationName': organization_name,
        'posterUrl': data.get('eventPosterUrl', '') or '',
        'tags': _parse_tags(data.get('eventTags', [])),
    }

class DatabaseClient:
    def __init__(self):
        self.pool = None

    async def async_init(self):
        # Run synchronous initialization in a thread to keep the Discord bot non-blocking
        await asyncio.to_thread(self._init_sync)

    def _init_sync(self):
        try:
            parsed = urlparse(config.DATABASE_URL)
            password = unquote(parsed.password) if parsed.password else None
            
            # Extract database name (path.lstrip removes the leading slash)
            db_name = parsed.path.lstrip('/') if parsed.path else 'postgres'

            self.pool = SimpleConnectionPool(
                1, 20,
                user=parsed.username,
                password=password,
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=db_name
            )
            self._create_tables()
            logging.info("✅ Successfully connected to PostgreSQL Database using psycopg2.")
        except Exception as e:
            logging.error(f"❌ Failed to connect to Database: {e}")
            raise

    def _create_tables(self):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS individuals (
                        email VARCHAR PRIMARY KEY,
                        data JSONB,
                        accepted VARCHAR DEFAULT 'pending',
                        responded VARCHAR DEFAULT 'no',
                        role_claimed VARCHAR DEFAULT 'no'
                    );

                    CREATE TABLE IF NOT EXISTS colleges (
                        id SERIAL PRIMARY KEY,
                        data JSONB,
                        responded VARCHAR DEFAULT 'no'
                    );

                    CREATE TABLE IF NOT EXISTS events (
                        id VARCHAR PRIMARY KEY,
                        data JSONB,
                        status VARCHAR DEFAULT 'pending'
                    );

                    CREATE TABLE IF NOT EXISTS user_xp (
                        user_id VARCHAR PRIMARY KEY,
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        last_message TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS email_subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    unsubscribed_at TIMESTAMP WITH TIME ZONE,
    unsubscribe_token_hash VARCHAR(64) UNIQUE
);
CREATE TABLE IF NOT EXISTS email_unsubscribe_tokens (
    id SERIAL PRIMARY KEY,
    subscriber_id INTEGER NOT NULL REFERENCES email_subscribers(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE
);
ALTER TABLE email_subscribers
ADD COLUMN IF NOT EXISTS unsubscribe_token_hash VARCHAR(64) UNIQUE;
                ''')
                conn.commit()
        finally:
            self.pool.putconn(conn)

    # --- Async wrappers for database execution ---
    async def _execute(self, query, *args):
        return await asyncio.to_thread(self._execute_sync, query, args)

    def _execute_sync(self, query, args):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, args)
                conn.commit()
                return cur.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    async def _fetch(self, query, *args):
        return await asyncio.to_thread(self._fetch_sync, query, args)

    def _fetch_sync(self, query, args):
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, args)
                rows = cur.fetchall()
                conn.commit()
                return rows
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    async def _fetchrow(self, query, *args):
        return await asyncio.to_thread(self._fetchrow_sync, query, args)

    def _fetchrow_sync(self, query, args):
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, args)
                row = cur.fetchone()
                conn.commit()
                return row
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    async def _fetchval(self, query, *args):
        return await asyncio.to_thread(self._fetchval_sync, query, args)

    def _fetchval_sync(self, query, args):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, args)
                row = cur.fetchone()
                conn.commit()
                return row[0] if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    def _row_to_dict(self, row):
        if not row:
            return None
        # row is a RealDictCursor, so row['data'] is typically a dict if psycopg2 JSON is configured,
        # but let's handle string parsing just in case
        d = row['data']
        if isinstance(d, str):
            d = json.loads(d)
            
        if 'accepted' in row:
            d['accepted'] = row['accepted']
        if 'responded' in row:
            d['responded'] = row['responded']
        if 'role_claimed' in row:
            d['roleClaimed'] = row['role_claimed']
        return d

    # --- Async Public Methods ---

    async def async_add_individual_applicant(self, data: dict):
        email = data.get(config.COL_EMAIL)
        if not email:
            return False
        await self._execute(
            'INSERT INTO individuals (email, data) VALUES (%s, %s) ON CONFLICT (email) DO UPDATE SET data = EXCLUDED.data',
            email, json.dumps(data)
        )
        return True

    async def async_add_college_applicant(self, data: dict):
        await self._execute('INSERT INTO colleges (data) VALUES (%s)', json.dumps(data))
        return True

    async def async_add_event_submission(self, data: dict) -> str:
        event_id = generate_random_id()
        data['ID'] = event_id
        await self._execute(
            'INSERT INTO events (id, data, status) VALUES (%s, %s, %s)',
            event_id, json.dumps(data), 'pending'
        )
        return event_id

    async def async_accept_event_submission(self, event_id: str) -> bool:
        res = await self._execute("UPDATE events SET status = 'accepted' WHERE id = %s", event_id)
        return res > 0

    async def async_reject_event_submission(self, event_id: str) -> bool:
        res = await self._execute("UPDATE events SET status = 'rejected' WHERE id = %s", event_id)
        return res > 0

    async def async_revert_rejection(self, event_id: str) -> bool:
        res = await self._execute("UPDATE events SET status = 'pending' WHERE id = %s", event_id)
        return res > 0

    async def async_get_approved_events(self):
        rows = await self._fetch(
            "SELECT id, data FROM events WHERE status = 'accepted' ORDER BY data->>'startDateTime' ASC"
        )
        events = [_to_public_event(row) for row in rows]
        return [event for event in events if event is not None]

    async def async_get_all_records(self):
        rows = await self._fetch('SELECT * FROM individuals')
        return [self._row_to_dict(row) for row in rows]

    async def async_get_record_by_email(self, email: str):
        row = await self._fetchrow('SELECT * FROM individuals WHERE email = %s', email)
        return self._row_to_dict(row) if row else None

    async def async_update_status_by_email(self, email: str, status: str) -> bool:
        res = await self._execute(
            "UPDATE individuals SET accepted = %s, responded = 'yes' WHERE email = %s",
            status, email
        )
        return res > 0

    async def async_claim_role_by_email(self, email: str) -> bool:
        res = await self._execute(
            "UPDATE individuals SET role_claimed = 'yes' WHERE email = %s",
            email
        )
        return res > 0
        
    async def async_mark_responded(self, email: str) -> bool:
        res = await self._execute(
            "UPDATE individuals SET responded = 'yes' WHERE email = %s",
            email
        )
        return res > 0

    
    async def async_subscribe_email(self, email: str):
        email = (email or "").strip().lower()

        existing = await self._fetchrow(
            """
            SELECT id, email, is_active
            FROM email_subscribers
            WHERE email = %s
            """,
            email,
        )

        if existing and existing["is_active"]:
            return {
                **dict(existing),
                "status": "already_subscribed",
            }

        row = await self._fetchrow(
            """
            INSERT INTO email_subscribers
                (email, is_active, unsubscribed_at)
            VALUES (%s, TRUE, NULL)
            ON CONFLICT (email)
            DO UPDATE SET
                is_active = TRUE,
                unsubscribed_at = NULL
            RETURNING id, email, is_active
            """,
            email,
        )

        if not row:
            return None

        return {
            **dict(row),
            "status": "subscribed",
        }


    async def async_get_active_email_subscribers(self):
        return await self._fetch(
            """
            SELECT id, email
            FROM email_subscribers
            WHERE is_active = TRUE
            ORDER BY created_at ASC
            """
        )

    async def async_get_digest_recipients(self):
        subscribers = await self.async_get_active_email_subscribers()
        recipients = []

        for subscriber in subscribers:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            await self._execute(
                """
                INSERT INTO email_unsubscribe_tokens
                    (subscriber_id, token_hash, expires_at)
                VALUES (
                    %s,
                    %s,
                    CURRENT_TIMESTAMP + INTERVAL '365 days'
                )
                """,
                subscriber["id"],
                token_hash
            )

            recipients.append({
                "email": subscriber["email"],
                "unsubscribe_token": token
            })

        return recipients

    async def async_unsubscribe_email(self, token: str):
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        return await asyncio.to_thread(
            self._unsubscribe_email_sync,
            token_hash
        )

    def _unsubscribe_email_sync(self, token_hash: str):
        conn = self.pool.getconn()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT t.id, s.id
                    FROM email_unsubscribe_tokens t
                    JOIN email_subscribers s
                        ON s.id = t.subscriber_id
                    WHERE t.token_hash = %s
                        AND t.used_at IS NULL
                        AND t.expires_at > CURRENT_TIMESTAMP
                        AND s.is_active = TRUE
                    FOR UPDATE OF t, s
                    """,
                    (token_hash,)
                )

                row = cur.fetchone()

                if not row:
                    conn.rollback()
                    return False

                token_id, subscriber_id = row

                cur.execute(
                    """
                    UPDATE email_subscribers
                    SET is_active = FALSE,
                        unsubscribed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (subscriber_id,)
                )

                cur.execute(
                    """
                    UPDATE email_unsubscribe_tokens
                    SET used_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (token_id,)
                )

                conn.commit()
                return True

        except Exception:
            conn.rollback()
            raise

        finally:
            self.pool.putconn(conn)
    async def async_get_records_by_status(self, status: str):
        rows = await self._fetch('SELECT * FROM individuals WHERE accepted = %s', status)
        return [self._row_to_dict(row) for row in rows]

    async def async_search_records(self, query: str):
        search_term = f"%{query}%"
        rows = await self._fetch(
            "SELECT * FROM individuals WHERE data->>'firstName' ILIKE %s OR data->>'lastName' ILIKE %s OR email ILIKE %s",
            search_term, search_term, search_term
        )
        return [self._row_to_dict(row) for row in rows]

    async def async_get_stats(self):
        approved = await self._fetchval("SELECT COUNT(*) FROM individuals WHERE accepted = 'yes'")
        rejected = await self._fetchval("SELECT COUNT(*) FROM individuals WHERE accepted = 'no'")
        pending = await self._fetchval("SELECT COUNT(*) FROM individuals WHERE accepted = 'pending'")
        total = await self._fetchval("SELECT COUNT(*) FROM individuals")
        return {
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'total': total
        }
