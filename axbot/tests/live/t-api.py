import time, json, urllib.request
time.sleep(20)  # E2E driver: let the bot restart win the race (skill: ax-substrate-ops)
with urllib.request.urlopen("https://api-pl.easypack24.net/v4/machines/SAN01BAPP", timeout=20) as r:
    d = json.load(r)
md = "Paczkomat %s: %s" % (d.get("name", "?"), d.get("status", "?"))
results = {"status": d.get("status"), "address": d.get("address", {}).get("line1", "")}
