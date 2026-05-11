import asyncio
import aiosqlite
import datetime
import pytz
from typing import List, Tuple, Optional, Dict

DB_PATH = 'zoey.db'

async def init_db():
    """Initialize the database and create tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reminder_text TEXT NOT NULL,
                target_datetime TEXT NOT NULL,  -- UTC ISO format (e.g., '2026-05-12T15:30:00')
                repeat_interval TEXT CHECK(repeat_interval IN ('daily', 'weekly')) OR repeat_interval IS NULL,
                timezone TEXT NOT NULL DEFAULT 'UTC',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, reminder_text)  -- Prevent duplicate texts per user
            )
        ''')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_user_datetime ON reminders(user_id, target_datetime)')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT NOT NULL DEFAULT 'UTC'
            )
        ''')
        await db.commit()

async def get_user_timezone(user_id: int) -> str:
    """Get user's timezone, default to UTC."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT timezone FROM user_settings WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 'UTC'

async def set_user_timezone(user_id: int, timezone: str):
    """Set or update user's timezone."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR REPLACE INTO user_settings (user_id, timezone) VALUES (?, ?)', (user_id, timezone))
        await db.commit()

async def add_reminder(user_id: int, reminder_text: str, target_time: datetime.datetime, repeat_interval: Optional[str] = None) -> bool:
    """Add a reminder. Validates against past dates and duplicates. target_time should be timezone-aware."""
    now = datetime.datetime.now(pytz.UTC)
    if target_time <= now:
        return False  # Prevent past reminders
    tz = await get_user_timezone(user_id)
    utc_time = target_time.astimezone(pytz.UTC)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO reminders (user_id, reminder_text, target_datetime, repeat_interval, timezone)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, reminder_text, utc_time.isoformat(), repeat_interval, tz))
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False  # Duplicate text

async def get_due_reminders() -> List[Tuple[int, str]]:
    """Get due reminders, reschedule repeats, and delete non-repeats."""
    now = datetime.datetime.now(pytz.UTC)
    due = []
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id, user_id, reminder_text, target_datetime, repeat_interval FROM reminders WHERE target_datetime <= ?', (now.isoformat(),))
        rows = await cursor.fetchall()
        for row in rows:
            rid, uid, text, dt_str, repeat = row
            due.append((uid, text))
            if repeat:
                # Reschedule next occurrence
                dt = datetime.datetime.fromisoformat(dt_str).replace(tzinfo=pytz.UTC)
                if repeat == 'daily':
                    next_dt = dt + datetime.timedelta(days=1)
                elif repeat == 'weekly':
                    next_dt = dt + datetime.timedelta(weeks=1)
                await db.execute('UPDATE reminders SET target_datetime = ? WHERE id = ?', (next_dt.isoformat(), rid))
            else:
                await db.execute('DELETE FROM reminders WHERE id = ?', (rid,))
        await db.commit()
    return due

async def list_reminders(user_id: int) -> List[Dict]:
    """List all reminders for a user, with local timezone display."""
    tz_str = await get_user_timezone(user_id)
    tz = pytz.timezone(tz_str)
    reminders = []
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id, reminder_text, target_datetime, repeat_interval FROM reminders WHERE user_id = ? ORDER BY target_datetime', (user_id,))
        rows = await cursor.fetchall()
        for row in rows:
            rid, text, dt_str, repeat = row
            dt_utc = datetime.datetime.fromisoformat(dt_str).replace(tzinfo=pytz.UTC)
            dt_local = dt_utc.astimezone(tz)
            reminders.append({
                'id': rid,
                'text': text,
                'datetime': dt_local.strftime('%Y-%m-%d %H:%M %Z'),
                'repeat': repeat
            })
    return reminders

async def edit_reminder(user_id: int, reminder_id: int, new_text: Optional[str] = None, new_datetime: Optional[datetime.datetime] = None, new_repeat: Optional[str] = None) -> bool:
    """Edit a reminder. Validates ownership and past dates."""
    updates = []
    params = []
    if new_text:
        updates.append('reminder_text = ?')
        params.append(new_text)
    if new_datetime:
        now = datetime.datetime.now(pytz.UTC)
        if new_datetime <= now:
            return False
        updates.append('target_datetime = ?')
        params.append(new_datetime.astimezone(pytz.UTC).isoformat())
    if new_repeat is not None:
        updates.append('repeat_interval = ?')
        params.append(new_repeat)
    if not updates:
        return False
    params.append(reminder_id)
    params.append(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f'UPDATE reminders SET {", ".join(updates)} WHERE id = ? AND user_id = ?', params)
        await db.commit()
        return db.total_changes > 0

async def delete_reminder(user_id: int, reminder_id: int) -> bool:
    """Delete a reminder by ID, checking ownership."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM reminders WHERE id = ? AND user_id = ?', (reminder_id, user_id))
        await db.commit()
        return db.total_changes > 0