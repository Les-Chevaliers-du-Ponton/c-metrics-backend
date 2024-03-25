from rest_framework import serializers

from .models import Orders, Trades, CoinMarketCapMetaData, CoinMarketCapMapping


class BaseSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        fields = "__all__"


class OrdersSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = Orders


class TradesSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = Trades


class CoinMarketCapMetaDataSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = CoinMarketCapMetaData


class CoinMarketCapMappingSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = CoinMarketCapMapping
