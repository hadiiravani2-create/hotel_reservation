# reservation_system/celery.py

import os
from celery import Celery

# تنظیم متغیر محیطی پیش‌فرض برای تنظیمات جنگو
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_system.settings')

app = Celery('reservation_system')

# خواندن تنظیمات از فایل settings.py جنگو
app.config_from_object('django.conf:settings', namespace='CELERY')

# پیدا کردن و بارگذاری خودکار تسک‌ها از تمام اپلیکیشن‌های ثبت شده
app.autodiscover_tasks()
