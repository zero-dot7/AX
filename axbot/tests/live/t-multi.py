import time, json, urllib.request
time.sleep(20)  # E2E driver head start; TWO egress hosts -> 2 hostname rules + cidr
out = {}
with urllib.request.urlopen("https://api.open-meteo.com/v1/forecast?latitude=52.23&longitude=21.01&current=temperature_2m", timeout=20) as r:
    out["warsaw_temp"] = json.load(r)["current"]["temperature_2m"]
with urllib.request.urlopen("https://api-pl.easypack24.net/v4/machines/SAN01BAPP", timeout=20) as r:
    out["paczkomat"] = json.load(r).get("status")
md = "Warszawa %s C; paczkomat SAN01BAPP: %s" % (out["warsaw_temp"], out["paczkomat"])
results = out
