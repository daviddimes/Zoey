import requests

# Groq API Setup
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

# Zoey's tone
system_message = """Act as Zoey. You’re texting David. Sound like a real person — casual, clear, never robotic. Don’t repeat things or speak for David. Always respond like it’s your turn in a chat."""

conversation_history = []

# Wikipedia search
def search_wikipedia(query):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
    try:
        response = requests.get(url)
        data = response.json()
        return data.get("extract", "No summary found.")
    except Exception as e:
        return f"Error searching Wikipedia: {e}"

# Reminder using Pushover API directly (no external library)
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

# Main chat loop
while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ["exit", "quit"]:
        print("Zoey: Catch you later 👋")
        break

    if user_input.lower().startswith("search:"):
        query = user_input[len("search:"):].strip()
        result = search_wikipedia(query)
        print("\nZoey:", result, "\n")
        conversation_history.append(f"David: {user_input}")
        conversation_history.append(f"Zoey: {result}")
        continue

    if user_input.lower().startswith("remind me to"):
        message = user_input[len("remind me to"):].strip()
        result = send_reminder(message)
        print("\nZoey:", result, "\n")
        conversation_history.append(f"David: {user_input}")
        conversation_history.append(f"Zoey: {result}")
        continue

    conversation_history.append(f"David: {user_input}")
    recent_history = "\n".join(conversation_history[-6:])
    prompt = f"{system_message}\n\n{recent_history}\nZoey:"

    reply = call_groq(prompt).strip().split("\n")[0]

    print("\nZoey:", reply, "\n")
    conversation_history.append(f"Zoey: {reply}")
