import os
import requests
import redis
import json
import time
from datetime import datetime, timedelta

telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
redis_host = os.getenv('REDIS_HOST')
redis_port = os.getenv('REDIS_PORT')
redis_username = os.getenv('REDIS_USERNAME')
redis_password = os.getenv('REDIS_PASSWORD')

redis_client = redis.Redis(
    host=redis_host,
    port=int(redis_port),
    username=redis_username,
    password=redis_password,
    decode_responses=True
)

divar_api_url = "https://api.divar.ir/v8/postlist/w/search"
telegram_message_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"


def save_divar_tokens(tokens_info):
    redis_client.set("divar_tokens", json.dumps(tokens_info))

def load_divar_tokens():
    tokens_data = redis_client.get("divar_tokens")
    return json.loads(tokens_data) if tokens_data else None 

def send_telegram_message(message_content):
    message_payload = {
        "chat_id": telegram_chat_id,
        "text": message_content,
        "parse_mode": "HTML"
    }
    response = requests.post(telegram_message_url, data=message_payload, timeout=10)
    if response.status_code != 200:
        print(f"Error sending message: {response.status_code}")
    time.sleep(5)


divar_initial_post_request = {
    "city_ids": [
        "12", "824", "825", "1852", "1812", "1688", "1854", "708", "1841", "829", "1855",
        "1850", "864", "1686", "1844", "1847", "1689", "1809", "1814", "1851", "1839", "1835",
        "1684", "1810", "1849", "826", "1683", "1811", "861", "1813", "1845", "827", "860", "863",
        "1840", "1843", "1687", "1846", "746", "1690", "828", "1836", "1842", "1837", "1848", "862",
        "1853", "1815", "1834", "1969", "1983", "1994", "2000", "2004", "2007", "2011"
    ],
    "pagination_data": {
        "@type": "type.googleapis.com/post_list.PaginationData",
        "last_post_date": None,
        "page": 1,
        "layer_page": 1
    },
    "disable_recommendation": False,
    "search_data": {"form_data": {"data": {"category": {"str": {"value": "cars"}}}}}
}

loaded_tokens = load_divar_tokens()

if not loaded_tokens:
    all_tokens = []
    response = requests.post(divar_api_url, json=divar_initial_post_request)
    response_data = response.json()
    initial_last_post_date = response_data["pagination"]["data"].get("last_post_date", None)
    
    if not initial_last_post_date:
        print("Error: No initial_last_post_date found!")
        exit()

    initial_last_post_date_dt = datetime.strptime(initial_last_post_date, "%Y-%m-%dT%H:%M:%S.%fZ")
    time_threshold = initial_last_post_date_dt - timedelta(days=50)
    date_limit = time_threshold.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    while True:
        response = requests.post(divar_api_url, json=divar_initial_post_request)
        response_data = response.json()
        tokens = response_data["action_log"]["server_side_info"]["info"].get("tokens", [])
        all_tokens.extend(tokens)
        has_next_page = response_data["pagination"].get("has_next_page", False)
        new_last_post_date = response_data["pagination"]["data"].get("last_post_date", None)
        if new_last_post_date and new_last_post_date < date_limit:
            break
        if has_next_page:
            divar_initial_post_request["pagination_data"]["last_post_date"] = new_last_post_date
            divar_initial_post_request["pagination_data"]["page"] += 1
        else:
            break
    loaded_tokens = all_tokens


