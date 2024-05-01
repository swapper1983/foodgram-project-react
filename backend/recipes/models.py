from django.contrib.auth.models import User  # AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Имя')
    color = models.CharField(max_length=7, unique=True, verbose_name='Цвет')
    slug = models.SlugField(unique=True, verbose_name='Слаг')

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.slug


class Ingredient(models.Model):
    name = models.CharField(max_length=256, verbose_name='Имя')
    measurement_unit = models.CharField(max_length=256,
                                        verbose_name='Единица измерения')

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE,
                               related_name='recipe_ingredients',
                               verbose_name='Рецепт')
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE,
                                   related_name='ingredient_recipes',
                                   verbose_name='Ингредиент')
    amount = models.IntegerField(verbose_name='Количество',
                                 validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'
        constraints = [
            UniqueConstraint(fields=['recipe', 'ingredient'],
                             name='unique_recipe_ingredient')
        ]

    def __str__(self):
        return f"Recipe: {self.recipe} Ingredient: {self.ingredient}"


class Recipe(models.Model):
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               related_name='user_recipes',
                               verbose_name='Автор')
    name = models.CharField(max_length=256, verbose_name='Название')
    tags = models.ManyToManyField(Tag,
                                  related_name='tagged_recipes',
                                  blank=True,
                                  verbose_name='Тэги')
    ingredients = models.ManyToManyField(Ingredient,
                                         through=RecipeIngredient,
                                         related_name='recipes',
                                         verbose_name='Ингредиенты')
    text = models.TextField(default='', blank=True, verbose_name='Текст')
    image = models.ImageField(upload_to='recipe_images',
                              default='recipe_images/default.jpg',
                              verbose_name='Изображение')
    cooking_time = models.IntegerField(default=0,
                                       verbose_name='Время приготовления',
                                       validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='favorites',
                             verbose_name='Пользователь')
    recipes = models.ManyToManyField(Recipe,
                                     related_name='favorite_by',
                                     verbose_name='Рецепты')

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'

    def __str__(self):
        return self.user.username


class ShoppingCart(models.Model):
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='shopping_cart',
                             verbose_name='Пользователь')
    recipes = models.ManyToManyField(Recipe,
                                     related_name='in_shopping_carts',
                                     verbose_name='Рецепты')

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

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
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='subscriptions',
                             verbose_name='Пользователь')
    subscription = models.ManyToManyField(User,
                                          related_name='following',
                                          verbose_name='Подписка')
    objects = SubscriptionManager()

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return self.user.username
