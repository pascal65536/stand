from django.urls import path
from . import views

urlpatterns = [
    # ============ УЯЗВИМОСТЬ 1: SQL Injection через .raw() с f-строкой ============
    path("search/raw/", views.user_search_raw, name="user_search_raw"),
    # ============ УЯЗВИМОСТЬ 2: SQL Injection через .extra() ============
    path("search/extra/", views.user_search_extra, name="user_search_extra"),
    # ============ УЯЗВИМОСТЬ 3: XSS через render_template_string ============
    path("greet/", views.greet_user, name="greet_user"),
    # ============ УЯЗВИМОСТЬ 4: Небезопасная десериализация (pickle) ============
    path("pickle/load/", views.load_pickle_data, name="load_pickle_data"),
    # ============ УЯЗВИМОСТЬ 5: Небезопасная десериализация (yaml) ============
    path("yaml/load/", views.load_yaml_data, name="load_yaml_data"),
    # ============ УЯЗВИМОСТЬ 7: Пароль в GET-параметре ============
    path("user/password/", views.user_password, name="user_password"),
    # ============ УЯЗВИМОСТЬ 8: Командная инъекция ============
    path("command/run/", views.run_command, name="run_command"),
    # ============ УЯЗВИМОСТЬ 9: Path Traversal ============
    path("file/read/", views.read_file, name="read_file"),
    # ============ УЯЗВИМОСТЬ 10: Небезопасное хеширование паролей ============
    path("password/set/", views.set_password_insecure, name="set_password_insecure"),
    # ============ УЯЗВИМОСТЬ 11: Отсутствие проверки прав доступа ============
    path("user/delete/<int:user_id>/", views.delete_any_user, name="delete_any_user"),
    # ============ УЯЗВИМОСТЬ 12: Небезопасное перенаправление (Open Redirect) ============
    path("redirect/", views.redirect_user, name="redirect_user"),
    # ============ УЯЗВИМОСТЬ 13: Утечка информации через детальные ошибки ============
    path("crash/", views.crash_me, name="crash_me"),
    # ============ УЯЗВИМОСТЬ 14: Небезопасное кэширование чувствительных данных ============
    path("cache/user/", views.cache_user_data, name="cache_user_data"),
    # ============ УЯЗВИМОСТЬ 15: SSRF ============
    path("fetch/url/", views.fetch_url, name="fetch_url"),
    # ============ УЯЗВИМОСТЬ 16: CSRF (отключена защита) ============
    path("transfer/money/", views.transfer_money, name="transfer_money"),
    # ============ УЯЗВИМОСТЬ 17: SSTI через Jinja2 ============
    path("jinja/greet/", views.jinja_template, name="jinja_template"),
    # ============ УЯЗВИМОСТЬ 18: Утечка памяти через глобальный кэш ============
    path("cache/add/", views.add_to_global_cache, name="add_to_global_cache"),
    # ============ УЯЗВИМОСТЬ 19: Небезопасный генератор случайных чисел ============
    path(
        "token/generate/", views.generate_token_insecure, name="generate_token_insecure"
    ),
    # ============ УЯЗВИМОСТЬ 20: Хранение секретов в коде ============
    path("api/key/", views.use_api_key, name="use_api_key"),
]
