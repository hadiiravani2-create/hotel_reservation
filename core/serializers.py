# core/serializers.py

from rest_framework import serializers
from .models import SiteSettings, Menu, MenuItem
from rest_framework import serializers
from .models import SiteSettings, Menu, MenuItem, CustomUser, AgencyUserRole
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

class AgencyUserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgencyUserRole
        fields = ['id', 'name']


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")

    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name', 'agency', 'agency_role')
        extra_kwargs = {
            'agency': {'required': False, 'allow_null': True},
            'agency_role': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # بررسی منطق نقش آژانس
        if attrs.get('agency') and not attrs.get('agency_role'):
            raise serializers.ValidationError({"agency_role": "نقش کاربر آژانس الزامی است."})

        return attrs

    def create(self, validated_data):
        # حذف فیلدهای غیرضروری برای ایجاد کاربر
        password = validated_data.pop('password')
        validated_data.pop('password2')

        # از متد create_user برای هش کردن صحیح رمز عبور استفاده می‌کنیم
        user = CustomUser.objects.create(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            agency=validated_data.get('agency', None),
            agency_role=validated_data.get('agency_role', None)
        )
        user.set_password(password)
        user.save()
        return user

class AgencySubUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    agency_role = serializers.PrimaryKeyRelatedField(queryset=AgencyUserRole.objects.all())

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'agency_role']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        # اطمینان از اینکه فیلد agency توسط view تنظیم می‌شود و نه کاربر
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
