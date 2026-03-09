"""
Test script - makes a real test call to verify Twilio is working.
"""
from dotenv import load_dotenv
load_dotenv()

import config
from phone_caller import PhoneCaller

print("🔧 Testing Twilio phone call...")
print(f"   From: {config.TWILIO_PHONE_NUMBER}")
print(f"   To:   {config.MY_PHONE_NUMBER}")
print()

caller = PhoneCaller()
sid = caller.make_alert_call(["תל אביב - בדיקה"])

if sid:
    print(f"\n✅ Call initiated! SID: {sid}")
    print("📞 You should receive a call now!")
else:
    print("\n❌ Call failed! Check the error above.")
