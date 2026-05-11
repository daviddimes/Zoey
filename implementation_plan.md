# Implementation Plan: Reminder Functionality in Telegram Bot

## Overview
Add AI-powered reminder setting and notification via Telegram messages. Use OpenAI for intent classification and parsing, store reminders persistently in SQLite with background job checks, and send notifications when due. Includes user settings for timezones, support for listing/editing/deleting reminders, repeating reminders, and validations against past dates/duplicates. Assumes Central Time if timezone unclear.

## Steps
1. Write the implementation plan to a markdown file (e.g., `implementation_plan.md`) for reference during development. ✅ Completed
2. Update [requirements.txt](requirements.txt) to add `aiosqlite` and `pytz` for async DB and timezone handling.
3. Refactor [reminders.py](reminders.py) to use SQLite: create schemas for reminders (with repeat_interval, timezone) and user_settings; implement async functions for init_db, add_reminder (prevent past/duplicates), get_due_reminders (reschedule repeats), list_reminders, edit_reminder, delete_reminder, get_user_timezone, set_user_timezone.
4. Update [intents.py](intents.py) to add intents for LIST_REMINDERS, EDIT_REMINDER, DELETE_REMINDER; enhance `parse_reminder_details()` to include user timezone in AI prompt and support repeat parsing (e.g., "daily", "weekly"); modify `create_datetime_from_details()` to prevent past dates and apply user timezone.
5. Modify [messaging.py](messaging.py) to call `await init_db()` on startup; route new intents to handlers for listing/editing/deleting; add timezone prompting if unclear during reminder creation (ask user, store in DB); update `reminder_job()` to await `get_due_reminders()`.
6. Add local testing support: modify main() in [messaging.py](messaging.py) for polling mode toggle via command-line flag.
7. Deploy to Fly.io: validate secrets, add health checks, handle rollbacks; ensure DB file persists via volume mount.

## Further Considerations
1. Improve AI prompts for edge cases like relative times, long text (truncate to 200 chars), or invalid inputs; add rate-limiting for reminders.
2. Handle dependencies: audit versions periodically; ensure OpenAI API compatibility.
3. For repeating reminders, limit to daily/weekly; extend with more intervals if needed.
4. Add user confirmation for edits/deletes to prevent accidents.