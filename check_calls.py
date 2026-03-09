from twilio.rest import Client
import config

client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

# Check last few calls
calls = client.calls.list(limit=5)
for call in calls:
    print(f"SID: {call.sid}")
    print(f"  To: {call.to}, From: {call.from_formatted}")
    print(f"  Status: {call.status}, Duration: {call.duration}s")
    print(f"  Direction: {call.direction}")
    print(f"  Start: {call.start_time}, End: {call.end_time}")
    print()
