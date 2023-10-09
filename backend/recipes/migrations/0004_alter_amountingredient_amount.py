# Generated by Django 4.2.5 on 2023-10-08 22:07

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0003_alter_amountingredient_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='amountingredient',
            name='amount',
            field=models.PositiveSmallIntegerField(default=1, help_text='Введите количество ингредиента в единицах измерения', validators=[django.core.validators.MinValueValidator(1, message='Должно быть больше нуля')], verbose_name='Количество'),
        ),
    ]
