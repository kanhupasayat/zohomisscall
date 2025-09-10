import os
import json
import time
import requests
import datetime
import pytz
import asyncio
import httpx
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.http import StreamingHttpResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 🔑 Zoho Credentials
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ACCOUNTS_URL = "https://accounts.zoho.in/oauth/v2/token"
CRM_API_URL = "https://www.zohoapis.in/crm/v2"

# 🔑 Knowlarity Credentials
X_API_KEY = os.getenv("X_API_KEY")
AUTHORIZATION_TOKEN = os.getenv("AUTHORIZATION_TOKEN")

# Configure session with retries (for Zoho API)
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))


# --------------------------- ZOHO TOKEN --------------------------- #
def get_access_token():
    """Fetch Zoho CRM access token using refresh token."""
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("Error: Missing Zoho environment variables")
        return None
    data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    try:
        response = session.post(ACCOUNTS_URL, data=data, timeout=(5, 30))
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Error generating access token: {e}")
        return None


# --------------------------- KNOWLARITY (ASYNC FETCH) --------------------------- #
async def fetch_page(client, url, headers, params):
    """Fetch a single page of call logs."""
    try:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print(f"[ERROR] Fetching page failed: {e}")
        return None


async def get_all_call_logs(url, headers, start_time, end_time, limit=500):
    """Fetch all call logs concurrently (fast)."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        # Get first page (to know total count)
        params = {'start_time': start_time, 'end_time': end_time, 'limit': limit, 'offset': 0}
        initial_data = await fetch_page(client, url, headers, params)
        if not initial_data:
            return []

        total_count = initial_data.get('meta', {}).get('total_count', 0)
        if total_count == 0:
            return []

        tasks = [
            fetch_page(client, url, headers, {
                'start_time': start_time,
                'end_time': end_time,
                'limit': limit,
                'offset': offset
            }) for offset in range(0, total_count, limit)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=False)
        all_calls = [call for result in results if result for call in result.get('objects', [])]
        return all_calls


def fetch_phone_numbers():
    """Fetch unattended missed calls from Knowlarity (last 48 hours)."""
    try:
        india_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(india_tz)
        start_time = (now - datetime.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")
        end_time = now.strftime("%Y-%m-%dT%H:%M:%S")

        url = 'https://kpi.knowlarity.com/Basic/v1/account/calllog'
        headers = {
            'x-api-key': X_API_KEY,
            'authorization': AUTHORIZATION_TOKEN,
            'content-type': "application/json",
        }

        all_calls = asyncio.run(get_all_call_logs(url, headers, start_time, end_time))
        if not all_calls:
            return []

        # Sort by time
        all_calls.sort(key=lambda x: x.get('start_time', ''))

        attended_calls, unattended_missed_calls = {}, []

        for call in all_calls:
            agent, customer, call_time = call.get('agent_number', ''), call.get('customer_number', ''), call.get('start_time', '')
            if customer and agent not in ['Call Missed', 'NA', '', None]:
                attended_calls[customer] = max(call_time, attended_calls.get(customer, ''))

        for call in all_calls:
            agent, customer, call_time = call.get('agent_number', ''), call.get('customer_number', ''), call.get('start_time', '')
            if customer and agent in ['Call Missed', 'NA']:
                if call_time > attended_calls.get(customer, ''):
                    unattended_missed_calls.append({
                        "phone": customer.lstrip('+'),
                        "time": call_time
                    })

        return unattended_missed_calls

    except Exception as e:
        print(f"Error fetching phone numbers: {e}")
        return []


# --------------------------- ZOHO HELPERS --------------------------- #
def search_records(module, phone_number, access_token):
    """Search Zoho CRM for records by phone number."""
    url = f"{CRM_API_URL}/{module}/search?phone={phone_number}"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    try:
        response = session.get(url, headers=headers, timeout=(5, 30))
        response.raise_for_status()
        return response.json().get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"Error in {module} search (phone: {phone_number}): {e}")
        return []


def get_owner_name(record):
    """Extract owner name based on record type and stage."""
    deal_exists = record.get("Deal_Name") is not None
    owner_name = record.get("Owner", {}).get("name", "Unknown")

    if not deal_exists:
        return f"Lead Owner: {owner_name}"

    stage = (record.get("Stage") or "").strip()
    if stage == "Consultation Done":
        return f"Deal Owner: {owner_name}"
    elif stage == "Plan Shipped":
        return "Delivery related - No Owner"
    elif stage in ["Plan Delivered", "Plan  Delivered"]:
        raaz_mitra = record.get("Raaz_Mitra")
        return f"Raaz Mitra: {raaz_mitra}" if raaz_mitra else f"Raaz Mitra Missing (Deal Owner: {owner_name})"

    return f"Deal Owner: {owner_name}"


# --------------------------- STREAMING RESPONSE --------------------------- #
def fetch_zoho_data_stream(request):
    """SSE streaming response with Zoho CRM data and Knowlarity numbers."""
    def stream():
        try:
            yield f"event: heartbeat\ndata: {json.dumps({'message': 'Connected'})}\n\n"

            access_token = get_access_token()
            if not access_token:
                yield f"data: {json.dumps({'error': 'Cannot generate access token'})}\n\n"
                return

            phone_numbers = fetch_phone_numbers()
            if not phone_numbers:
                yield f"data: {json.dumps({'error': 'No phone numbers retrieved'})}\n\n"
                return

            # Process in batches for speed
            chunk_size = 15
            for i in range(0, len(phone_numbers), chunk_size):
                batch = phone_numbers[i:i + chunk_size]
                batch_result = []

                for entry in batch:
                    phone, entry_time = entry["phone"], entry["time"]

                    # ✅ Convert entry_time into IST Date + Time
                    try:
                        entry_dt = datetime.datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                        india_tz = pytz.timezone('Asia/Kolkata')
                        entry_dt = entry_dt.astimezone(india_tz)

                        mis_date = entry_dt.strftime("%Y-%m-%d")   # only date
                        mis_time = entry_dt.strftime("%H:%M:%S")   # only time
                    except Exception:
                        mis_date, mis_time = "N/A", entry_time

                    # ✅ Search Zoho records
                    leads = search_records("Leads", phone, access_token)
                    deals = search_records("Deals", phone, access_token)
                    all_records = leads + deals

                    if all_records:
                        latest_record = max(all_records, key=lambda x: x.get("Created_Time", "1970-01-01T00:00:00Z"))
                        owner = get_owner_name(latest_record)
                    else:
                        owner = None

                    # ✅ Final JSON result
                    batch_result.append({
                        "phone": phone,
                        "mis_date": mis_date,
                        "mis_time": mis_time,
                        "owner": owner
                    })

                yield f"data: {json.dumps(batch_result)}\n\n"
                time.sleep(0.05)  # lighter delay (faster)

            yield f"event: end\ndata: {json.dumps({'message': 'Stream finished'})}\n\n"

        except Exception as e:
            print(f"Unexpected error in stream: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    response = StreamingHttpResponse(stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['Access-Control-Allow-Origin'] = '*'
    return response
