import json
import uuid
from datetime import datetime as dt

import ccxt
import django
from GoogleNews import GoogleNews
from asgiref.sync import sync_to_async
from ccxt.base import errors
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.response import Response

from cmetrics.backend import models
from cmetrics.backend import serializers
from cmetrics.data_source.coinmarketcap import CoinMarketCap
from cmetrics.utils.helpers import get_exchange_object

coinmarketcap = CoinMarketCap()


@csrf_exempt
def login_view(request: django.core.handlers.wsgi.WSGIRequest):
    # thomas_bouamoud
    username = request.POST.get("username")
    password = request.POST.get("password")
    user = django.contrib.auth.authenticate(
        request, username=username, password=password
    )
    if user is not None:
        django.contrib.auth.login(request, user)
        return django.http.JsonResponse({"result": "ok"}, safe=False)
    else:
        return django.http.HttpResponseForbidden()


async def get_exchanges(request: django.core.handlers.wsgi.WSGIRequest):
    data = ccxt.exchanges
    return django.http.JsonResponse(data, safe=False)


async def get_ohlc(request: django.core.handlers.wsgi.WSGIRequest):
    exchange = request.GET.get("exchange")
    timeframe = request.GET.get("timeframe")
    pair = request.GET.get("pair")
    exchange = get_exchange_object(exchange)
    try:
        ohlc_data = await exchange.fetch_ohlcv(
            symbol=pair, timeframe=timeframe, limit=300
        )
    except errors.BadSymbol:
        ohlc_data = None
    await exchange.close()
    return django.http.JsonResponse(ohlc_data, safe=False)


async def get_order_book(request: django.core.handlers.wsgi.WSGIRequest):
    exchange = request.GET.get("exchange")
    pair = request.GET.get("pair")
    exchange = get_exchange_object(exchange)
    try:
        order_book_data = await exchange.fetch_order_book(symbol=pair, limit=10000)
    except:
        order_book_data = None
    await exchange.close()
    return django.http.JsonResponse(order_book_data, safe=False)


async def get_public_trades(request: django.core.handlers.wsgi.WSGIRequest):
    exchange = request.GET.get("exchange")
    pair = request.GET.get("pair")
    exchange = get_exchange_object(exchange)
    try:
        data = await exchange.fetch_trades(symbol=pair, limit=1000)
    except errors.BadSymbol:
        data = None
    await exchange.close()
    return django.http.JsonResponse(data, safe=False)


async def get_exchange_markets(request: django.core.handlers.wsgi.WSGIRequest):
    exchange = request.GET.get("exchange")
    exchange = get_exchange_object(exchange)
    markets = await exchange.load_markets()
    await exchange.close()
    return django.http.JsonResponse(markets, safe=False)


async def get_news(request: django.core.handlers.wsgi.WSGIRequest):
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
async def post_new_order(request: django.core.handlers.wsgi.WSGIRequest):
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
async def cancel_order(request: django.core.handlers.wsgi.WSGIRequest):
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
        queryset = models.CoinMarketCapMetaData.objects.filter(id=crypto_coinmarketcap_id)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
