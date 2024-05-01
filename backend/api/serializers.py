from django.contrib.auth.models import User
from djoser.serializers import (UserCreateSerializer as
                                BaseUserRegistrationSerializer)
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Subscriptions, Tag)


def validate_image(value):
    if not value:
        raise serializers.ValidationError(
            "Поле image не может быть пустым.")
    return value


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username',
                  'first_name', 'last_name',
                  'email', 'is_subscribed']

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if (request
                and hasattr(request, "user")
                and request.user.is_authenticated):
            if obj == request.user:
                return False
            is_subscribed = Subscriptions.objects.is_subscribed(
                user=request.user, author=obj)
            return is_subscribed
        return False


class RegistrationSerializer(BaseUserRegistrationSerializer):
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True)

    class Meta(BaseUserRegistrationSerializer.Meta):
        fields = ('id', 'email', 'username',
                  'password', 'first_name', 'last_name')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Данная почта уже занята.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        ShoppingCart.objects.create(user=user)
        Favorite.objects.create(user=user)
        Subscriptions.objects.create(user=user)
        return user


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "measurement_unit"]


class ShoppingCartAndFavoritesSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    def validate_image(self, value):
        return validate_image(value)

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['is_subscribed',
                                               'recipes',
                                               'recipes_count']

    def get_recipes(self, obj):
        recipes_limit = self.context.get('request').query_params.get(
            'recipes_limit', None)
        recipes = Recipe.objects.filter(
            author=obj)[:int(recipes_limit) if recipes_limit else None]
        return ShoppingCartAndFavoritesSerializer(recipes, many=True,
                                                  context=self.context).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.IntegerField(min_value=0)

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'measurement_unit', 'amount']


class CreateRecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1, max_value=100000)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(source='recipe_ingredients',
                                             many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = "__all__"

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user and not user.is_anonymous:
            return Favorite.objects.filter(user=user, recipes=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user and not user.is_anonymous:
            return ShoppingCart.objects.filter(user=user, recipes=obj).exists()
        return False


class CreateRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    ingredients = CreateRecipeIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(),
                                              many=True)
    name = serializers.CharField(max_length=200)
    text = serializers.CharField(allow_null=False)
    cooking_time = serializers.IntegerField(allow_null=False, min_value=1)

    class Meta:
        model = Recipe
        fields = ['name', 'image', 'text',
                  'cooking_time', 'ingredients', 'tags']

    def validate(self, data):
        ingredients_data = data.get('ingredients')
        tags = data.get('tags')

        if not tags or len(tags) == 0:
            raise serializers.ValidationError(
                "Рецепт должен содержать хотя бы один тег.")

        if len(tags) != len(set(tags)):
            raise serializers.ValidationError("Теги должны быть уникальными.")

        for tag in tags:
            if not Tag.objects.filter(id=tag.id).exists():
                raise serializers.ValidationError(
                    f"Тег с ID {tag.id} не был найден.")

        if not isinstance(ingredients_data, list):
            raise serializers.ValidationError(
                "Не был получен список ингредиентов.")

        if not ingredients_data or len(ingredients_data) == 0:
            raise serializers.ValidationError(
                "Рецепт должен содержать хотя бы один ингредиент.")

        if len(ingredients_data) != len(set(tuple(ingredient.items())
                                            for ingredient
                                            in ingredients_data)):
            raise serializers.ValidationError(
                "Ингредиенты должны быть уникальными.")

        return data

    def validate_image(self, value):
        return validate_image(value)

    def update_ingredients(self, recipe, ingredients_data):
        new_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'].id,
                amount=ingredient['amount']
            ) for ingredient in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(new_ingredients)

    def create(self, validated_data):

        cooking_time = validated_data.pop('cooking_time')
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(author=self.context['request'].user,
                                       cooking_time=cooking_time,
                                       **validated_data)

        self.update_ingredients(recipe, ingredients_data)

        recipe.tags.set(tags_data)

        return recipe

    def update(self, instance, validated_data):

        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance = super().update(instance, validated_data)
        RecipeIngredient.objects.filter(recipe=instance).delete()
        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            self.update_ingredients(instance, ingredients_data)

        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data
