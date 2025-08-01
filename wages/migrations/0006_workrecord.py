# Generated by Django 5.2.4 on 2025-07-21 07:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wages', '0005_dailywork_rate_alter_dailywork_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('rate', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date', models.DateField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wages.product')),
                ('tailor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wages.tailor')),
            ],
        ),
    ]
