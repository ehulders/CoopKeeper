# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client

# Get environment variables
USER = os.getenv('API_USER')
PASSWORD = os.environ.get('API_PASSWORD')

account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')
client = Client(account_sid, auth_token)

recipient = os.getenv('COOP_SMS_OUT')
coop_number = os.getenv('COOP_SMS_IN')

message = client.messages \
                .create(
                     body="This is a CoopControl test",
                     from_=coop_number,
                     to=recipient
                 )

print(message.sid)