from django.contrib.auth.models import User  # ,AbstractUser
from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.slug


class Ingredient(models.Model):
    name = models.CharField(max_length=256)
    measurement_unit = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE,
                               related_name='recipe_ingredients')
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE,
                                   related_name='ingredient_recipes')
    amount = models.IntegerField()

    def __str__(self):
        return ("Recipe: " + self.recipe.__str__()
                + " Ingredient: " + self.ingredient.__str__())

    class Meta:
        unique_together = ('recipe', 'ingredient')


class Recipe(models.Model):
    author = models.ForeignKey(User, on_delete=models.DO_NOTHING,
                               related_name='user_recipes')
    name = models.CharField(max_length=256)
    tags = models.ManyToManyField(Tag, related_name='tagged_recipes',
                                  blank=True)
    ingredients = models.ManyToManyField(Ingredient, through=RecipeIngredient,
                                         related_name='recipes')
    text = models.TextField(default='', blank=True)
    image = models.ImageField(upload_to='recipe_images',
                              default='recipe_images/default.jpg')
    cooking_time = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Favorites(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='favorites')
    recipes = models.ManyToManyField(Recipe, related_name='favorite_by')

    def __str__(self):
        return self.user.username


class ShoppingCart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='shopping_cart')
    recipes = models.ManyToManyField(Recipe, related_name='in_shopping_carts')

    def __str__(self):
        return self.user.username


class SubscriptionManager(models.Manager):
    def is_subscribed(self, user, author):
        try:
            subscriptions = Subscriptions.objects.get(user=user)
            return subscriptions.subscription.filter(id=author.id).exists()
        except Subscriptions.DoesNotExist:
            return False

    def get_subscriptions(self, user):
        try:
            return Subscriptions.objects.get(user=user).subscription.all()
        except Subscriptions.DoesNotExist:
            return []


class Subscriptions(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='subscriptions')
    subscription = models.ManyToManyField(User, related_name='following')
    objects = SubscriptionManager()

    def __str__(self):
        return self.user.username
