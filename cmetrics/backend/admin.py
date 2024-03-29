from django.contrib import admin

import models

admin.site.register(models.Orders)
admin.site.register(models.Trades)
admin.site.register(models.CoinMarketCapMapping)
admin.site.register(models.CoinMarketCapMetaData)
