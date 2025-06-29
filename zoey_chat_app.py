import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
from memory.memory_utils import (
    load_memory,
    save_memory,
    remember,
    forget,
    list_memory,
    should_remember,
    convert_to_third_person
)
import sys
import os
import threading
import re
import datetime
import requests

print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("Listing models directory:")
print(os.listdir("models"))

# System prompt
system_message = (
    "You are Zoey. You are a friendly, casual, and helpful assistant. You always let the user lead the conversation. "
    "You do not ask questions unless directly asked. You do not offer your opinions unless they are specifically requested "
    "or directly relevant to the current topic. You never go off topic. You do not mention being an AI. "
    "You respond clearly and efficiently. You avoid rambling, repetition, or adding fluff. "
    "You only act when spoken to, and you only talk about what the user is talking about. "
    "Before answering, you silently think through your response, then reply clearly and intelligently. "
    "Only mention facts from your memory if they are directly relevant to the user's current message or question. "
    "Do not bring up unrelated memories."
)

# Load memory (initial, but always reload from file before displaying)
memory = load_memory()
history = []
last_thinking_step = ""
reminders = []

root = tk.Tk()
root.title("Zoey AI")
root.geometry("750x540")
root.configure(bg="#181a1b")  # Dark background

# --- Reminders Frame ---
reminders_frame = tk.Frame(root, bg="#181a1b")
reminders_canvas = tk.Canvas(reminders_frame, width=580, height=400, bg="#232526", highlightthickness=0)
reminders_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
reminders_scrollbar = tk.Scrollbar(reminders_frame, orient="vertical", command=reminders_canvas.yview, bg="#232526", troughcolor="#232526", activebackground="#444")
reminders_scrollbar.pack(side="right", fill="y")
reminders_canvas.configure(yscrollcommand=reminders_scrollbar.set)
reminders_canvas.bind("<Configure>", lambda e: reminders_canvas.configure(scrollregion=reminders_canvas.bbox("all")))
reminders_inner_frame = tk.Frame(reminders_canvas, bg="#232526")
reminders_canvas.create_window((0, 0), window=reminders_inner_frame, anchor="nw")

def update_reminders_view():
    for widget in reminders_inner_frame.winfo_children():
        widget.destroy()
    if reminders:
        for reminder in reminders:
            row = tk.Frame(reminders_inner_frame, bg="#232526")
            label = tk.Label(row, text=f"• {reminder}", anchor="w", justify="left", wraplength=460, bg="#232526", fg="#e0e0e0", font=("Segoe UI", 11))
            row.pack(fill="x", pady=2)
            label.pack(side="left", fill="x", expand=True)
    else:
        tk.Label(reminders_inner_frame, text="No reminders set yet.", bg="#232526", fg="#888", font=("Segoe UI", 11, "italic")).pack(pady=10)

# Handle memory commands
def update_memory_from_input(user_input):
    lowered = user_input.lower()
    if lowered.startswith("remember this:"):
        fact = user_input[len("remember this:"):].strip()
        return remember(memory, fact)
    elif lowered == "what do you remember?":
        return list_memory(memory)
    elif lowered.startswith("forget:"):
        text = user_input[len("forget:"):].strip()
        return forget(memory, text)
    return None

# Build prompt with simulated thinking
def build_prompt(user_input):
    history.append(f"David: {user_input}")
    recent = "\n".join(history[-6:])
    memory_summary = ""
    if memory:
        memory_summary = "\nZoey’s memory:\n" + "\n".join(f"- {v}" for v in memory.values()) + "\n"
    return (
        f"{system_message}{memory_summary}\n{recent}\n"
        f"# Thinking step:\n(Think carefully about David's message and prepare a useful, clear, and detailed response. Feel free to elaborate and provide more information when helpful.)\n\n"
        f"Zoey:"
    )

# --- GUI ---

# Sidebar
sidebar = tk.Frame(root, width=150, bg="#1a1c1e")
sidebar.pack(side="left", fill="y")

def switch_to_chat():
    reminders_frame.pack_forget()
    chat_frame.pack(fill="both", expand=True)

def switch_to_memory():
    global memory
    memory = load_memory()  # Always reload from file
    update_memory_view()
    chat_frame.pack_forget()
    reminders_frame.pack_forget()
    memory_frame.pack(fill="both", expand=True)
    memory_canvas.yview_moveto(0)

def switch_to_reminders():
    update_reminders_view()
    chat_frame.pack_forget()
    memory_frame.pack_forget()
    reminders_frame.pack(fill="both", expand=True)

tk.Button(sidebar, text="💬 Chat", command=switch_to_chat, height=2, width=20, bg="#1a1c1e", fg="#fff", font=("Segoe UI", 11, "bold"), bd=0, activebackground="#232526").pack(pady=(20, 5))
tk.Button(sidebar, text="🧠 Memory", command=switch_to_memory, height=2, width=20, bg="#1a1c1e", fg="#fff", font=("Segoe UI", 11, "bold"), bd=0, activebackground="#232526").pack(pady=5)
tk.Button(sidebar, text="Reminders", command=switch_to_reminders, height=2, width=20, bg="#1a1c1e", fg="#fff", font=("Segoe UI", 11, "bold"), bd=0, activebackground="#232526").pack(pady=5)

