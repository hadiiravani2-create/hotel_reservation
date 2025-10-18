# reservation_system/settings.py
"""
Django settings for reservation_system project.
"""
from pathlib import Path
import environ
import os  # <-- ایمپورت جدید و ضروری

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- START: Final and Robust Environment Variable Configuration ---
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# به صورت صریح مسیر کامل فایل .env را مشخص می‌کنیم
env_file_path = os.path.join(BASE_DIR, '.env')
environ.Env.read_env(env_file=env_file_path)
# --- END: Final and Robust Environment Variable Configuration ---

# خواندن متغیرها از محیط
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')


ALLOWED_HOSTS = ['192.168.10.131','2.180.44.137','demo.mirisafar.com','hotel.mirisafar.com']
CORS_ALLOWED_ORIGINS = [
    # ...
    "http://hotel.mirisafar.com", 
    # ...
    "http://192.168.10.131:3000",
    "http://localhost:3000", 
    # ...
]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Application definition
INSTALLED_APPS = [
    'jazzmin',
    'jalali_date',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core.apps.CoreConfig',
    'hotels.apps.HotelsConfig',
    'pricing.apps.PricingConfig',
    'agencies.apps.AgenciesConfig',
    'reservations.apps.ReservationsConfig',
    'rest_framework.authtoken',
    'notifications.apps.NotificationsConfig',
    'services'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'reservation_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'reservation_system.wsgi.application'

#CustomUser 
AUTH_USER_MODEL = 'core.CustomUser'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'hotelmiri_db',        # نام دیتابیس که ایجاد کردید
        'USER': 'iravani',    # نام کاربری PostgreSQL شما
        'PASSWORD': 'hadiir439@ODOO', # رمز عبور شما
        'HOST': 'localhost',       # یا آدرس سرور PostgreSQL
        'PORT': '5432'
    }
}

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': BASE_DIR / 'db.sqlite3',
#    }
#}




# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i1n/
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ADDED: Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

#django-jalali
JALALI_DATE_DEFAULTS = {
   'Strftime': {
        'date': '%y/%m/%d',
        'datetime': '%H:%M:%S _ %y/%m/%d',
    },
    'StaticFiles': False,
}

# CELERY SETTINGS
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

STATICFILES_DIRS = [BASE_DIR / 'static']

# JAZZMIN SETTINGS
JAZZMIN_SETTINGS = {
    # ... other settings
    "custom_css": "admin/css/jazzmin_rtl.css",
}
