import asyncio
import json
import logging

from dotenv import load_dotenv
import redis.asyncio as async_redis

from channels import exceptions
from channels.generic.websocket import AsyncWebsocketConsumer

import os

from cmetrics.utils.helpers import get_available_redis_streams

load_dotenv()


LOG = logging.getLogger(__name__)

REDIS = async_redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
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

    async def connect(self):
        self.errors = list()
        self.client_parmas = await self.get_client_params()
        self.client_streams = await self.get_valid_channels()
        if self.client_streams:
            await self.accept()
            if self.errors:
                await self.send(text_data=json.dumps({"errors": self.errors}))
            await self.serve_client_data()
        else:
            await self.close()
            raise exceptions.StopConsumer()

    async def get_client_params(self) -> dict:
        parmas = dict()
        raw_params = self.scope["query_string"].decode("utf-8")
        for raw_param in raw_params.split("&"):
            try:
                k, v = raw_param.split("=")
                parmas[k] = v
            except ValueError:
                pass
        return parmas

    async def serve_client_data(self):
        while True:
            streams = {stream: "$" for stream in self.client_streams}
            data = await REDIS.xread(streams=streams, block=0)
            data = data[0][1]
            _, latest_record = data[len(data) - 1]
            await self.send(text_data=json.dumps(latest_record))
            await asyncio.sleep(0)

    async def get_valid_channels(self) -> list:
        validated_channels = list()
        failed_channels = list()
        streams = await get_available_redis_streams(REDIS)
        if not streams:
            LOG.error("The real time service is down")
        else:
            channels = self.client_parmas.get("channels", "").split(",")
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
        raise exceptions.StopConsumer()

    async def receive(self, text_data=None):
        pass


class PrivateOrderStream(AsyncWebsocketConsumer):
    """
    Exposes data on: ws://127.0.0.1:8000/ws/orders/
    """

    async def connect(self):
        await self.accept()  # TODO: implement authorization
        await self.serve_client_data()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None):
        pass
