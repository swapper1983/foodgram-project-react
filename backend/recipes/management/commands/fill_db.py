from django.core.management.base import BaseCommand
from recipes.models import Ingredient, Tag
from rest_framework.utils import json

from foodgram.settings import BASE_DIR


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        self.load_ingredients()
        self.create_tags()

    def load_ingredients(self):
        if not Ingredient.objects.all().exists():
            path = BASE_DIR.joinpath('data', 'ingredients.json')

            with open(path, 'r', encoding='utf8') as file:
                data = json.load(file)
                ingredients = []
                for ingredient in data:
                    ingredients.append(Ingredient(
                        name=ingredient['name'],
                        measurement_unit=ingredient['measurement_unit']
                    ))

                Ingredient.objects.bulk_create(ingredients)

    def create_tags(self):
        if not Tag.objects.all().exists():
            tag_breakfast = Tag(name='Завтрак',
                                color='#FF6B00',
                                slug='breakfast')
            tag_lunch = Tag(name='Обед', color='#FF9642', slug='lunch')
            tag_dinner = Tag(name='Ужин', color='#6D3353', slug='dinner')
            tag_list = [tag_breakfast, tag_lunch, tag_dinner]
            Tag.objects.bulk_create(tag_list)
