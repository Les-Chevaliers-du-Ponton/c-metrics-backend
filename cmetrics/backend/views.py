import asyncio
import json
import uuid
from datetime import datetime as dt

import ccxt.async_support as async_cct
import django
from GoogleNews import GoogleNews
from asgiref.sync import sync_to_async
from ccxt.base import errors
from django import http
from django.contrib import auth
from django.core.handlers.asgi import ASGIRequest
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.response import Response

from cmetrics.backend import models
from cmetrics.backend import serializers
from cmetrics.data_source.coinmarketcap import CoinMarketCap
from cmetrics.utils.helpers import get_exchange_object

COINMARKETCAP = CoinMarketCap()


@csrf_exempt
def login_view(request: ASGIRequest):
    # thomas_bouamoud
    username = request.POST.get("username")
    password = request.POST.get("password")
    user = auth.aauthenticate(request, username=username, password=password)
    if user is not None:
        auth.login(request, user)
        return http.JsonResponse({"result": "ok"}, safe=False)
    else:
        return http.HttpResponseForbidden()


async def get_exchanges(request: ASGIRequest):
    data = async_cct.exchanges
    return django.http.JsonResponse(data, safe=False)


async def get_ohlc(request: ASGIRequest):
    print(request)
    if not user.is_authenticated:
        return http.HttpResponseForbidden()
    else:
        exchange = request.GET.get("exchange")
        timeframe = request.GET.get("timeframe")
        pairs = request.GET.get("pairs")
        if not exchange or not timeframe or not pairs:
            return http.JsonResponse({"error": "Missing parameters"}, status=400)
        pairs = pairs.split(",")
        tasks = list()
        for pair in pairs:
            tasks += exchange.fetch_ohlcv(symbol=pair, timeframe=timeframe, limit=300)
        try:
            ohlc_data = await asyncio.gather(*tasks)
        except errors.BadSymbol:
            ohlc_data = None
        await exchange.close()
        return django.http.JsonResponse(ohlc_data, safe=False)


async def get_order_book(request: ASGIRequest):
    exchange = request.GET.get("exchange")
    pairs = request.GET.get("pair")
    if not exchange or not pairs:
        return http.JsonResponse({"error": "Missing parameters"}, status=400)
    exchange = get_exchange_object(exchange)
    pairs = pairs.split(",")
    tasks = list()
    for pair in pairs:
        tasks += exchange.fetch_order_book(symbol=pair, limit=10000)
    try:
        order_book_data = await asyncio.gather(*tasks)
    except errors.BadSymbol:
        order_book_data = None
    await exchange.close()
    return django.http.JsonResponse(order_book_data, safe=False)


async def get_public_trades(request: ASGIRequest):
    exchange = request.GET.get("exchange")
    pairs = request.GET.get("pair")
    if not exchange or not pairs:
        return http.JsonResponse({"error": "Missing parameters"}, status=400)
    exchange = get_exchange_object(exchange)
    pairs = pairs.split(",")
    tasks = list()
    for pair in pairs:
        tasks += exchange.fetch_trades(symbol=pair, limit=1000)
    try:
        data = await asyncio.gather(*tasks)
    except errors.BadSymbol:
        data = None
    await exchange.close()
    return django.http.JsonResponse(data, safe=False)


async def get_exchange_markets(request: ASGIRequest):
    exchange = request.GET.get("exchange")
    exchange = get_exchange_object(exchange)
    markets = await exchange.load_markets()
    await exchange.close()
    return django.http.JsonResponse(markets, safe=False)


async def get_news(request: ASGIRequest):
    # TODO: find an alternative approach as Google News gets partially blocked on AWS
    pair = request.GET.get("search_term")
    googlenews = GoogleNews()
    googlenews.get_news(pair)
    data = googlenews.results()
    data = [
        article
        for article in data
        if isinstance(article["datetime"], dt) and article["datetime"] <= dt.now()
    ]
    return django.http.JsonResponse(data, safe=False)


@csrf_exempt
async def post_new_order(request: ASGIRequest):
    data = json.loads(request.body.decode("utf-8"))
    new_order = models.Orders(
        order_dim_key=str(uuid.uuid4()),
        user_id=data.get("user_id"),
        order_id=str(uuid.uuid4()),
        broker_id=data.get("broker_id"),
        trading_env=data.get("trading_env"),
        trading_type=data.get("trading_type"),
        asset_id=data.get("asset_id"),
        order_side=data.get("order_side"),
        order_type=data.get("order_type"),
        order_creation_tmstmp=dt.fromtimestamp(
            float(data.get("order_creation_tmstmp")) / 1000
        ),
        order_status=data.get("order_status"),
        fill_pct=data.get("fill_pct"),
        order_volume=data.get("order_volume"),
        order_price=data.get("order_price") if data.get("order_price") else 1,
        insert_tmstmp=dt.now(),
    )
    await sync_to_async(new_order.save)()
    return django.http.JsonResponse("success", safe=False)


@csrf_exempt
async def cancel_order(request: ASGIRequest):
    data = json.loads(request.body.decode("utf-8"))
    order_dim_key = data.get("order_dim_key")
    order = models.Orders.objects.filter(order_dim_key=order_dim_key)
    await sync_to_async(order.update)(expiration_tmstmp=dt.now())
    new_row = models.Orders(
        order_dim_key=str(uuid.uuid4()),
        user_id=order.values("user_id"),
        order_id=order.values("order_id"),
        broker_id=order.values("broker_id"),
        trading_env=order.values("trading_env"),
        trading_type=order.values("trading_type"),
        asset_id=order.values("asset_id"),
        order_side=order.values("order_side"),
        order_type=order.values("order_type"),
        order_creation_tmstmp=order.values("order_creation_tmstmp"),
        order_status="cancelled",
        fill_pct=order.values("fill_pct"),
        order_volume=order.values("order_volume"),
        order_price=order.values("order_price"),
        insert_tmstmp=dt.now(),
    )
    await sync_to_async(new_row.save)()
    return django.http.JsonResponse("success", safe=False)


class OrdersViewSet(viewsets.ModelViewSet):
    queryset = models.Orders.objects.filter(expiration_tmstmp__isnull=True)
    serializer_class = serializers.OrdersSerializer


class TradesViewSet(viewsets.ModelViewSet):
    queryset = models.Trades.objects.filter(expiration_tmstmp__isnull=True)
    serializer_class = serializers.TradesSerializer


class CoinMarketCapMappingViewSet(viewsets.ModelViewSet):
    queryset = models.CoinMarketCapMapping.objects.all()
    serializer_class = serializers.CoinMarketCapMappingSerializer


class CoinMarketCapMetaDataViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CoinMarketCapMetaDataSerializer

    def get_queryset(self):
        crypto_coinmarketcap_id = self.request.GET.get("crypto_coinmarketcap_id")
        queryset = models.CoinMarketCapMetaData.objects.filter(
            id=crypto_coinmarketcap_id
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
