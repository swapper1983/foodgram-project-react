# Generated by Django 4.2.5 on 2023-10-08 22:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0006_alter_amountingredient_amount'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='amountingredient',
            unique_together={('recipe', 'ingredient')},
        ),
    ]
