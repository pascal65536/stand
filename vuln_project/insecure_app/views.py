import pickle
import yaml
import os
import subprocess
import hashlib
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.core.cache import cache
from django.conf import settings
from django.template import engines
from django.urls import reverse

# ============ УЯЗВИМОСТЬ 1: SQL Injection через .raw() с f-строкой ============
def user_search_raw(request):
    username = request.GET.get('username', '')
    query = f"SELECT * FROM auth_user WHERE username = '{username}'"
    users = User.objects.raw(query)  # <-- Уязвимость! CWE-89
    return HttpResponse(f"Found {len(list(users))} users.")

# ============ УЯЗВИМОСТЬ 2: SQL Injection через .extra() ============
def user_search_extra(request):
    username = request.GET.get('username', '')
    users = User.objects.extra(where=[f"username = '{username}'"])  # <-- Уязвимость! CWE-89
    return HttpResponse(f"Found {len(list(users))} users.")

# ============ УЯЗВИМОСТЬ 3: XSS через render_template_string ============
def greet_user(request):
    name = request.GET.get('name', 'Anonymous')
    django_engine = engines['django']
    template = django_engine.from_string(f"<h1>Hello, {name}!</h1>")  # <-- Уязвимость! CWE-79 (XSS)
    return HttpResponse(template.render())

# ============ УЯЗВИМОСТЬ 4: Небезопасная десериализация (pickle) ============
@csrf_exempt
def load_pickle_data(request):
    if request.method == 'POST':
        data = pickle.loads(request.body)  # <-- Уязвимость! CWE-502
        return HttpResponse(f"Loaded: {data}")
    return HttpResponse("Send POST data.")

# ============ УЯЗВИМОСТЬ 5: Небезопасная десериализация (yaml) ============
@csrf_exempt
def load_yaml_data(request):
    if request.method == 'POST':
        data = yaml.load(request.body, Loader=yaml.FullLoader)  # <-- Уязвимость! CWE-502
        return HttpResponse(f"Loaded: {data}")
    return HttpResponse("Send POST data.")

# ============ УЯЗВИМОСТЬ 6: Отладка включена в settings.py ============
# Проверяется в settings.py: DEBUG = True, SECRET_KEY = '...' — CWE-16

# ============ УЯЗВИМОСТЬ 7: Пароль в GET-параметре (логгирование, кэш браузера) ============
def user_password(request):
    username = request.GET.get('username')
    password = request.GET.get('password')
    # Опасно! Пароль в GET попадает в логи сервера, историю браузера, кэш прокси.
    return HttpResponse(f"Found {username=} {password=}.")  # <-- Уязвимость! CWE-598, CWE-319

# ============ УЯЗВИМОСТЬ 8: Командная инъекция (Command Injection) ============
@csrf_exempt
def run_command(request):
    cmd = request.POST.get('cmd', '')
    # Опасно! Прямое выполнение команды из пользовательского ввода.
    output = subprocess.getoutput(cmd)  # <-- Уязвимость! CWE-78
    return HttpResponse(f"Output: {output}")

# ============ УЯЗВИМОСТЬ 9: Path Traversal (Directory Traversal) ============
def read_file(request):
    filename = request.GET.get('file', '')
    # Опасно! Позволяет читать произвольные файлы на сервере.
    with open(f"/var/www/uploads/{filename}", 'r') as f:  # <-- Уязвимость! CWE-22
        content = f.read()
    return HttpResponse(content)

# ============ УЯЗВИМОСТЬ 10: Небезопасное хеширование паролей ============
def set_password_insecure(request):
    password = request.POST.get('password', '')
    # Опасно! Использование слабого или неподходящего хеша для паролей.
    hashed = hashlib.md5(password.encode()).hexdigest()  # <-- Уязвимость! CWE-327, CWE-916
    return HttpResponse(f"Hashed: {hashed}")

# ============ УЯЗВИМОСТЬ 11: Отсутствие проверки прав доступа (Broken Access Control) ============
def delete_any_user(request, user_id):
    # Опасно! Любой пользователь может удалить любого другого, нет проверки прав.
    user = User.objects.get(id=user_id)
    user.delete()  # <-- Уязвимость! CWE-285, OWASP A01:2021
    return redirect('/')

