# Generated by Django 4.2.5 on 2023-10-09 22:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0004_alter_ingredient_measurement_unit_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='ingredient',
            unique_together=set(),
        ),
    ]
