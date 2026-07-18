import json
import debugai_sdk

with open('.roota.json', 'r') as f:
    config = json.load(f)

debugai_sdk.install(repo="AbdullahKhan-77/demo-service", api_key=config['api_key'])
print("Starting app...")
user_sessions = {}
user_id = 9981
print(f"Looking up session for user {user_id}...")
session = user_sessions[user_id]
print(f"Session: {session}")