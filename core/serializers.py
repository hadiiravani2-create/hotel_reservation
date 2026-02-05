# core/serializers.py
# version: 1.2.1
# FIX: Added missing import 'Q' from django.db.models
# FIX: Fixed variable name mismatch in UserLoginSerializer (username -> username_input)

from rest_framework import serializers
from django.db.models import Q  # [FIX] Added this import
from .models import SiteSettings, Menu, MenuItem, CustomUser, AgencyUserRole, Wallet, WalletTransaction, SpecialPeriod
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

# --- Wallet Serializers ---

class WalletTransactionSerializer(serializers.ModelSerializer):
    transaction_type = serializers.CharField(source='get_transaction_type_display')
    status = serializers.CharField(source='get_status_display')
    class Meta:
        model = WalletTransaction
        fields = ['id', 'transaction_type', 'amount', 'status', 'description', 'created_at']


class WalletSerializer(serializers.ModelSerializer):
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['balance', 'recent_transactions']

    def get_recent_transactions(self, obj):
        recent_transactions = obj.transactions.all()[:10]
        return WalletTransactionSerializer(recent_transactions, many=True).data


# --- Site Settings Serializers ---

class SiteSettingsSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SiteSettings
        fields = ('site_name', 'logo_url', 'slogan', 'favicon', 'primary_color', 'secondary_color', 'text_color', 'phone_number', 'email', 'address', 'instagram_url', 'telegram_url', 'whatsapp_url', 'footer_text', 'enamad_code', 'copyright_text')

    def get_logo_url(self, obj):
        if obj.logo:
            return f"{settings.MEDIA_URL}{obj.logo.name}"
        return None

# --- Menu Serializers ---
class SpecialPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialPeriod
        fields = ['id', 'name', 'start_date', 'end_date']

class MenuItemChildrenSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['title', 'url', 'order']


class MenuItemSerializer(serializers.ModelSerializer):
    children = MenuItemChildrenSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['title', 'url', 'order', 'children']


class MenuSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['name', 'slug', 'items']

    def get_items(self, obj):
        top_level_items = obj.items.filter(parent__isnull=True)
        return MenuItemSerializer(top_level_items, many=True).data
        
# --- User and Auth Serializers ---
        
class AgencyUserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgencyUserRole
        fields = ['id', 'name']


class UserAuthSerializer(serializers.ModelSerializer):
    agency_role = AgencyUserRoleSerializer(read_only=True)
    agency_id = serializers.ReadOnlyField(source='agency.id')
    
    class Meta:
        model = CustomUser
        # [FIX]: افزودن first_name و last_name به لیست فیلدها
        fields = ['username', 'mobile', 'email', 'first_name', 'last_name', 'agency_role', 'agency_id']

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255, label="شماره موبایل یا ایمیل")
    password = serializers.CharField(
        label=("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        max_length=128,
        write_only=True
    )
    user = serializers.HiddenField(default=None, write_only=True) 

    def validate(self, attrs):
        # [FIX] Variable name changed to matches the logic below
        username_input = attrs.get('username') 
        password = attrs.get('password')

        if username_input and password:
            # 1. Try to find the user by Mobile OR Email OR Username
            # [FIX] Q is now imported and works
            user_obj = CustomUser.objects.filter(
                Q(username=username_input) | 
                Q(email=username_input) | 
                Q(mobile=username_input)
            ).first()

            if user_obj:
                # 2. Authenticate using the found user's actual username field
                user = authenticate(request=self.context.get('request'),
                                    username=user_obj.username, password=password)
            else:
                user = None
            
            if not user:
                msg = ('اطلاعات ورود نامعتبر است.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = ('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class UserRegisterSerializer(serializers.ModelSerializer):
    mobile = serializers.CharField(required=True, validators=[]) 
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")

    class Meta:
        model = CustomUser
        fields = ('mobile', 'password', 'password2', 'email', 'first_name', 'last_name', 'agency', 'agency_role')
        extra_kwargs = {
            'agency': {'required': False, 'allow_null': True},
            'agency_role': {'required': False, 'allow_null': True},
        }

    def validate_mobile(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("شماره موبایل باید فقط شامل اعداد باشد.")
        if len(value) != 11:
            raise serializers.ValidationError("شماره موبایل باید ۱۱ رقم باشد.")
        if not value.startswith('09'):
            raise serializers.ValidationError("شماره موبایل باید با 09 شروع شود.")
        
        if CustomUser.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "رمز عبور و تکرار آن یکسان نیستند."})
        
        if attrs.get('agency') and not attrs.get('agency_role'):
            raise serializers.ValidationError({"agency_role": "نقش کاربر آژانس الزامی است."})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password2')
        mobile = validated_data.get('mobile')

        user = CustomUser.objects.create(
            username=mobile, 
            mobile=mobile,
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            agency=validated_data.get('agency', None),
            agency_role=validated_data.get('agency_role', None)
        )
        user.set_password(password)
        user.save()
        Token.objects.create(user=user) 
        return user
    
    def to_representation(self, instance):
        return UserAuthSerializer(instance).data


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
        password = validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user
