# -*- coding: utf-8 -*-

import logging
import asyncio
import json
import queue as block_queue
import threading
from os import getenv

import httpx
import requests
from certifi import where

from .. import __version__
from ..exts.config import default_api_prefix,USER_CONFIG_DIR
import uuid
from openai import util
import os

class API:
    def __init__(self, proxy, ca_bundle):
        self.proxy = proxy
        self.ca_bundle = ca_bundle
        self.logger = logging.getLogger('waitress')

    @staticmethod
    def wrap_stream_out(generator, status):
        if status != 200:
            for line in generator:
                yield json.dumps(line)

            return

        for line in generator:
            yield b'data: ' + json.dumps(line).encode('utf-8') + b'\n\n'

        yield b'data: [DONE]\n\n'

    async def __process_sse(self, resp):
        yield resp.status_code
        yield resp.headers

        if resp.status_code != 200:
            yield await self.__process_sse_except(resp)
            return

        async for utf8_line in resp.aiter_lines():
            if 'data: [DONE]' == utf8_line[0:12]:
                break

            if 'data: {"message":' == utf8_line[0:17] or 'data: {"id":' == utf8_line[0:12]:
                yield json.loads(utf8_line[6:])

    @staticmethod
    async def __process_sse_except(resp):
        result = b''
        async for line in resp.aiter_bytes():
            result += line

        return json.loads(result.decode('utf-8'))

    @staticmethod
    def __generate_wrap(queue, thread, event):
        while True:
            try:
                item = queue.get()
                if item is None:
                    break

                yield item
            except BaseException as e:
                event.set()
                thread.join()

                if isinstance(e, GeneratorExit):
                    raise e

    async def _do_request_sse(self, url, headers, data, queue, event):
        async with httpx.AsyncClient(verify=self.ca_bundle, proxies=self.proxy) as client:
            async with client.stream('POST', url, json=data, headers=headers, timeout=600) as resp:
                async for line in self.__process_sse(resp):
                    queue.put(line)

                    if event.is_set():
                        await client.aclose()
                        break

                queue.put(None)

    def _request_sse(self, url, headers, data):
        queue, e = block_queue.Queue(), threading.Event()
        t = threading.Thread(target=asyncio.run, args=(self._do_request_sse(url, headers, data, queue, e),))
        t.start()

        return queue.get(), queue.get(), self.__generate_wrap(queue, t, e)


