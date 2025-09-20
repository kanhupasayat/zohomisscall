import os
import json
import requests
from dotenv import load_dotenv
from django.http import JsonResponse

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

ACCOUNTS_URL = "https://accounts.zoho.in/oauth/v2/token"
CRM_URL = "https://www.zohoapis.in/crm/v2/coql"
MISSCALL_URL = "https://misscall.onrender.com/api/missed-calls/"

ACCESS_TOKEN = None
BATCH_SIZE = 50   # ek baar me 50 number check
CACHE_RESULTS = {}   # in-memory cache


# ---------- Token ----------
def get_access_token():
    global ACCESS_TOKEN
    data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    resp = requests.post(ACCOUNTS_URL, data=data)
    if resp.status_code != 200:
        return None
    ACCESS_TOKEN = resp.json().get("access_token")
    return ACCESS_TOKEN


def request_with_auto_retry(url, headers, payload=None):
    """Zoho API call retry with refresh"""
    global ACCESS_TOKEN
    resp = requests.post(url, headers=headers, data=json.dumps(payload) if payload else None)
    if resp.status_code == 401:  # token expire
        ACCESS_TOKEN = get_access_token()
        if not ACCESS_TOKEN:
            return None
        headers["Authorization"] = f"Zoho-oauthtoken {ACCESS_TOKEN}"
        resp = requests.post(url, headers=headers, data=json.dumps(payload) if payload else None)
    return resp


# ---------- Missed Call ----------
def fetch_missed_call_numbers():
    try:
        response = requests.get(MISSCALL_URL)
        if response.status_code == 200:
            data = response.json()
            calls = data.get("unattended_missed_calls", [])
            numbers = [call["customer_number"].replace("+", "") for call in calls]
            return numbers
        else:
            print(f"Error: {response.status_code}")
            return []
    except Exception as e:
        print("Request failed:", e)
        return []


# ---------- Helper ----------
def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# ---------- Main Logic ----------
def check_lead_or_deal(phone_numbers):
    headers = {
        "Authorization": f"Zoho-oauthtoken {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    found_number = {}
    unknown_number = set()
    plan_slipped_numbers = set()
    consultation_done = set()
    plan_delivered_numbers = {}

    leads_found = set()

    # ✅ Sirf naye numbers hi Zoho se check karna hai
    new_numbers = [num for num in phone_numbers if num not in CACHE_RESULTS]

    # ---------- Leads ----------
    for batch in chunk_list(new_numbers, BATCH_SIZE):
        phone_list = ",".join([f"'{num}'" for num in batch])
        query = {
            "select_query": f"""
                select Full_Name, Owner, Phone
                from Leads
                where Phone in ({phone_list})
            """
        }
        resp_lead = request_with_auto_retry(CRM_URL, headers, query)
        if resp_lead and resp_lead.status_code == 200:
            data = resp_lead.json()
            if data.get("data"):
                for rec in data["data"]:
                    phone = rec.get("Phone")
                    leads_found.add(phone)
                    name = rec.get("Full_Name", "Unknown")
                    owner_id = rec.get("Owner", {}).get("id")
                    owner_name = {
                        "570692000000284001": "Akash Kumar",
                        "570692000000696001": "Dr. Harshit Kukreja",
                        "570692000001303016": "Rahul Namdeo",
                        "570692000015545001": "Rashid Hussain",
                        "570692000021553001": "Sahil Kumar",
                        "570692000021084001": "Team",
                        "570692000034410001": "Kuntal Ghosh",
                        "570692000064235701": "Alam Uddin",
                        "570692000031980001": "Suraj Giri",
                        "570692000003887001": "Sudhanshu Kumar",
                        "570692000015618001": "Vicky Routh",
                        "570692000034206008": "deep roy",
                        "570692000001307001": "Sonu Giri",
                        "570692000031974020": "Himanshu Goswami",
                        "570692000034410024": "Sourav Mondal",
                        "570692000064235703": "Sourav Mondal",
                        "570692000062859037": "Aman Ul Nawaz",
                        "570692000031974043": "Prince Kumar",
                        "570692000022523001": "Naresh Prajapati",
                        "570692000011216042": "Sumit Raghuwanshi",
                        "570692000062919131": "Fozlur Rahman",
                        "570692000017587001": "Kanhu Pasayat"
                    }.get(owner_id, f"Unknown ({owner_id})")

                    CACHE_RESULTS[phone] = {"type": "lead", "name": name, "owner": owner_name}

    # ---------- Deals ----------
    remaining_numbers = [num for num in new_numbers if num not in leads_found]

    for batch in chunk_list(remaining_numbers, BATCH_SIZE):
        phone_list_remaining = ",".join([f"'{num}'" for num in batch])
        query = {
            "select_query": f"""
                select Deal_Name, Stage, Phone, Raaz_Mitra, Owner
                from Deals
                where Phone in ({phone_list_remaining})
                order by Created_Time desc
            """
        }
        resp_deal = request_with_auto_retry(CRM_URL, headers, query)
        if resp_deal and resp_deal.status_code == 200:
            data = resp_deal.json()
            if data.get("data"):
                for rec in data["data"]:
                    phone = rec.get("Phone")
                    stage = rec.get("Stage")

                    if stage == "Plan Shipped":
                        CACHE_RESULTS[phone] = {"type": "plan_slipped"}

                    elif stage and stage.strip().lower() == "consultation done":
                        CACHE_RESULTS[phone] = {"type": "consultation_done"}

                    elif stage == "Plan  Delivered":
                        CACHE_RESULTS[phone] = {
                            "type": "plan_delivered",
                            "Raaz_Mitra": rec.get("Raaz_Mitra") or "None"
                        }

    # ---------- Cached Results load ----------
    for num in phone_numbers:
        result = CACHE_RESULTS.get(num)
        if result:
            if result["type"] == "lead":
                found_number[num] = {"name": result["name"], "owner": result["owner"]}

            elif result["type"] == "plan_slipped":
                plan_slipped_numbers.add(num)

            elif result["type"] == "consultation_done":
                consultation_done.add(num)

            elif result["type"] == "plan_delivered":
                raaz_mitra = result.get("Raaz_Mitra", "None")
                if raaz_mitra not in plan_delivered_numbers:
                    plan_delivered_numbers[raaz_mitra] = set()
                plan_delivered_numbers[raaz_mitra].add(num)

        else:
            unknown_number.add(num)

    # ✅ Convert sets back to list before returning
    return {
        "leads": found_number,
        "plan_slipped": list(plan_slipped_numbers),
        "consultation_done": list(consultation_done),
        "plan_delivered": {k: list(v) for k, v in plan_delivered_numbers.items()},
        "unknown": list(unknown_number)
    }


# ---------- Django View ----------
def check_numbers_view(request):
    global ACCESS_TOKEN
    ACCESS_TOKEN = get_access_token()
    if not ACCESS_TOKEN:
        return JsonResponse({"error": "Could not generate access token"}, status=400)

    phone_numbers = fetch_missed_call_numbers()
    result = check_lead_or_deal(phone_numbers)
    return JsonResponse(result, safe=False)
