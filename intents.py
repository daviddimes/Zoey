import os
import datetime
import json
import pytz
from openai import AsyncOpenAI
from reminders import (
    add_reminder,
    get_user_timezone,
    set_user_timezone,
    list_reminders,
    edit_reminder,
    delete_reminder,
)

def get_client():
    """Create and return AsyncOpenAI client lazily."""
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def determine_intent(user_message):
    """Use AI to determine what the user wants to do."""
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Classify intent. Respond with only one word: REMINDER, LIST_REMINDERS, EDIT_REMINDER, DELETE_REMINDER, or CHAT.\n\nREMINDER = User wants to create a new reminder\nLIST_REMINDERS = User wants to see their existing reminders\nEDIT_REMINDER = User wants to modify an existing reminder\nDELETE_REMINDER = User wants to remove an existing reminder\nCHAT = Everything else.\n\nExamples:\n'What's a good drink at Starbucks?' → CHAT\n'Recommend a book' → CHAT\n'I'm on PTO today' → CHAT\n'Tell me about yourself' → CHAT\n'What time is it' → CHAT\n'Remind me to call mom at 3pm tomorrow' → REMINDER\n'Set a reminder for my meeting tomorrow' → REMINDER\n'Don't let me forget to buy milk' → REMINDER\n'Ping me in an hour' → REMINDER\n'Alert me when it's 5pm' → REMINDER\n'Show me my reminders' → LIST_REMINDERS\n'List my reminders' → LIST_REMINDERS\n'What reminders do I have?' → LIST_REMINDERS\n'Edit reminder 1 to call dad' → EDIT_REMINDER\n'Change my 3pm reminder' → EDIT_REMINDER\n'Delete reminder 2' → DELETE_REMINDER\n'Remove the milk reminder' → DELETE_REMINDER"
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=10,
            temperature=0,
        )
        intent = response.choices[0].message.content.strip().upper()
        return intent if intent in [
            'REMINDER',
            'LIST_REMINDERS',
            'EDIT_REMINDER',
            'DELETE_REMINDER',
            'CHAT',
        ] else 'CHAT'
    except:
        return 'CHAT'

async def parse_reminder_details(user_message, user_id):
    """Use AI to extract date, time, reminder text, repeat pattern, and timezone."""
    try:
        client = get_client()
        now = datetime.datetime.now()
        current_time_info = f"Current date and time: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')})"
        user_tz = await get_user_timezone(user_id)
        tz_info = f"User timezone: {user_tz}"

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""Extract reminder details from the user's message. Respond with JSON only, with no surrounding markdown. Use this schema:\n{{\n  \"reminder_text\": \"what to remind about\",\n  \"date\": \"YYYY-MM-DD or 'today' or 'tomorrow'\",\n  \"time\": \"HH:MM (24-hour)\",\n  \"repeat\": \"daily\", \"weekly\", or null,\n  \"timezone\": \"IANA timezone name like America/New_York or null\"\n}}\n{current_time_info}\n{tz_info}\nIf no reminder text is specified, use \"Reminder\". If no date is specified, use \"today\". If no time is specified, use current time + 1 hour in the user's timezone. If no repeat is specified, use null. If no timezone is explicitly specified, use null.\n\nExamples:\n\"Remind me at 3pm tomorrow\" -> {{\"reminder_text\": \"Reminder\", \"date\": \"tomorrow\", \"time\": \"15:00\", \"repeat\": null, \"timezone\": null}}\n\"Call mom at 2:30\" -> {{\"reminder_text\": \"Call mom\", \"date\": \"today\", \"time\": \"14:30\", \"repeat\": null, \"timezone\": null}}\n\"Remind me daily to take my meds at 8am\" -> {{\"reminder_text\": \"Take my meds\", \"date\": \"today\", \"time\": \"08:00\", \"repeat\": \"daily\", \"timezone\": null}}\n\"Set a weekly reminder for team meeting every Monday at 10am\" -> {{\"reminder_text\": \"Team meeting\", \"date\": \"2026-05-12\", \"time\": \"10:00\", \"repeat\": \"weekly\", \"timezone\": null}}\n\"Set a reminder for 5pm Eastern\" -> {{\"reminder_text\": \"Reminder\", \"date\": \"today\", \"time\": \"17:00\", \"repeat\": null, \"timezone\": \"America/New_York\"}}"""
                },
                {"role": "user", "content": user_message},
            ],
            max_tokens=150,
            temperature=0,
        )
        details = json.loads(response.choices[0].message.content.strip())
        return details
    except Exception as e:
        print(f"Error parsing reminder details: {e}")
        return None

