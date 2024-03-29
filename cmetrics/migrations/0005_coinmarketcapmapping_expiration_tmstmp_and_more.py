# Generated by Django 5.0.3 on 2024-03-24 14:51

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cmetrics", "0004_alter_coinmarketcapmapping_platform_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="coinmarketcapmapping",
            name="expiration_tmstmp",
            field=models.DateTimeField(
                null=True, verbose_name="Record Expiration Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="coinmarketcapmapping",
            name="insert_tmstmp",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name="Record Insert Timestamp",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="coinmarketcapmetadata",
            name="expiration_tmstmp",
            field=models.DateTimeField(
                null=True, verbose_name="Record Expiration Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="coinmarketcapmetadata",
            name="insert_tmstmp",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name="Record Insert Timestamp",
            ),
            preserve_default=False,
        ),
    ]