divar_post_request = {
    "city_ids": [
        "12", "824", "825", "1852", "1812", "1688", "1854", "708", "1841", "829", "1855",
        "1850", "864", "1686", "1844", "1847", "1689", "1809", "1814", "1851", "1839", "1835",
        "1684", "1810", "1849", "826", "1683", "1811", "861", "1813", "1845", "827", "860", "863",
        "1840", "1843", "1687", "1846", "746", "1690", "828", "1836", "1842", "1837", "1848", "862",
        "1853", "1815", "1834", "1969", "1983", "1994", "2000", "2004", "2007", "2011"
    ],
    "pagination_data": {
        "@type": "type.googleapis.com/post_list.PaginationData",
        "last_post_date": None,
        "page": 1,
        "layer_page": 1,
        "search_uid": "722d47b0-5c96-44ba-9298-7a9c79edc9ac"
    },
    "disable_recommendation": False,
    "map_state": {
        "camera_info": {
            "bbox": {}
        }
    },
    "search_data": {
        "form_data": {
            "data": {
                "category": {
                    "str": {
                        "value": "cars"
                    }
                },
                "price": {
                    "number_range": {
                        "maximum": "250000000"
                    }
                },
                "production-year": {
                    "number_range": {
                        "minimum": "1385"
                    }
                }
            }
        },
        "server_payload": {
            "@type": "type.googleapis.com/widgets.SearchData.ServerPayload",
            "additional_form_data": {
                "data": {
                    "sort": {
                        "str": {
                            "value": "sort_date"
                        }
                    }
                }
            }
        }
    }
}

response = requests.post(divar_api_url, json=divar_post_request)
if response.status_code != 200:
    print(f"Error fetching posts: {response.status_code}")
    exit()

response_data = response.json()
first_post_date = response_data["pagination"]["data"].get("last_post_date", None)
if not first_post_date:
    print("Error: No first_post_date found!")
    exit()

first_post_date_dt = datetime.strptime(first_post_date, "%Y-%m-%dT%H:%M:%S.%fZ")
time_threshold = first_post_date_dt - timedelta(days=1)
date_limit = time_threshold.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

while True:
    response = requests.post(divar_api_url, json=divar_post_request)
    if response.status_code != 200:
        print(f"Error fetching posts: {response.status_code}")
        break

    response_data = response.json()
    has_next_page = response_data["pagination"].get("has_next_page", False)
    new_last_post_date = response_data["pagination"]["data"].get("last_post_date", None)
    list_widgets = response_data["list_widgets"]
    seo_linked_data = response_data["seo_details"]["linked_data"]

    for i in range(len(list_widgets)):
        post_token = list_widgets[i].get('data', {}).get('token', "")
        if post_token not in loaded_tokens:
            loaded_tokens.append(post_token)

            offer_price = int(seo_linked_data[i].get('offers', {}).get('price', "0"))
            if offer_price > 2500000000 or offer_price < 800000000:
                continue

            post_title = list_widgets[i].get('data', {}).get('title', "")
            vehicle_color = seo_linked_data[i].get('color', "")
            transmission_type = seo_linked_data[i].get('vehicleTransmission', "")
            post_top_description = list_widgets[i].get('data', {}).get('top_description_text', "")
            post_middle_description = list_widgets[i].get('data', {}).get('middle_description_text', "")
            post_bottom_description = list_widgets[i].get('data', {}).get('bottom_description_text', "")
            vehicle_description = seo_linked_data[i].get('description', "")
            image_count = list_widgets[i].get('data', {}).get('image_count', "")
            image_url = list_widgets[i].get('data', {}).get('image_url', "")
            ad_url = seo_linked_data[i].get('url', "")

            telegram_message = f"""<b>{post_title}</b>
            
{post_top_description}
{post_middle_description}

رنگ {vehicle_color}
گیربکس {transmission_type}
توضیحات
{vehicle_description}

<a href="{ad_url}">لینک مشاهده آگهی</a>

{post_bottom_description}
تعداد تصاویر: {image_count}
<a href="{image_url}"> </a>
            """
            send_telegram_message(telegram_message)

    if new_last_post_date and new_last_post_date < date_limit:
        break
    if has_next_page:
        divar_post_request["pagination_data"]["last_post_date"] = new_last_post_date
        divar_post_request["pagination_data"]["page"] += 1
    else:
        break

save_divar_tokens(loaded_tokens)
