import django
from ccxt import async_support as async_ccxt
from dotenv import load_dotenv
import os
import redis.asyncio as async_redis


load_dotenv()


def get_api_keys(exchange: str, websocket: bool = False) -> dict:
    try:
        key = os.environ[f"{exchange}_api_key"]
        secret = os.environ[f"{exchange}_api_secret"]
    except django.core.exceptions.ImproperlyConfigured:
        key = secret = None
    if key and secret:
        if websocket:
            return dict(key_id=key, key_secret=secret)
        else:
            return dict(apiKey=key, secret=secret)


def get_exchange_object(exchange: str) -> async_ccxt.Exchange:
    module = async_ccxt
    exchange_class = getattr(module, exchange)
    keys = get_api_keys(exchange)
    return exchange_class(keys) if keys else exchange_class()


async def get_available_redis_streams(
    redis_server: async_redis.StrictRedis, streams: str = None
) -> list:
    i = 0
    all_streams = list()
    while True:
        i, streams = await redis_server.scan(i, _type="STREAM")
        all_streams += streams
        if i == 0:
            return all_streams