async def parse_reminder_edit_details(user_message, user_id):
    """Use AI to extract edit details from a reminder update request."""
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Extract reminder edit details from the user's message. Respond with JSON only, using this schema:\n{\n  \"reminder_id\": integer or null,\n  \"new_text\": string or null,\n  \"new_date\": \"YYYY-MM-DD\" or 'today' or 'tomorrow' or null,\n  \"new_time\": \"HH:MM\" or null,\n  \"new_repeat\": \"daily\" or \"weekly\" or \"none\" or null\n}"
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=150,
            temperature=0,
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"Error parsing edit details: {e}")
        return None

async def parse_reminder_delete_details(user_message, user_id):
    """Use AI to extract the reminder ID from a delete request."""
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Extract the reminder ID from the user's message. Respond with JSON only, using this schema:\n{\n  \"reminder_id\": integer or null\n}"
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=50,
            temperature=0,
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"Error parsing delete details: {e}")
        return None


def create_datetime_from_details(date_str, time_str, timezone_str='UTC'):
    """Convert parsed date/time strings into a timezone-aware datetime."""
    try:
        tz = pytz.timezone(timezone_str)
    except Exception:
        tz = pytz.UTC

    now_local = datetime.datetime.now(tz)

    if isinstance(date_str, str) and date_str.lower() == 'today':
        target_date = now_local.date()
    elif isinstance(date_str, str) and date_str.lower() == 'tomorrow':
        target_date = now_local.date() + datetime.timedelta(days=1)
    else:
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return None

    target_time = None
    if isinstance(time_str, str):
        try:
            hour, minute = map(int, time_str.split(':'))
            target_time = datetime.time(hour, minute)
        except Exception:
            target_time = None

    if target_time is None:
        future_local = now_local + datetime.timedelta(hours=1)
        target_date = future_local.date()
        target_time = future_local.time()

    target_naive = datetime.datetime.combine(target_date, target_time)
    try:
        if hasattr(tz, 'localize'):
            target_datetime = tz.localize(target_naive)
        else:
            target_datetime = target_naive.replace(tzinfo=tz)
    except Exception:
        target_datetime = target_naive.replace(tzinfo=pytz.UTC)

    if target_datetime <= now_local:
        if isinstance(date_str, str) and date_str.lower() == 'today':
            target_datetime += datetime.timedelta(days=1)
        else:
            return None

    return target_datetime

async def handle_reminder(user_message, user_id):
    """Handle reminder creation requests."""
    try:
        details = await parse_reminder_details(user_message, user_id)
        if not details:
            return "Sorry, I couldn't understand that reminder. Try something like 'Remind me to call mom at 3pm tomorrow'."

        reminder_text = details.get('reminder_text') or 'Reminder'
        date_str = details.get('date') or 'today'
        time_str = details.get('time') or ''
        repeat = details.get('repeat')
        timezone_hint = details.get('timezone')

        user_tz = await get_user_timezone(user_id)
        timezone_to_use = timezone_hint or user_tz or 'UTC'

        if timezone_hint and timezone_hint != user_tz:
            try:
                pytz.timezone(timezone_hint)
                await set_user_timezone(user_id, timezone_hint)
                user_tz = timezone_hint
            except Exception:
                timezone_to_use = user_tz

        target_datetime = create_datetime_from_details(date_str, time_str, timezone_to_use)
        if not target_datetime:
            return 'I could not schedule that reminder because the date/time looked invalid or was already in the past. Try again with a different date or time.'

        success = await add_reminder(user_id, reminder_text, target_datetime, repeat)
        if not success:
            return 'I could not create the reminder. It may already exist or it may be scheduled in the past.'

        friendly_time = target_datetime.strftime('%B %d at %I:%M %p %Z')
        repeat_text = f' repeating {repeat}' if repeat else ''
        timezone_hint_text = ''
        if user_tz == 'UTC' and not timezone_hint:
            timezone_hint_text = ' Tip: you can set your timezone with a message like "Set my timezone to America/New_York".'

        return f"✅ Reminder set: '{reminder_text}' on {friendly_time}{repeat_text}.{timezone_hint_text}"
    except Exception as e:
        print(f"Error handling reminder: {e}")
        return "Sorry, I couldn't set that reminder. Try something like 'Remind me to call mom at 3pm tomorrow'."