# Chat Frame
chat_frame = tk.Frame(root, bg="#181a1b")
chat_box = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, width=60, height=20, bg="#232526", fg="#e0e0e0", font=("Segoe UI", 11), bd=0, highlightthickness=1, highlightbackground="#232526")
chat_box.pack(padx=10, pady=10)
user_entry = tk.Entry(chat_frame, width=40, bg="#232526", fg="#e0e0e0", font=("Segoe UI", 11), bd=1, relief="flat", highlightthickness=1, highlightbackground="#232526")
user_entry.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))

def send_message():
    global last_thinking_step
    user_input = user_entry.get().strip()
    if not user_input:
        return
    chat_box.insert(tk.END, f"You: {user_input}\n")
    user_entry.delete(0, tk.END)

    # Remind me to (task) at (time)
    remind_at_match = re.match(r"remind me to (.+) at (.+)", user_input, re.IGNORECASE)
    if remind_at_match:
        import requests
        task = remind_at_match.group(1).strip()
        time_str = remind_at_match.group(2).strip()
        # Try to parse the time
        try:
            # Accept formats like '7:30pm', '19:30', '7pm', etc.
            now = datetime.datetime.now()
            time_formats = ["%I:%M%p", "%I%p", "%H:%M", "%H"]
            reminder_time = None
            for fmt in time_formats:
                try:
                    parsed = datetime.datetime.strptime(time_str.lower().replace(' ', ''), fmt)
                    # Set the date to today
                    reminder_time = now.replace(hour=parsed.hour, minute=parsed.minute if '%M' in fmt else 0, second=0, microsecond=0)
                    break
                except Exception:
                    continue
            if reminder_time is None:
                raise ValueError("Could not parse time.")
            # If the time is in the past, schedule for tomorrow
            if reminder_time < now:
                reminder_time += datetime.timedelta(days=1)
            seconds_until = (reminder_time - now).total_seconds()
        except Exception as e:
            chat_box.insert(tk.END, f"Zoey: Sorry, I couldn't understand the time '{time_str}'. Please use a format like '7:30pm' or '19:30'.\n")
            chat_box.see(tk.END)
            return
        def send_reminder():
            token = "asoyjemyxuuymxq1b3o32fehd7ez1h"  # Your Pushover app token
            user_key = "uzc58jcvu7hdf3r9dykjj55piobtub"  # Your Pushover user key
            response = requests.post("https://api.pushover.net/1/messages.json", data={
                "token": token,
                "user": user_key,
                "message": task
            })
            if response.status_code == 200:
                print(f"Reminder '{task}' sent to your phone.")
            else:
                print(f"Failed to send reminder: {response.text}")
        threading.Timer(seconds_until, send_reminder).start()
        reminders.append(f"{task} at {reminder_time.strftime('%I:%M %p')}")
        chat_box.insert(tk.END, f"Zoey: Reminder set for {reminder_time.strftime('%I:%M %p')}!\n")
        history.append(f"Zoey: Reminder set for {reminder_time.strftime('%I:%M %p')}!")
        chat_box.see(tk.END)
        update_reminders_view()
        return

    # Remind me to integration
    if user_input.lower().startswith("remind me to"):
        import requests
        def send_reminder(message):
            token = "asoyjemyxuuymxq1b3o32fehd7ez1h"  # Your Pushover app token
            user_key = "uzc58jcvu7hdf3r9dykjj55piobtub"  # Your Pushover user key
            response = requests.post("https://api.pushover.net/1/messages.json", data={
                "token": token,
                "user": user_key,
                "message": message
            })
            if response.status_code == 200:
                return "Reminder sent to your phone."
            else:
                return f"Failed to send reminder: {response.text}"
        message = user_input[len("remind me to"):].strip()
        result = send_reminder(message)
        reminders.append(message)
        chat_box.insert(tk.END, f"Zoey: {result}\n")
        history.append(f"Zoey: {result}")
        chat_box.see(tk.END)
        return

    memory_response = update_memory_from_input(user_input)
    if memory_response:
        chat_box.insert(tk.END, f"Zoey: {memory_response}\n")
        history.append(f"Zoey: {memory_response}")
        chat_box.see(tk.END)
        return

    # Show thinking message
    chat_box.insert(tk.END, "Zoey is thinking...\n")
    chat_box.see(tk.END)

    def llm_thread():
        prompt = build_prompt(user_input)
        full_reply = call_groq(prompt).strip()
        # Extract thinking step if present
        if "# Thinking step:" in prompt:
            if "Zoey:" in full_reply:
                parts = full_reply.split("Zoey:", 1)
                thinking = parts[0].strip()
                zoey_reply = parts[1].strip().split("\n")[0]
            else:
                thinking = "(No explicit thinking step in reply)"
                zoey_reply = full_reply.split("\n")[0]
        else:
            thinking = "(No explicit thinking step in prompt)"
            zoey_reply = full_reply.split("\n")[0]
        def update_ui():
            # Remove the last 'Zoey is thinking...' line
            chat_box.delete("end-2l", "end-1l")
            chat_box.insert(tk.END, f"Zoey: {zoey_reply}\n")
            history.append(f"Zoey: {zoey_reply}")
            chat_box.see(tk.END)
            if should_remember(user_input):
                third_person_fact = convert_to_third_person(user_input)
                confirm = messagebox.askyesno("Add to Memory?", f"Should I remember this?\n\n“{third_person_fact}”")
                if confirm:
                    memory_confirmation = remember(memory, third_person_fact)
                    chat_box.insert(tk.END, f"Zoey: {memory_confirmation}\n")
                    history.append(f"Zoey: {memory_confirmation}")
                    chat_box.see(tk.END)
        root.after(0, update_ui)
    threading.Thread(target=llm_thread, daemon=True).start()

