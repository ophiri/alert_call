"""
Fetch and display today's alerts from Pikud HaOref.
"""
import requests
import json

headers = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Current active alerts
print("=== התרעות פעילות כרגע ===")
try:
    r = requests.get("https://www.oref.org.il/WarningMessages/alert/alerts.json", headers=headers, timeout=5)
    if r.text.strip():
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    else:
        print("  אין התרעות פעילות כרגע ✅")
except Exception as e:
    print(f"  Error: {e}")

print()

# Today's history
print("=== היסטוריית התרעות היום ===")
try:
    r = requests.get("https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json", headers=headers, timeout=10)
    if r.text.strip():
        alerts = r.json()
        if isinstance(alerts, list) and len(alerts) > 0:
            print(f"  סה\"כ {len(alerts)} התרעות היום:\n")
            for a in alerts[:40]:
                date = a.get("alertDate", "")
                data = a.get("data", "")
                cat = a.get("category_desc", "")
                print(f"  🕐 {date} | {cat} | {data}")
            if len(alerts) > 40:
                print(f"\n  ... ועוד {len(alerts) - 40} התרעות")
        else:
            print("  אין התרעות היום")
    else:
        print("  אין היסטוריה")
except Exception as e:
    print(f"  Error: {e}")
