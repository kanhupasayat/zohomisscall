# import os
# import json
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

# ACCOUNTS_URL = "https://accounts.zoho.in/oauth/v2/token"
# CRM_URL = "https://www.zohoapis.in/crm/v2/coql"

# ACCESS_TOKEN = None


# def get_access_token():
#     global ACCESS_TOKEN
#     data = {
#         "refresh_token": REFRESH_TOKEN,
#         "client_id": CLIENT_ID,
#         "client_secret": CLIENT_SECRET,
#         "grant_type": "refresh_token"
#     }
#     resp = requests.post(ACCOUNTS_URL, data=data)
#     if resp.status_code != 200:
#         print("Failed to get access token:", resp.status_code, resp.text)
#         return None
#     ACCESS_TOKEN = resp.json().get("access_token")
#     return ACCESS_TOKEN


# def request_with_auto_retry(url, headers, payload=None):
#     global ACCESS_TOKEN
#     resp = requests.post(url, headers=headers, data=json.dumps(payload) if payload else None)
#     if resp.status_code == 401:
#         print("Token expired. Refreshing...")
#         ACCESS_TOKEN = get_access_token()
#         if not ACCESS_TOKEN:
#             return None
#         headers["Authorization"] = f"Zoho-oauthtoken {ACCESS_TOKEN}"
#         resp = requests.post(url, headers=headers, data=json.dumps(payload) if payload else None)
#     return resp


# # -------- MAIN ----------
# ACCESS_TOKEN = get_access_token()
# if not ACCESS_TOKEN:
#     exit("❌ Could not generate access token")

# headers = {
#     "Authorization": f"Zoho-oauthtoken {ACCESS_TOKEN}",
#     "Content-Type": "application/json"
# }

# phone_numbers = ["918160122490"]
# phone_list = ",".join([f"'{num}'" for num in phone_numbers])

# # ✅ Query with Created_Time also
# query = {
#     "select_query": f"""
#         select Deal_Name, Raaz_Mitra, Order_Status, Stage, Contact_Name, Owner, Created_Time
#         from Deals
#         where Phone in ({phone_list})
#         order by Created_Time desc
#         limit 1
#     """
# }

# resp = request_with_auto_retry(CRM_URL, headers, query)

# if resp and resp.status_code == 200:
#     data = resp.json()
#     print(json.dumps(data, indent=2))  # Debugging

#     if "data" in data:
#         record = data["data"][0]   # ✅ सिर्फ पहला (latest) record

#         Deal_Name = record.get("Deal_Name")
#         Stage = record.get("Stage")
#         Raaz_Mitra = record.get("Raaz_Mitra", {}).get("name") if isinstance(record.get("Raaz_Mitra"), dict) else record.get("Raaz_Mitra")
#         Contact_Name = record.get("Contact_Name", {}).get("name") if isinstance(record.get("Contact_Name"), dict) else None
#         Owner = record.get("Owner", {}).get("id") if isinstance(record.get("Owner"), dict) else None
#         Created_Time = record.get("Created_Time")

#         print(f"✅ Latest Deal: {Deal_Name}, Contact: {Contact_Name}, Stage: {Stage}, Owner: {Owner}, Raaz_Mitra: {Raaz_Mitra}, Created: {Created_Time}")
#     else:
#         print("No deals found for this number.")

# else:
#     print("Error fetching deals:", resp.status_code if resp else "No response")






import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

ACCOUNTS_URL = "https://accounts.zoho.in/oauth/v2/token"
CRM_URL = "https://www.zohoapis.in/crm/v2/coql"

ACCESS_TOKEN = None

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
        print("Failed to get access token:", resp.status_code, resp.text)
        return None
    ACCESS_TOKEN = resp.json().get("access_token")
    return ACCESS_TOKEN

def request_with_auto_retry(url, headers, payload=None):
    global ACCESS_TOKEN
    resp = requests.post(url, headers=headers, data=json.dumps(payload) if payload else None)
    if resp.status_code == 401:
        print("Token expired. Refreshing...")
        ACCESS_TOKEN = get_access_token()
        if not ACCESS_TOKEN:
            return None
        headers["Authorization"] = f"Zoho-oauthtoken {ACCESS_TOKEN}"
        resp = requests.post(url, headers=headers, data=json.dumps(payload) if payload else None)
    return resp


