from twilio.rest import Client

account_sid = 'ACb9a3d7a879954647f052a343dcb499c4'
auth_token = '3889853a3e6ad8684ee6e621937da0a0'
client = Client(account_sid, auth_token)

def send_text(message):
    client.messages.create(
        body=message,
        from_='8666108170',
        to='6825518763'
    )
if __name__ == "__main__":
    send_text("Hello World.")
