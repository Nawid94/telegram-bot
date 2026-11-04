import os
import sys
import html
import time
import json
import logging
from datetime import datetime, timedelta

import requests
import redis

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("divar-bot")

# ==================================================================
# ⚙️ تنظیمات فیلترها (اینجا را تغییر دهید)
# ==================================================================
SEARCH_MAX_PRICE_TOMAN = 1_600_000_000
SEARCH_MIN_PRICE_TOMAN = 50_000_000
SEARCH_MIN_PRODUCTION_YEAR = "1386"

# ─── فیلترهای سمت سرور — دقیقاً مطابق payload واقعی دیوار ───
SERVER_CATEGORY       = "light"
SERVER_CHASSIS_STATUS = "both-healthy"
SERVER_MOTOR_STATUS   = "healthy"
SERVER_BODY_STATUS    = ["intact", "some-scratches"]
SERVER_FUEL_TYPE      = ["benzine"]

# 🌆 شهرهای فعال — شهرهای یک استان (طبق payload واقعی)
TARGET_CITY_IDS = ["889"]

# ==================================================================
# 🌆 لیست منتخب شهرها (فقط جهت مراجعه — کامنت‌شده)
# ------------------------------------------------------------------
# CITY_IDS_REFERENCE = [
#     "12", "824", "825", "1852", "1812", "1688", "1854", "708", "1841", "829", "1855",
#     "1850", "864", "1686", "1844", "1847", "1689", "1809", "1814", "1851", "1839", "1835",
#     "1684", "1810", "1849", "826", "1683", "1811", "861", "1813", "1845", "827", "860", "863",
#     "1840", "1843", "1687", "1846", "746", "1690", "828", "1836", "1842", "1837", "1848", "862",
#     "1853", "1815", "1834", "1969", "1983", "1994", "2000", "2004", "2007", "2011",
# ]
# ==================================================================


# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT") or 6379)
REDIS_USERNAME = os.getenv("REDIS_USERNAME") or "default"
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

missing = [k for k, v in {
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    "REDIS_HOST": REDIS_HOST,
    "REDIS_PASSWORD": REDIS_PASSWORD,
}.items() if not v]
if missing:
    log.error("Missing required env vars: %s", ", ".join(missing))
    sys.exit(1)

DIVAR_API_URL = "https://api.divar.ir/v8/postlist/w/search"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
MIN_POOL_SIZE_FOR_PRUNE = 20

# ─── شناسهٔ سشن جستجوی دیوار (ثابت، بدون نیاز به env) ───
DIVAR_SEARCH_UID = "5df7f4fd-5839-4108-accd-fda27178a0a5"

# ─── پیشوند ثابت لینک آگهی دیوار ───
DIVAR_AD_BASE_URL = "https://divar.ir/v/"

# ------------------------------------------------------------------
# Redis
# ------------------------------------------------------------------
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        username=REDIS_USERNAME,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
    )
    redis_client.ping()
