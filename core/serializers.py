# core/serializers.py

from rest_framework import serializers
from .models import SiteSettings, Menu, MenuItem
from rest_framework import serializers
from .models import SiteSettings, Menu, MenuItem, CustomUser # CustomUser را اضافه کنید
from django.contrib.auth.password_validation import validate_password


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        # تمام فیلدهای مدل را شامل شود
        fields = '__all__'

class MenuItemChildrenSerializer(serializers.ModelSerializer):
    """
    یک سریالایزر برای نمایش فرزندان یک آیتم منو (برای منوهای تو در تو)
    """
    class Meta:
        model = MenuItem
        fields = ['title', 'url', 'order']


class MenuItemSerializer(serializers.ModelSerializer):
    # از سریالایزر بالا برای نمایش فرزندان استفاده میکنیم
    children = MenuItemChildrenSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['title', 'url', 'order', 'children']


class MenuSerializer(serializers.ModelSerializer):
    # فقط آیتمهای سطح بالا (که والد ندارند) را نمایش میدهیم
    # آیتمهای فرزند به صورت تو در تو در سریالایزر بالا نمایش داده میشوند
    items = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['name', 'slug', 'items']

    def get_items(self, obj):
        # فیلتر کردن آیتمهایی که والد ندارند
        top_level_items = obj.items.filter(parent__isnull=True)
        return MenuItemSerializer(top_level_items, many=True).instance
        
        # core/serializers.py



class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")

    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        # از متد create_user برای هش کردن صحیح رمز عبور استفاده می‌کنیم
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user