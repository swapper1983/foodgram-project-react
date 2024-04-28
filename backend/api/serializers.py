# import base64

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
# from django.core.files.base import ContentFile
# from django.core.validators import MaxValueValidator, MinValueValidator
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Subscriptions, Tag)
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied


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
            f = Subscriptions.objects.is_subscribed(user=request.user,
                                                    author=obj)
            return f
        return False


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'},
                                     trim_whitespace=False)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)

            if not user:
                msg = 'Учётные данные некорректны.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Укажите email и пароль.'
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return token


class RegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    class Meta:
        model = User
        fields = "__all__"

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Данная почта уже занята.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        ShoppingCart.objects.create(user=user)
        Favorites.objects.create(user=user)
        Subscriptions.objects.create(user=user)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True,
                                         style={'input_type': 'password'})
    current_password = serializers.CharField(write_only=True, required=True,
                                             style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('new_password', 'current_password')

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Текущий пароль неверен.")
        return value

    def validate(self, data):
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError(
                "Новый пароль не должен быть таким же как и текущий.")
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
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
        if not value:
            raise serializers.ValidationError(
                "Поле image не может быть пустым.")
        return value

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
        recipes = Recipe.objects.filter(author=obj)[:int(recipes_limit)
                                                    if recipes_limit else None]
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
            return Favorites.objects.filter(user=user, recipes=obj).exists()
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
        # cooking_time = data.get('cooking_time')
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
        if not value:
            raise serializers.ValidationError(
                "Поле image не может быть пустым.")
        return value

    def create(self, validated_data):

        cooking_time = validated_data.pop('cooking_time')
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(author=self.context['request'].user,
                                       cooking_time=cooking_time,
                                       **validated_data)

        for ingredient_data in ingredients_data:
            ingredient = Ingredient.objects.get(id=ingredient_data['id'].id)
            RecipeIngredient.objects.create(recipe=recipe,
                                            ingredient=ingredient,
                                            amount=ingredient_data['amount'])

        recipe.tags.set(tags_data)

        return recipe

    def update(self, instance, validated_data):
        current_user = self.context['request'].user
        if instance.author != current_user:
            raise PermissionDenied("Вы не можете редактировать эту запись.")

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time',
                                                   instance.cooking_time)
        instance.image = validated_data.get('image', instance.image)
        instance.tags.set(validated_data.get('tags', instance.tags.all()))

        ingredients = validated_data.get('ingredients')
        RecipeIngredient.objects.filter(recipe=instance).delete()
        for ingredient in ingredients:
            RecipeIngredient.objects.create(recipe=instance,
                                            ingredient=ingredient['id'],
                                            amount=ingredient['amount'])

        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data
