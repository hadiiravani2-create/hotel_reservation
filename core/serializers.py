# core/serializers.py
# version: 0.0.5
# FEATURE: Added WalletSerializer and WalletTransactionSerializer for the new wallet feature.

from rest_framework import serializers
from .models import SiteSettings, Menu, MenuItem, CustomUser, AgencyUserRole, Wallet, WalletTransaction
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

# --- Wallet Serializers ---

class WalletTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying a single wallet transaction.
    """
    # Use get_..._display() for choice fields to show human-readable values.
    transaction_type = serializers.CharField(source='get_transaction_type_display')
    
    class Meta:
        model = WalletTransaction
        fields = ['id', 'transaction_type', 'amount', 'description', 'created_at']


class WalletSerializer(serializers.ModelSerializer):
    """
    Serializer for the user's wallet, including balance and recent transactions.
    """
    # Fetch recent transactions using a serializer method field.
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['balance', 'recent_transactions']

    def get_recent_transactions(self, obj):
        # Retrieve the 10 most recent transactions for the wallet.
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
    class Meta:
        model = CustomUser
        fields = ['username', 'agency_role']


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(
        label=("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        max_length=128,
        write_only=True
    )
    user = serializers.HiddenField(default=None, write_only=True) 

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            
            if not user:
                msg = ('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = ('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


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
        
        if attrs.get('agency') and not attrs.get('agency_role'):
            raise serializers.ValidationError({"agency_role": "نقش کاربر آژانس الزامی است."})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password2')

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
