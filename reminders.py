import datetime

reminders = []

def add_reminder(reminder, time):
    reminders.append((reminder, time))
    print(f"Reminder added: {reminder} at {time}")

def show_reminders():
    now = datetime.datetime.now()
    for reminder, time in reminders:
        if time > now:
            print(f"Upcoming reminder: {reminder} at {time}")

def check_reminders():
    now = datetime.datetime.now()
    for reminder, time in reminders:
        if time <= now:
            print(f"Reminder: {reminder}")
            reminders.remove((reminder, time))