# ============ УЯЗВИМОСТЬ 12: Небезопасное перенаправление (Open Redirect) ============
def redirect_user(request):
    next_url = request.GET.get('next', '/')
    # Опасно! Позволяет перенаправить пользователя на произвольный сайт (фишинг).
    return redirect(next_url)  # <-- Уязвимость! CWE-601

# ============ УЯЗВИМОСТЬ 13: Утечка информации через детальные ошибки ============
def crash_me(request):
    user_id = request.GET.get('id')
    # Опасно! Если DEBUG=True, пользователь увидит полный трейсбек с путями, переменными и т.д.
    user = User.objects.get(id=int(user_id))  # <-- Уязвимость! CWE-209, CWE-497
    return HttpResponse(f"User: {user.username}")

# ============ УЯЗВИМОСТЬ 14: Небезопасное кэширование чувствительных данных ============
def cache_user_data(request):
    username = request.GET.get('username')
    user = User.objects.get(username=username)
    # Опасно! Кэшируем объект пользователя, который может содержать email, пароль (хеш), ФИО.
    cache.set(f"user_{username}", user, timeout=3600)  # <-- Уязвимость! CWE-524, CWE-312
    return HttpResponse("Cached!")

# ============ УЯЗВИМОСТЬ 15: SSRF (Server-Side Request Forgery) ============
import requests

def fetch_url(request):
    url = request.GET.get('url')
    # Опасно! Сервер делает запрос на произвольный URL, указанный пользователем.
    # Может использоваться для атаки на внутренние сервисы (127.0.0.1, metadata и т.д.)
    response = requests.get(url)  # <-- Уязвимость! CWE-918
    return HttpResponse(response.text)

# ============ УЯЗВИМОСТЬ 16: Небезопасная генерация CSRF-токена (или его отключение) ============
@csrf_exempt  # <-- Явное отключение защиты CSRF!
def transfer_money(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        to_user = request.POST.get('to_user')
        # Опасно! Злоумышленник может заставить жертву выполнить этот запрос с ее сессией.
        # Пример: <img src="http://yoursite/transfer_money?amount=1000&to_user=hacker" />
        return HttpResponse(f"Transferred {amount} to {to_user}")  # <-- Уязвимость! CWE-352

# ============ УЯЗВИМОСТЬ 17: SSTI (Server-Side Template Injection) через Jinja2 ============
from jinja2 import Environment

def jinja_template(request):
    name = request.GET.get('name', 'World')
    # Опасно! Если используется Jinja2 и включено autoescape=False, можно выполнить код.
    env = Environment()  # По умолчанию autoescape=False!
    template = env.from_string(f"Hello, {{name}}!")  # <-- Уязвимость! CWE-94, CWE-74
    return HttpResponse(template.render(name=name))

# ============ УЯЗВИМОСТЬ 18: Утечка памяти через глобальный кэш (логическая утечка) ============
GLOBAL_CACHE = {}

def add_to_global_cache(request):
    key = request.GET.get('key')
    value = request.GET.get('value')
    # Опасно! Данные накапливаются в глобальной переменной без очистки → потребление памяти растет до OOM.
    GLOBAL_CACHE[key] = value  # <-- Уязвимость! Аналог "утечки памяти" (CWE-404, CWE-772)
    return HttpResponse(f"Cache size: {len(GLOBAL_CACHE)}")

# ============ УЯЗВИМОСТЬ 19: Использование небезопасного генератора случайных чисел ============
import random

def generate_token_insecure(request):
    # Опасно! `random` не криптографически безопасен. Токен можно предсказать.
    token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=32))  # <-- Уязвимость! CWE-338
    return HttpResponse(f"Token: {token}")

# ============ УЯЗВИМОСТЬ 20: Хранение секретов в коде ============
# Это проверяется в settings.py, но можно и так:
API_KEY = "sk_test_1234567890abcdef"  # <-- Уязвимость! CWE-798, CWE-259
def use_api_key(request):
    return HttpResponse(f"Using API Key: {API_KEY}")