class ChatGPT(API):
    def __init__(self, access_tokens: dict, proxy=None):
        self.access_tokens = access_tokens
        self.access_token_key_list = list(access_tokens)
        self.default_token_key = self.access_token_key_list[0]
        self.session = requests.Session()
        self.req_kwargs = {
            'proxies': {
                'http': proxy,
                'https': proxy,
            } if proxy else None,
            'verify': where(),
            'timeout': 100,
            'allow_redirects': False,
        }

        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Pandora/{} Safari/537.36'.format(__version__)

        super().__init__(proxy, self.req_kwargs['verify'])

    def __get_headers(self, token_key=None):
        return {
            'Authorization': 'Bearer ' + self.get_access_token(token_key),
            'User-Agent': self.user_agent,
            'Content-Type': 'application/json',
        }

    @staticmethod
    def __get_api_prefix():
        return getenv('CHATGPT_API_PREFIX', default_api_prefix())

    def get_access_token(self, token_key=None):
        return self.access_tokens[token_key or self.default_token_key]

    def list_token_keys(self):
        return self.access_token_key_list

    def list_models(self, raw=False, token=None):
        url = '{}/chatgpt/backend-api/models'.format(self.__get_api_prefix())
        # url = 'https://ai.fakeopen.com/api/models'
        resp = self.session.get(url=url, headers=self.__get_headers(token), **self.req_kwargs)

        if raw:
            return resp

        if resp.status_code != 200:
            raise Exception('list models failed: ' + self.__get_error(resp))

        result = resp.json()
        if 'models' not in result:
            raise Exception('list models failed: ' + resp.text)

        return result['models']

    def list_conversations(self, offset, limit, raw=False, token=None):
        url = '{}/chatgpt/backend-api/conversations?offset={}&limit={}'.format(self.__get_api_prefix(), offset, limit)
        resp = self.session.get(url=url, headers=self.__get_headers(token), **self.req_kwargs)

        if raw:
            return resp

        if resp.status_code != 200:
            raise Exception('list conversations failed: ' + self.__get_error(resp))

        return resp.json()

    def get_conversation(self, conversation_id, raw=False, token=None):
        url = '{}/chatgpt/backend-api/conversation/{}'.format(self.__get_api_prefix(), conversation_id)
        resp = self.session.get(url=url, headers=self.__get_headers(token), **self.req_kwargs)

        if raw:
            return resp

        if resp.status_code != 200:
            raise Exception('get conversation failed: ' + self.__get_error(resp))

        return resp.json()

    def clear_conversations(self, raw=False, token=None):
        data = {
            'is_visible': False,
        }

        url = '{}/chatgpt/backend-api/conversations'.format(self.__get_api_prefix())
        resp = self.session.patch(url=url, headers=self.__get_headers(token), json=data, **self.req_kwargs)

        if raw:
            return resp

        if resp.status_code != 200:
            raise Exception('clear conversations failed: ' + self.__get_error(resp))

        result = resp.json()
        if 'success' not in result:
            raise Exception('clear conversations failed: ' + resp.text)

        return result['success']

    def del_conversation(self, conversation_id, raw=False, token=None):
        data = {
            'is_visible': False,
        }

        return self.__update_conversation(conversation_id, data, raw, token)

    def gen_conversation_title(self, conversation_id, model, message_id, raw=False, token=None):
        url = '{}/chatgpt/backend-api/conversation/gen_title/{}'.format(self.__get_api_prefix(), conversation_id)
        data = {
            'model': model,
            'message_id': message_id,
        }
        resp = self.session.post(url=url, headers=self.__get_headers(token), json=data, **self.req_kwargs)

        if raw:
            return resp

        if resp.status_code != 200:
            raise Exception('gen title failed: ' + self.__get_error(resp))

        result = resp.json()
        if 'title' not in result:
            raise Exception('gen title failed: ' + resp.text)

        return result['title']

    def set_conversation_title(self, conversation_id, title, raw=False, token=None):
        data = {
            'title': title,
        }

        return self.__update_conversation(conversation_id, data, raw, token)

    def talk(self, prompt, model, message_id, parent_message_id, conversation_id=None, stream=True, token=None, gizmo_id=None):
        data = {
            'action': 'next',
            'conversation_mode': {'kind': 'primary_assistant'},
            'messages': [
                {
                    'id': message_id,
                    'role': 'user',
                    'author': {
                        'role': 'user',
                    },
                    'content': {
                        'content_type': 'text',
                        'parts': [prompt],
                    },
                }
            ],
            'model': model,
            'parent_message_id': parent_message_id,
        }

        if conversation_id:
            data['conversation_id'] = conversation_id

        if gizmo_id:
            data['conversation_mode'] = {'kind': 'gizmo_interaction', 'gizmo_id': gizmo_id}

        return self.__request_conversation(data, token)
    def talkv2(self, messages, model, parent_message_id, conversation_id=None, stream=True, token=None, auto_conversation=False):
        new_messages = []
        for msg in messages:
            message_id = str(uuid.uuid4())
            if msg['role'] == 'system':
                msg['role'] = 'user'
            new_messages.append({
                    'id': message_id,
                    'role': msg['role'],
                    'author': {
                        'role': msg['role'],
                    },
                    'content': {
                        'content_type': 'text',
                        'parts': [msg['content']],
                    },
                })
        if auto_conversation:
            action = 'variant'
        else:
            action = 'next'
        data = {
            'action': action,
            'messages': new_messages,
            'model': model,
            'parent_message_id': parent_message_id,
        }

        if conversation_id:
            data['conversation_id'] = conversation_id

        return self.__request_conversation(data, token)

    def goon(self, model, parent_message_id, conversation_id, stream=True, token=None, gizmo_id=None):
        data = {
            'action': 'continue',
            'conversation_mode': {'kind': 'primary_assistant'},
            'conversation_id': conversation_id,
            'model': model,
            'parent_message_id': parent_message_id,
        }
        if gizmo_id:
            data['conversation_mode'] = {'kind': 'gizmo_interaction', 'gizmo_id': gizmo_id}

        return self.__request_conversation(data, token)

    def regenerate_reply(self, prompt, model, conversation_id, message_id, parent_message_id, stream=True, token=None):
        data = {
            'action': 'variant',
            'conversation_mode': {'kind': 'primary_assistant'},
            'messages': [
                {
                    'id': message_id,
                    'role': 'user',
                    'author': {
                        'role': 'user',
                    },
                    'content': {
                        'content_type': 'text',
                        'parts': [prompt],
                    },
                }
            ],
            'model': model,
            'conversation_id': conversation_id,
            'parent_message_id': parent_message_id,
        }

        return self.__request_conversation(data, token)

    def __request_conversation(self, data, token=None):
        url = '{}/chatgpt/backend-api/conversation'.format(self.__get_api_prefix())
        headers = {**self.session.headers, **self.__get_headers(token), 'Accept': 'text/event-stream'}

        return self._request_sse(url, headers, data)

    def __update_conversation(self, conversation_id, data, raw=False, token=None):
        url = '{}/chatgpt/backend-api/conversation/{}'.format(self.__get_api_prefix(), conversation_id)
        resp = self.session.patch(url=url, headers=self.__get_headers(token), json=data, **self.req_kwargs)

        if raw:
            return resp

        if resp.status_code != 200:
            raise Exception('update conversation failed: ' + self.__get_error(resp))

        result = resp.json()
        if 'success' not in result:
            raise Exception('update conversation failed: ' + resp.text)

        return result['success']

    @staticmethod
    def __get_error(resp):
        try:
            return str(resp.json()['detail'])
        except:
            return resp.text