except Exception as e:
    log.error("Cannot connect to Redis: %s", e)
    sys.exit(1)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def request_with_retry(url, timeout=20, **kwargs):
    last_exc = None
    for attempt in range(1, 4):
        try:
            resp = requests.post(url, timeout=timeout, **kwargs)
            if resp.status_code == 200:
                return resp
            log.warning("HTTP %s on attempt %d from %s", resp.status_code, attempt, url)
        except requests.RequestException as e:
            last_exc = e
            log.warning("Request error on attempt %d: %s", attempt, e)
        time.sleep(2 ** attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Request to {url} failed after 3 attempts")


def load_tokens():
    try:
        data = redis_client.get("divar_tokens")
        return json.loads(data) if data else []
    except Exception as e:
        log.warning("Failed to load tokens from Redis: %s", e)
        return []


def save_tokens(tokens_list):
    try:
        redis_client.set("divar_tokens", json.dumps(tokens_list))
    except Exception as e:
        log.error("Failed to save tokens to Redis: %s", e)


def send_telegram(text):
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(TELEGRAM_URL, data=payload, timeout=15)
        if r.status_code != 200:
            log.error("Telegram error %s: %s", r.status_code, r.text[:200])
            return False
        return True
    except requests.RequestException as e:
        log.error("Telegram request failed: %s", e)
        return False


def get_city(widget):
    """نام شهر را از مسیر action.payload.web_info.city_persian استخراج می‌کند."""
    d = widget.get("data", {}) or {}
    web_info = (d.get("action") or {}).get("payload", {}).get("web_info", {}) or {}
    return web_info.get("city_persian") or ""


# ==================================================================
# 🔧 فیلترهای سمت سرور — دقیقاً مطابق payload واقعی دیوار
# ==================================================================
def build_search_request():
    price_inner = {"maximum": str(SEARCH_MAX_PRICE_TOMAN)}
    if SEARCH_MIN_PRICE_TOMAN is not None and SEARCH_MIN_PRICE_TOMAN > 0:
        price_inner["minimum"] = str(SEARCH_MIN_PRICE_TOMAN)

    # تکرار داخل value — دقیقاً مطابق فرمت واقعی دیوار
    price_filter = dict(price_inner)
    price_filter["value"] = dict(price_inner)

    return {
        "source_view": "FILTER",
        "city_ids": TARGET_CITY_IDS,
        "pagination_data": {
            "@type": "type.googleapis.com/post_list.PaginationData",
            "last_post_date": None,
            "page": 1,
            "layer_page": 1,
            "search_uid": DIVAR_SEARCH_UID,
        },
        "disable_recommendation": False,
        "map_state": {"camera_info": {"bbox": {}}},
        "search_data": {
            "form_data": {
                "data": {
                    "category":       {"str": {"value": SERVER_CATEGORY}},
                    "chassis_status": {"str": {"value": SERVER_CHASSIS_STATUS}},
                    "motor_status":   {"str": {"value": SERVER_MOTOR_STATUS}},
                    "body_status":    {"repeated_string": {"value": SERVER_BODY_STATUS}},
                    "fuel_type":      {"repeated_string": {"value": SERVER_FUEL_TYPE}},
                    "price":          {"number_range": price_filter},
                    "production-year": {
                        "number_range": {
                            "minimum": SEARCH_MIN_PRODUCTION_YEAR,
                            "value": {"minimum": SEARCH_MIN_PRODUCTION_YEAR},
                        }
                    },
                }
            },
            "server_payload": {
                "@type": "type.googleapis.com/widgets.SearchData.ServerPayload",
                "additional_form_data": {
                    "data": {"sort": {"str": {"value": "sort_date"}}}
                },
            },
        },
        "user_selected_location": {
            "places": [{"place_id": cid} for cid in TARGET_CITY_IDS]
        },
        "previous_user_selected_location": {"places": []},
    }
# ==================================================================


def bootstrap_tokens():
    """پُرکردن اولیهٔ Redis با توکن‌های ۵۰ روز اخیر (بدون ارسال پیام)."""
    log.info("Redis empty — bootstrapping tokens for last 50 days")
    req = build_search_request()   # ← فیلترها اعمال می‌شن

    try:
        resp = request_with_retry(DIVAR_API_URL, json=req)
    except Exception as e:
        log.error("Bootstrap initial request failed: %s", e)
        return []

    last_date = resp.json().get("pagination", {}).get("data", {}).get("last_post_date")
    if not last_date:
        log.error("No initial last_post_date — aborting bootstrap")
        return []

    last_dt = datetime.strptime(last_date, "%Y-%m-%dT%H:%M:%S.%fZ")
    date_limit = (last_dt - timedelta(days=50)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    tokens = set()
    while True:
        try:
            resp = request_with_retry(DIVAR_API_URL, json=req)
        except Exception as e:
            log.error("Bootstrap page request failed: %s", e)
            break
        data = resp.json()
        tokens.update(
            data.get("action_log", {})
                .get("server_side_info", {})
                .get("info", {})
                .get("tokens", [])
        )
        new_last = data.get("pagination", {}).get("data", {}).get("last_post_date")
        has_next = data.get("pagination", {}).get("has_next_page", False)
        if new_last and new_last < date_limit:
            break
        if has_next and new_last:
            req["pagination_data"]["last_post_date"] = new_last
            req["pagination_data"]["page"] += 1
        else:
            break

    log.info("Bootstrap collected %d unique tokens", len(tokens))
    return list(tokens)


def format_message(widget):
    """پیام تلگرام را فقط از فیلدهای موجود در data و web_info می‌سازد."""
    d = widget.get("data", {}) or {}
    title = html.escape(d.get("title") or "")
    middle = html.escape(d.get("middle_description_text") or "")
    top = html.escape(d.get("top_description_text") or "")
    image_count = d.get("image_count", "0")
    image_url = d.get("image_url", "")
    city = html.escape(get_city(widget))

    # ─── لینک آگهی از توکن ───
    token = d.get("token", "")
    ad_url = f"{DIVAR_AD_BASE_URL}{token}" if token else ""

    parts = [
        f"<b>{title}</b>",
        f"<b>{middle}</b>",
        "",
        f"کارکرد {top}",
    ]
    if city:
        parts.append(f"شهر {city}")
    parts.append("")
    if ad_url:
        parts.append(f'<a href="{ad_url}">لینک مشاهده آگهی</a>')
    if image_url:
        parts.append(f'<a href="{image_url}">   </a>')
    parts.append(f"تعداد تصاویر {image_count} عدد")

    return "\n".join(parts)


def run():
    old_pool = set(load_tokens())

    if not old_pool:
        boot = bootstrap_tokens()
        save_tokens(boot)
        log.info("Bootstrap complete (%d tokens). Exiting without sending messages.", len(boot))
        return

    req = build_search_request()

    try:
        resp = request_with_retry(DIVAR_API_URL, json=req)
    except Exception as e:
        log.error("Initial fetch failed: %s", e)
        return

    first_date = resp.json().get("pagination", {}).get("data", {}).get("last_post_date")
    if not first_date:
        log.error("No first_post_date — aborting")
        return
    first_dt = datetime.strptime(first_date, "%Y-%m-%dT%H:%M:%S.%fZ")
    date_limit = (first_dt - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    current_pool = set()
    new_tokens = []
    sent_count = 0
    page = 0
    search_completed = False

    while True:
        page += 1
        try:
            resp = request_with_retry(DIVAR_API_URL, json=req)
        except Exception as e:
            log.error("Page %d request failed: %s", page, e)
            break

        data = resp.json()
        widgets = data.get("list_widgets") or []

        for widget in widgets:
            token = (widget.get("data") or {}).get("token", "")
            if not token:
                continue

            current_pool.add(token)

            if token in old_pool:
                continue

            new_tokens.append(token)

            # ⛔ اگر کلمه «حواله» در عنوان آگهی باشد، به تلگرام ارسال نشود
            title_raw = (widget.get("data") or {}).get("title") or ""
            if "حواله" in title_raw:
                log.info("Skipped Telegram send (title contains 'حواله'): %s", token)
                continue

            if send_telegram(format_message(widget)):
                sent_count += 1
            time.sleep(1)

            if len(new_tokens) % 10 == 0:
                save_tokens(list(old_pool | set(new_tokens)))
                log.info("Checkpoint (safe): %d tokens", len(old_pool | set(new_tokens)))

        new_last = (data.get("pagination") or {}).get("data", {}).get("last_post_date")
        has_next = (data.get("pagination") or {}).get("has_next_page", False)
        if new_last and new_last < date_limit:
            search_completed = True
            break
        if has_next and new_last:
            req["pagination_data"]["last_post_date"] = new_last
            req["pagination_data"]["page"] += 1
        else:
            search_completed = True
            break

    if search_completed and len(current_pool) >= MIN_POOL_SIZE_FOR_PRUNE:
        pruned_intersection = old_pool & current_pool
        final_pool = current_pool
        log.info(
            "Prune OK — old=%d, current=%d, intersection=%d, removed=%d, final=%d",
            len(old_pool),
            len(current_pool),
            len(pruned_intersection),
            len(old_pool) - len(pruned_intersection),
            len(final_pool),
        )
    else:
        final_pool = old_pool | set(new_tokens)
        log.warning(
            "Prune skipped (completed=%s, current_pool=%d). Safe union: %d tokens",
            search_completed, len(current_pool), len(final_pool),
        )

    save_tokens(list(final_pool))
    log.info("Run complete. Sent %d new ads. Memory: %d tokens.", sent_count, len(final_pool))


if __name__ == "__main__":
    run()
