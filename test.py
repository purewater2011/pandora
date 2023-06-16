# -*- coding: utf-8 -*-
import json
import uuid

from src.pandora.openai.api import ChatGPT, API, ChatCompletionByGPT

ac_token = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik1UaEVOVUpHTkVNMVFURTRNMEZCTWpkQ05UZzVNRFUxUlRVd1FVSkRNRU13UmtGRVFrRXpSZyJ9.eyJodHRwczovL2FwaS5vcGVuYWkuY29tL3Byb2ZpbGUiOnsiZW1haWwiOiJlcmljMjc1MDQzMzk4QGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9hdXRoIjp7InVzZXJfaWQiOiJ1c2VyLUo2VlJUeWVVSWhGaUFMZVVUZEpBdGRMbCJ9LCJpc3MiOiJodHRwczovL2F1dGgwLm9wZW5haS5jb20vIiwic3ViIjoiYXV0aDB8NjNmODc3ZDViMGRmYTg3YzhlYzk1MWQxIiwiYXVkIjpbImh0dHBzOi8vYXBpLm9wZW5haS5jb20vdjEiLCJodHRwczovL29wZW5haS5vcGVuYWkuYXV0aDBhcHAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTY4NjEwNjc5MCwiZXhwIjoxNjg3MzE2MzkwLCJhenAiOiJUZEpJY2JlMTZXb1RIdE45NW55eXdoNUU0eU9vNkl0RyIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgbW9kZWwucmVhZCBtb2RlbC5yZXF1ZXN0IG9yZ2FuaXphdGlvbi5yZWFkIG9yZ2FuaXphdGlvbi53cml0ZSJ9.1H-stPSEvP5xhIUS-GXuK43KmbNJnP6r_PhcQn8w0LNUc0zQZkCy9PZRd66gKB_Q50bX2879GmvhdZcEWcOA2o6yfrs9GAmFPyxKxocq2pT8VfCttSR1sSBNyJXUfwgIbDP3ALURcatvCaQ8JedrNkMdBMCeExgXcWE2C2esiyhcYNSFmotZBUbT3AXIlpwyGW-fWMbF4e3F3GseAvhcKnhUjpaulJGMKXHYrBFgoUBcTW0w4oK5AU7LqBvhEj2g1Alj9yygkdNZdgAR0Jht20Yg4S4_6Tp3aF47tugmY7NCSRePXxuYzdkq-RdcIVGo-RO9qPI2Bh8_e_1i466ytw'
access_tokens = {'default': ac_token}
chatgpt = ChatCompletionByGPT()

messages = [{'role': 'user', 'content': 'hello world'}]
# status, header, generator = api.request(ac_token, 'gpt-3.5-turbo', messages, False)
payload = {"prompt":"test2","message_id":"1c71462a-c2c6-4665-a78d-e1d8eaed6950","parent_message_id":"71161e56-d3af-4173-bf55-a2eb3d712638","model":"text-davinci-002-render-sha","timezone_offset_min":-480,"conversation_id": "8c35cbe6-901d-443e-9e60-a839e609f6a7"}
prompt = payload['prompt']
model = payload['model']
message_id = str(uuid.uuid4()) #payload['message_id']
parent_message_id = None #str(uuid.uuid4()) #payload['parent_message_id']
conversation_id = None #payload.get('conversation_id')
stream = payload.get('stream', False)
print(stream)


# [status, headers, generator] = chatgpt.talk(prompt, model, message_id, parent_message_id, conversation_id, stream)
# for line in generator:
#     json_data = line
#     print(json_data['message']['content']['parts'][0])
messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who won the world series in 2020?"},
        ]
rs = chatgpt.create(messages, model, parent_message_id, conversation_id)
print(rs)