user_entry.bind("<Return>", lambda event: send_message())
tk.Button(chat_frame, text="Send", command=send_message, bg="#007aff", fg="#fff", font=("Segoe UI", 11, "bold"), bd=0, activebackground="#0051a8").pack(side=tk.LEFT, padx=(5, 2), pady=(0, 10))

# Memory Frame
memory_frame = tk.Frame(root, bg="#181a1b")

# --- Move function definitions above their usage ---
def delete_memory_by_index(idx):
    global memory
    memory = load_memory()  # Always reload from file before deleting
    key = list(memory.keys())[idx]
    if messagebox.askyesno("Delete Memory", "Are you sure you want to forget this?"):
        forget(memory, memory[key])
        update_memory_view()

def add_memory_popup():
    global memory
    fact = simpledialog.askstring("Add Memory", "What should Zoey remember?")
    if fact:
        memory = load_memory()  # Always reload from file before adding
        confirmation = remember(memory, fact)
        update_memory_view()
        messagebox.showinfo("Memory Added", confirmation)

def update_memory_view():
    global memory
    memory = load_memory()  # Always reload from file
    for widget in memory_inner_frame.winfo_children():
        widget.destroy()
    facts = list(memory.values()) if hasattr(memory, 'values') else list(memory)
    if facts:
        for idx, fact in enumerate(facts):
            row = tk.Frame(memory_inner_frame, bg="#232526")
            label = tk.Label(row, text=f"• {fact}", anchor="w", justify="left", wraplength=460, bg="#232526", fg="#e0e0e0", font=("Segoe UI", 11))
            delete_btn = tk.Button(row, text="❌", command=lambda k=idx: delete_memory_by_index(k), width=2, bg="#232526", fg="#ff5f56", bd=0, font=("Segoe UI", 11, "bold"), activebackground="#181a1b")
            row.pack(fill="x", pady=2)
            label.pack(side="left", fill="x", expand=True)
            delete_btn.pack(side="right", padx=5)
    else:
        tk.Label(memory_inner_frame, text="Zoey doesn't remember anything yet.", bg="#232526", fg="#888", font=("Segoe UI", 11, "italic")).pack(pady=10)

# Header frame for Add Memory button (top right)
memory_header = tk.Frame(memory_frame, bg="#181a1b")
memory_header.pack(fill="x", pady=(10, 0), padx=10)
add_memory_btn = tk.Button(memory_header, text="+ Add Memory", command=add_memory_popup, bg="#007aff", fg="#fff", font=("Segoe UI", 11, "bold"), bd=0, activebackground="#0051a8")
add_memory_btn.pack(side="right")

memory_canvas = tk.Canvas(memory_frame, width=580, height=400, bg="#232526", highlightthickness=0)
memory_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
memory_scrollbar = tk.Scrollbar(memory_frame, orient="vertical", command=memory_canvas.yview, bg="#232526", troughcolor="#232526", activebackground="#444")
memory_scrollbar.pack(side="right", fill="y")
memory_canvas.configure(yscrollcommand=memory_scrollbar.set)
memory_canvas.bind("<Configure>", lambda e: memory_canvas.configure(scrollregion=memory_canvas.bbox("all")))
memory_inner_frame = tk.Frame(memory_canvas, bg="#232526")
memory_canvas.create_window((0, 0), window=memory_inner_frame, anchor="nw")

# --- Groq API ---
GROQ_API_KEY = "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"
def call_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    res = requests.post(url, headers=headers, json=data)
    try:
        response_json = res.json()
        if "choices" in response_json:
            return response_json["choices"][0]["message"]["content"]
        else:
            print("Groq API error:", response_json)
            return "Sorry, there was a problem with the Groq API: " + str(response_json)
    except Exception as e:
        print("Groq error response:", res.status_code, res.text)
        raise

# Start App
chat_frame.pack(fill="both", expand=True)
root.mainloop()