phone_numbers = [
    "917294182699","917524888388","919937405129","919891237251","919450321534","919873914451","918923469897","918530741577","918081884299","918160122490","918269970026"
]
phone_list = ",".join([f"'{num}'" for num in phone_numbers])


def check_lead_or_deal(phone_list):
    headers = {
        "Authorization": f"Zoho-oauthtoken {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    found_number = {}           # केवल Leads के लिए
    unknown_number = []
    plan_slipped_numbers = []
    Consultation_Done = {}
    plan_delivered_numbers = {}





    # ---------- Check in Leads ----------
    query = {
        "select_query": f"""
            select Full_Name, Owner, Phone
            from Leads
            where Phone in ({phone_list})
        """
    }

    resp_lead = request_with_auto_retry(CRM_URL, headers, query)
    leads_found = []
    if resp_lead and resp_lead.status_code == 200:
        data = resp_lead.json()
        if data.get("data"):
            for rec in data["data"]:
                phone = rec.get("Phone")
                leads_found.append(phone)
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
                    "570692000064235701": "Alam Uddin"
                }.get(owner_id, f"Unknown ({owner_id})")

                found_number[phone] = {"name": name, "owner": owner_name}

    # ---------- Check in Deals (Only for numbers not in Leads) ----------
    remaining_numbers = [num for num in phone_numbers if num not in leads_found]

    if remaining_numbers:
        phone_list_remaining = ",".join([f"'{num}'" for num in remaining_numbers])
        query = {
            "select_query": f"""
            select Deal_Name, Stage, Phone ,Raaz_Mitra
            from Deals
            where Phone in ({phone_list_remaining})
            order by Created_Time desc
        """
        }

        resp_deal = request_with_auto_retry(CRM_URL, headers, query)
        deals_found = []
        if resp_deal and resp_deal.status_code == 200:
            data = resp_deal.json()
            if data.get("data"):
                for rec in data["data"]:
                    phone = rec.get("Phone")
                    stage = rec.get("Stage")
                    print({"phone": rec.get("Phone"), "owner": rec.get("id"),"stage":rec.get("Stage"),"Raaz_Mitra": rec.get("Raaz_Mitra")})
                    if stage == "Plan Shipped":
                        plan_slipped_numbers.append(phone)

                    elif stage == "Consultation Done":
                        if rec.get("id")=="570692000075910103":
                            Consultation_Done[phone] ="Naresh Prajapati"
                        elif rec.get("id")=="570692000075935263":
                            Consultation_Done[phone] ="Himanshu Goswami"
                            
                       

                    elif stage == "Plan  Delivered":
                        raaz_mitra = rec.get("Raaz_Mitra") or "None"   # agar Raaz_Mitra empty/missing hai to "None" use karo

                            # Agar pehle se list bani hai to usme append karo, warna new list banao
                        if raaz_mitra not in plan_delivered_numbers:
                            plan_delivered_numbers[raaz_mitra] = []
                        elif "None" not in plan_delivered_numbers:
                            plan_delivered_numbers["None"] = []

                        plan_delivered_numbers[raaz_mitra].append(phone)


                        # print({"phone": rec.get("Phone"), "owner": rec.get("id"),"stage":rec.get("Stage"),"Raaz_Mitra": rec.get("Raaz_Mitra")})

                                        # Remaining jo na leads me na deals me mile
        for num in remaining_numbers:
            if num not in deals_found and num not in plan_slipped_numbers:
                unknown_number.append(num)

    # ---------- Print result ----------
    print("✅ Found Numbers (Leads only):")
    for phone, val in found_number.items() :
        print(f"{phone} - {val['name']} - {val['owner']}")

    print("\n⚠️ Plan Slipped Numbers (from Deals only):")
    for num in plan_slipped_numbers:
        print(num)

    print("\n❌ Unknown Numbers:")
    for num in unknown_number:
        print(num)
    print(Consultation_Done)
    print("\n✅ Plan Delivered Numbers:", plan_delivered_numbers)

# -------- MAIN ----------
ACCESS_TOKEN = get_access_token()
if not ACCESS_TOKEN:
    exit("❌ Could not generate access token")

check_lead_or_deal(phone_list)


