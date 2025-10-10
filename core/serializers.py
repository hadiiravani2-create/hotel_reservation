# core/serializers.py
# version: 0.0.4
from rest_framework import serializers
from .models import SiteSettings, Menu, MenuItem, CustomUser, AgencyUserRole
from django.contrib.auth.password_validation import validate_password
from django.conf import settings  # Import settings for MEDIA_URL
from rest_framework.authtoken.models import Token # Import Token for user registration
from django.contrib.auth import authenticate  # NEW: Import for login logic

# --- Site Settings Serializers ---

class SiteSettingsSerializer(serializers.ModelSerializer):
    # FIX 1.1: Explicitly define logo_url using SerializerMethodField
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SiteSettings
        # List all fields explicitly for clarity
        fields = ('site_name', 'logo_url', 'slogan', 'favicon', 'primary_color', 'secondary_color', 'text_color', 'phone_number', 'email', 'address', 'instagram_url', 'telegram_url', 'whatsapp_url', 'footer_text', 'enamad_code', 'copyright_text')

    def get_logo_url(self, obj):
        # FIX 1.2: Explicitly prepend settings.MEDIA_URL to ensure the frontend receives the full path.
        # This resolves the missing '/media/' prefix (e.g., returns /media/site_settings/miri-logo2.png).
        if obj.logo:
            return f"{settings.MEDIA_URL}{obj.logo.name}"
        return None

# --- Menu Serializers ---

class MenuItemChildrenSerializer(serializers.ModelSerializer):
    """
    A serializer to display the children of a menu item (for nested menus).
    """
    class Meta:
        model = MenuItem
        fields = ['title', 'url', 'order']


class MenuItemSerializer(serializers.ModelSerializer):
    # Use the above serializer to display children
    children = MenuItemChildrenSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['title', 'url', 'order', 'children']


class MenuSerializer(serializers.ModelSerializer):
    # Only display top-level items (those without a parent)
    items = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['name', 'slug', 'items']

    def get_items(self, obj):
        # FIX 2: This method is now cleanly defined within the class structure, resolving the AttributeError.
        # Filter items that do not have a parent
        top_level_items = obj.items.filter(parent__isnull=True)
        # Use .data to return serialized data, not the instance
        return MenuItemSerializer(top_level_items, many=True).data
        
        
class AgencyUserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgencyUserRole
        fields = ['id', 'name']

# NEW: Serializer for User object in Auth Response
class UserAuthSerializer(serializers.ModelSerializer):
    # Use nested serializer for agency_role to get its name
    agency_role = AgencyUserRoleSerializer(read_only=True)
    class Meta:
        model = CustomUser
        # Only fields needed by the frontend's AuthContext
        fields = ['username', 'agency_role']

# NEW: Serializer for User Login (Auth Input)
class UserLoginSerializer(serializers.Serializer):
    """Serializer for authenticating users."""
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(
        label=("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        max_length=128,
        write_only=True
    )
    # The 'user' field will hold the validated user object
    user = serializers.HiddenField(default=None, write_only=True) 

    def validate(self, attrs):
        # Authenticate user using Django's built-in function
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            
            # The authenticate call returns the user if successful, or None otherwise.
            if not user:
                msg = ('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = ('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        # Store the validated user instance in the serializer instance data
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
        
        # بررسی منطق نقش آژانس
        if attrs.get('agency') and not attrs.get('agency_role'):
            raise serializers.ValidationError({"agency_role": "نقش کاربر آژانس الزامی است."})

        return attrs

    def create(self, validated_data):
        # حذف فیلدهای غیرضروری برای ایجاد کاربر
        password = validated_data.pop('password')
        validated_data.pop('password2')

        # ایجاد کاربر و تنظیم پسورد
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
        # Ensure token is created after user registration
        Token.objects.create(user=user) 
        return user
    
    def to_representation(self, instance):
        """Override to ensure the correct fields are returned, especially nested agency_role."""
        # Use the dedicated serializer for a clean user object expected by the AuthContext
        # Note: This is crucial for the AuthResponse structure in the frontend
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
        # اطمینان از اینکه فیلد agency توسط view تنظیم می‌شود و نه کاربر
        password = validated_data.pop('password')
        # Note: CustomUser does not have a create_user manager method, using create and set_password
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user