class ChatCompletion(API):
    def __init__(self, proxy=None):
        self.session = requests.Session()
        self.req_kwargs = {
            'proxies': {
                'http': proxy,
                'https': proxy,
            } if proxy else None,
            'verify': where(),
            'timeout': 600,
            'allow_redirects': False,
        }

        self.user_agent = 'pandora/{}'.format(__version__)

        super().__init__(proxy, self.req_kwargs['verify'])

    def __get_headers(self, api_key):
        return {
            'Authorization': 'Bearer ' + api_key,
            'User-Agent': self.user_agent,
            'Content-Type': 'application/json',
        }

    def request(self, api_key, model, messages, stream=True, **kwargs):
        data = {
            'model': model,
            'messages': messages,
            **kwargs,
            'stream': stream,
        }

        return self.__request_conversation(api_key, data, stream)

    def __request_conversation(self, api_key, data, stream):
        default = default_api_prefix()

        if api_key.startswith('fk-') or api_key.startswith('pk-'):
            prefix = default
        else:
            prefix = getenv('OPENAI_API_PREFIX', default)
        url = '{}/v1/chat/completions'.format(prefix)

        if stream:
            headers = {**self.__get_headers(api_key), 'Accept': 'text/event-stream'}
            return self._request_sse(url, headers, data)

        resp = self.session.post(url=url, headers=self.__get_headers(api_key), json=data, **self.req_kwargs)

        def __generate_wrap():
            yield resp.json()

        return resp.status_code, resp.headers, __generate_wrap()


# 基于actoken的Completion
class ChatCompletionByGPT(ChatCompletion):
    @staticmethod
    def read_access_token(token_file):
        with open(token_file, 'r') as f:
            return f.read().strip()

    def save_to_file(data, file):
        if not isinstance(data, str):
            data = json.dumps(data)
        with open(file, 'w') as f:
            f.write(data)

    @classmethod
    def create(cls,
               messages=None,
               model=None,
               deployment_id=None,
               conversation_id=None,
               max_tokens=None,
               temperature=None,
               stream=False,
               api_key=None,
               auto_conversation=False,
               **params
               ):

        token_file = os.path.join(USER_CONFIG_DIR, 'access_token.dat')
        cache_file = os.path.join(USER_CONFIG_DIR, 'cache.dat')
        ac_token = cls.read_access_token(token_file)

        # 初始化
        if os.path.isfile(cache_file):
            t = cls.read_access_token(cache_file)
            cache_data = json.loads(t) if t else ''
            if 'conversation_id' in cache_data:
                conversation_id = cache_data['conversation_id']
            if not deployment_id and 'message_id' in cache_data:
                deployment_id = cache_data['message_id']
        if not deployment_id:
            deployment_id = str(uuid.uuid4())

        chatgpt = ChatGPT({'default': ac_token})
        
        conversation_id = None # todo test
        [status, headers, generator] = chatgpt.talkv2(messages, 'text-davinci-002-render-sha', deployment_id, conversation_id, stream, auto_conversation=auto_conversation)

        choices = []
        c = 0
        cache = ''

        for line in generator:
            if 'message' not in line:
                result = {
                    'error': generator['msg'] if 'msg' in generator else 'happened error',
                    'detail': json.dumps(line)
                }
                cls.save_to_file('{}', cache_file)
                return result
            deployment_id = line['message']['id']
            cache = {'conversation_id': line['conversation_id'], 'message_id': deployment_id}
            create_time = int(line['message']['create_time'])
            choices.insert(0, {
                'text': line['message']['content']['parts'][0],
                'message': {'content': line['message']['content']['parts'][0], 'role': 'assistant'},
                'index': c,
                'finish_reason':  line['message']['metadata']['finish_details']['type'] if 'finish_details' in line['message']['metadata'] else None
            })
            c = c + 1

        cls.save_to_file(cache, cache_file)

        result = {
                  "id": deployment_id,
                  "object": "chat.completion",
                  "created": create_time,
                  "model": "text-davinci-002-render-sha",
                  "choices": choices,
                  "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2
                  }
                }
        result = util.convert_to_openai_object(result)
        return result

    @staticmethod
    def get_user_config_dir():
        return USER_CONFIG_DIR
