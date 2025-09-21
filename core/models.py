# core/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # در حال حاضر، ما فیلد اضافه‌ای به مدل کاربر استاندارد جنگو اضافه نمی‌کنیم.
    # اما با ساختن این مدل، دست خود را برای آینده (مثلاً برای افزودن شماره موبایل)
    # کاملاً باز گذاشته‌ایم.
    pass
