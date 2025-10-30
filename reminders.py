import datetime
from typing import List, Tuple, Optional

# Store reminders as (user_id, reminder_text, target_datetime)
reminders: List[Tuple[int, str, datetime.datetime]] = []

def add_reminder(user_id: int, reminder_text: str, target_time: datetime.datetime):
    """Add a reminder for a specific user"""
    reminders.append((user_id, reminder_text, target_time))
    print(f"Reminder added for user {user_id}: {reminder_text} at {target_time}")

def get_due_reminders() -> List[Tuple[int, str]]:
    """Get all reminders that are due now and remove them from the list"""
    now = datetime.datetime.now()
    due_reminders = []
    
    # Find due reminders
    for user_id, reminder_text, target_time in reminders[:]:  # Copy to avoid modification during iteration
        if target_time <= now:
            due_reminders.append((user_id, reminder_text))
            reminders.remove((user_id, reminder_text, target_time))
    
    return due_reminders

def parse_datetime_from_text(text: str) -> Optional[datetime.datetime]:
    """Simple datetime parsing - will be enhanced with AI"""
    now = datetime.datetime.now()
    
    # Default to 1 hour from now if no time specified
    return now + datetime.timedelta(hours=1)