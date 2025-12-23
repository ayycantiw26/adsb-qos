import time, requests

# 1) URL aircraft.json dari Raspi (PiAware)
RASPI_AIRCRAFT_URL = "http://192.168.155.81/skyaware/data/aircraft.json"

# 2) API endpoint (lokal dulu, nanti ganti cloud)
SERVER_URL = "http://127.0.0.1:5000/api/adsb"
API_KEY = "ayucantiw"

seq = 0

while True:
    try:
        # ambil JSON realtime dari Raspi
        r = requests.get(RASPI_AIRCRAFT_URL, timeout=5)
        data = r.json()
        aircraft = data.get("aircraft", [])

        payload = {
            "timestamp_send": time.time(),
            "aircraft_count": len(aircraft),
            "msg_seq": seq
        }

        # kirim ke API
        p = requests.post(
            SERVER_URL,
            json=payload,
            headers={"x-api-key": API_KEY},
            timeout=5
        )

        print("sent", seq, "status", p.status_code, "aircraft", len(aircraft))
        seq += 1

    except Exception as e:
        print("error:", e)

    time.sleep(1)
