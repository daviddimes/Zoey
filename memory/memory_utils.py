import json
import os
import re

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def remember(memory, fact):
    key = fact[:40]
    memory[key] = fact
    save_memory(memory)
    return f"Got it. I’ll remember: {fact}"

def forget(memory, text):
    text = text.lower()
    for key in list(memory.keys()):
        if text in memory[key].lower():
            del memory[key]
            save_memory(memory)
            return f"Forgot: {text}"
    return f"I couldn't find that in memory."

def list_memory(memory):
    if not memory:
        return "I don't remember anything yet."
    return "Here’s what I remember:\n- " + "\n- ".join(memory.values())

def should_remember(text):
    keywords = [
        "my name is", "i am", "i’m", "i have", "my dog", "my brother", "my wife", "i moved",
        "i live", "i work", "i don’t like", "i love", "i hate", "my birthday", "my favorite",
        "i usually", "i always", "i never", "my kids", "my daughter", "my son", "my wife",
        "i want", "i think", "i feel", "i need"
    ]
    lowered = text.lower()
    return any(phrase in lowered for phrase in keywords)

def convert_to_third_person(text):
    conversions = [
        (r"\bI'm\b", "David is"),
        (r"\bI am\b", "David is"),
        (r"\bI've\b", "David has"),
        (r"\bI'll\b", "David will"),
        (r"\bI\b", "David"),
        (r"\bme\b", "David"),
        (r"\bmy\b", "David's")
    ]
    for pattern, replacement in conversions:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text[0].upper() + text[1:]
