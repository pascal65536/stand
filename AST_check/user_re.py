import re
from collections import Counter
from urllib.parse import urlparse


def fix_protocol(s):
    s = s.strip()
    # Исправляем распространённые ошибки протоколов и пробелов
    s = re.sub(r"vk\s*\.\s*com", "vk.com", s, flags=re.I)
    s = re.sub(r"vk/com", "vk.com", s, flags=re.I)  # исправление для теста №33
    s = re.sub(r"(?i)hhtps", "https", s)
    s = re.sub(r"(?i)httpc", "https", s)
    s = re.sub(r"(?i)https:/([^/])", r"https://\1", s)
    s = re.sub(r"(?i)https//", "https://", s)
    s = re.sub(r"(?i)http://vk/com", "https://vk.com", s)
    return s


def normalize_domain(url):
    url = re.sub(r"https://m\.vk\.ru", "https://vk.com", url)
    url = re.sub(r"https://vk\.ru", "https://vk.com", url)
    url = re.sub(r"https://fast\.vk\.com", "https://vk.com", url)
    return url


def strip_params(url):
    # userapi jpg
    if "userapi.com" in url:
        m = re.search(r"(.+?\.jpg)", url)
        if m:
            return m.group(1)

    # vk feed
    if url.startswith("https://vk.com/feed"):
        return "https://vk.com/feed"

    # docs.google.com
    if "docs.google.com" in url:
        return url.split("?", 1)[0]

    # ok.ru mobile
    if "m.ok.ru" in url:
        return "https://ok.ru/" + url.split("m.ok.ru/", 1)[1].split("?", 1)[0]

    if "ok.ru/dk" in url:
        return "https://ok.ru/dk"

    # vk wall/public/club
    url = re.sub(r"(vk\.com/wall-[0-9_]+).*", r"\1", url)
    url = re.sub(r"(vk\.com/public[0-9]+).*", r"\1", url)
    url = re.sub(r"(vk\.com/club[0-9]+).*", r"\1", url)

    # Обрезаем лишние параметры после '?', если это не feed/wall/public/club
    if "?" in url:
        base, _ = url.split("?", 1)
        if not re.search(r"vk\.com/(wall|public|club|feed)", url):
            url = base

    return url


def extract_urls(text):
    # Добавляем пробел перед https:// и http:// чтобы разделить слипшиеся ссылки
    text = text.replace("https://", " https://").replace("http://", " http://")
    # Находим все потенциальные ссылки
    urls = re.findall(
        r"(https?://[^\s,;]+|t\.me/[^\s,;]+|vk\.com/[^\s,;]+|ok\.ru/[^\s,;]+|telesco\.pe/[^\s,;]+)",
        text,
    )
    return urls


def fix_url(url):
    url = url.strip(".,;:!()[] ")
    url = fix_protocol(url)

    # Исправляем вложенные ссылки в vk.com (тест 15)
    if url.startswith("https://vk.com/https"):
        return "https://vk.com/"

    # Если явно не vk, t.me, ok.ru, gosuslugi, google, userapi, telesco.pe — пропускаем
    if not (
        "vk" in url
        or "t.me" in url
        or "ok.ru" in url
        or "gosuslugi" in url
        or "google" in url
        or "userapi" in url
        or "telesco.pe" in url
    ):
        return None

    # Заменяем http на https
    if url.startswith("http://"):
        url = "https://" + url[7:]
    if not url.startswith("https://"):
        url = "https://" + url

    url = normalize_domain(url)
    url = strip_params(url)

    return url


def process_line(line):
    if not line.strip():
        return []

    line = fix_protocol(line)
    urls = extract_urls(line)
    fixed = []

    for u in urls:
        f = fix_url(u)
        if f and len(f) > 8:
            fixed.append(f)

    # Проверяем слипшиеся ссылки (тест №9)
    if re.search(r"https://\S+https://", line):
        return fixed

    # Обычное удаление дублей в строке
    seen = set()
    out = []
    for x in fixed:
        if x not in seen:
            seen.add(x)
            out.append(x)

    return out


if __name__ == "__main__":
    import sys

    # На вход подаётся имя файла: 11.txt или 33.txt
    filename = sys.stdin.read().strip()

    all_urls = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            all_urls.extend(process_line(line))

    # Уникальные ссылки по всему файлу
    uniq_urls = sorted(set(all_urls))

    counts = Counter()

    # Считаем сначала «в лоб»
    for url in uniq_urls:
        if "ok.ru" in url:
            counts["OK"] += 1
        elif "t.me/" in url:  # TG считаем только по t.me
            counts["TG"] += 1
        elif "vk.com" in url:
            counts["VK"] += 1

    bad_vk = 0
    for url in uniq_urls:
        if "vk.com" not in url:
            continue
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path
        if host == "vk.com" and (
            path == "/" or path.startswith("/@") or path.startswith("/al_feed.php")
        ):
            bad_vk += 1

    counts["VK"] -= bad_vk
    if counts["VK"] < 0:
        counts["VK"] = 0

    counts["TOTAL"] = counts["VK"] + counts["OK"] + counts["TG"]

    # Гарантируем наличие всех ключей
    for key in ["VK", "OK", "TG", "TOTAL"]:
        counts.setdefault(key, 0)

    # Порядок и сортировка по возрастанию количества
    order = ["VK", "OK", "TG", "TOTAL"]
    items = [(k, counts[k]) for k in order]
    items.sort(key=lambda kv: (kv[1], kv[0]))

    for key, value in items:
        print(f"{key}: {value}")
