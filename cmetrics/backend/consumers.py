import asyncio
import json
import logging
import os

import redis.asyncio as async_redis
from channels import exceptions
from channels.auth import get_user
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from dotenv import load_dotenv

from cmetrics.utils.helpers import get_available_redis_streams

load_dotenv()


LOG = logging.getLogger(__name__)

REDIS = async_redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    port=int(os.environ.get("REDIS_PORT")),
    decode_responses=True,
)


class PublicLiveDataStream(AsyncWebsocketConsumer):
    """
    Exposes data on:
    - LOCAL: ws://127.0.0.1:8000/ws/live_data/?channels=METHOD-EXCHANGE-BASE-QUOTE
    - PROD:  ws://18.205.192.229:8000/ws/live_data/?channels=EXCHANGE-BASE-QUOTE

    Methods:
    - book
    - trades
    """

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self._serve_client_data_task = None
        self.client_streams = None
        self.client_params = None
        self.errors = None

    async def connect(self):
        self.errors = list()
        user = await get_user(self.scope)
        if user.is_authenticated:
            self.client_params = await self.get_client_params()
            self.client_streams = await self.get_valid_channels()
            if self.client_streams:
                await self.accept()
                if self.errors:
                    await self.send(text_data=json.dumps({"errors": self.errors}))
                self._serve_client_data_task = asyncio.create_task(
                    self.serve_client_data()
                )
            else:
                await self.disconnect(404)
        else:
            await self.disconnect(403)

    async def get_client_params(self) -> dict:
        params = dict()
        raw_params = self.scope["query_string"].decode("utf-8")
        for raw_param in raw_params.split("&"):
            try:
                k, v = raw_param.split("=")
                params[k] = v
            except ValueError:
                pass
        return params

    async def serve_client_data(self):
        try:
            while True:
                streams = {stream: "$" for stream in self.client_streams}
                data = await REDIS.xread(streams=streams, block=0)
                data = data[0][1]
                _, latest_record = data[len(data) - 1]
                await self.send(text_data=json.dumps(latest_record))
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass

    async def get_valid_channels(self) -> list:
        validated_channels = list()
        failed_channels = list()
        streams = await get_available_redis_streams(REDIS)
        if not streams:
            LOG.error("The real time service is down")
        else:
            channels = self.client_params.get("channels", "").split(",")
            for channel in channels:
                channel = "{real-time}-" + f"{channel}"
                if channel in streams:
                    validated_channels.append(channel)
                else:
                    failed_channels.append(channel)
            if failed_channels:
                log = f'Following channels are invalid: {", ".join(failed_channels)}'
                LOG.error(log)
                self.errors.append(log)
        return validated_channels

    async def disconnect(self, close_code):
        if hasattr(self, "_serve_client_data_task"):
            self._serve_client_data_task.cancel()
        await self.close()
        raise exceptions.StopConsumer()

    async def receive(self, text_data=None, **kwargs):
        pass


class PrivateStream(AsyncWebsocketConsumer):
    """
    Exposes data on:
    - PROD:  ws://18.205.192.229:8000/ws/screening/
    """

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self._serve_client_data_task = None

    async def connect(self):
        user = await get_user(self.scope)
        if user.is_authenticated:
            await database_sync_to_async(self.scope["session"].save)()
            await self.accept()
            self._serve_client_data_task = asyncio.create_task(self.serve_client_data())
        else:
            await self.disconnect(403)

    async def serve_client_data(self):
        try:
            while True:
                streams = {"{screening}": "$"}
                data = await REDIS.xread(streams=streams, block=0)
                data = data[0][1]
                _, latest_record = data[len(data) - 1]
                await self.send(text_data=json.dumps(latest_record))
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass

    async def disconnect(self, close_code):
        if hasattr(self, "_serve_client_data_task"):
            self._serve_client_data_task.cancel()
        await self.close()
        raise exceptions.StopConsumer()

    async def receive(self, text_data=None, **kwargs):
        pass