async def handle_list_reminders(user_id):
    """Return the user's current reminders."""
    try:
        reminders_data = await list_reminders(user_id)
        if not reminders_data:
            return 'You have no reminders yet. Ask me to set one!'

        lines = ['Your reminders:']
        for reminder in reminders_data:
            repeat_note = f' (repeats {reminder["repeat"]})' if reminder['repeat'] else ''
            lines.append(
                f"ID {reminder['id']}: {reminder['text']} at {reminder['datetime']}{repeat_note}"
            )
        return '\n'.join(lines)
    except Exception as e:
        print(f"Error listing reminders: {e}")
        return 'Sorry, I could not fetch your reminders right now.'

async def handle_edit_reminder(user_message, user_id):
    """Handle reminder edit requests."""
    try:
        details = await parse_reminder_edit_details(user_message, user_id)
        if not details or details.get('reminder_id') is None:
            return 'Please include the reminder ID you want to edit, for example: "Edit reminder 2 to call dad tomorrow at 3pm."'

        reminder_id = int(details['reminder_id'])
        new_text = details.get('new_text') or None
        new_date = details.get('new_date')
        new_time = details.get('new_time')
        raw_repeat = details.get('new_repeat')
        new_repeat = None
        if raw_repeat is not None:
            if isinstance(raw_repeat, str) and raw_repeat.lower() == 'none':
                new_repeat = 'none'
            elif raw_repeat in ('daily', 'weekly'):
                new_repeat = raw_repeat

        new_datetime = None
        if new_date or new_time:
            user_tz = await get_user_timezone(user_id)
            if not new_time:
                now_tz = pytz.timezone(user_tz)
                new_time = datetime.datetime.now(now_tz).strftime('%H:%M')
            new_datetime = create_datetime_from_details(new_date or 'today', new_time, user_tz)
            if not new_datetime:
                return 'I could not interpret the new date or time. Please try again with a valid date and time.'

        success = await edit_reminder(user_id, reminder_id, new_text, new_datetime, new_repeat)
        if not success:
            return 'I could not update that reminder. Make sure the reminder ID is correct and try again.'

        return '✅ Reminder updated successfully.'
    except Exception as e:
        print(f"Error editing reminder: {e}")
        return 'Sorry, I could not edit that reminder.'

async def handle_delete_reminder(user_message, user_id):
    """Handle reminder deletion requests."""
    try:
        details = await parse_reminder_delete_details(user_message, user_id)
        if not details or details.get('reminder_id') is None:
            return 'Please include the reminder ID you want to delete, for example: "Delete reminder 2."'

        reminder_id = int(details['reminder_id'])
        success = await delete_reminder(user_id, reminder_id)
        if not success:
            return 'I could not delete that reminder. Verify the reminder ID and try again.'

        return '✅ Reminder deleted.'
    except Exception as e:
        print(f"Error deleting reminder: {e}")
        return 'Sorry, I could not delete that reminder.'

async def handle_chat(user_message):
    """Handle regular chat requests."""
    try:
        client = get_client()
        now = datetime.datetime.now()
        current_time_info = f"Current date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}"

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"You are Zoey, a helpful personal assistant. Keep responses brief and friendly.\n\n{current_time_info}"
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=100,
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return 'Sorry, I had trouble understanding that.'
