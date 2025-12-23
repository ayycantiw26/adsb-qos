from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time, sqlite3, os

APP_KEY = os.getenv("APP_KEY", "ayucantiw")  # set di cloud nanti

DB_PATH = "adsb.db"
app = FastAPI(title="ADSB Cloud QoS", version="1.0")

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts_send REAL,
      ts_recv REAL,
      aircraft_count INTEGER,
      msg_seq INTEGER
    )
    """)
    return conn

conn = init_db()

class ADSBPayload(BaseModel):
    timestamp_send: float | None = None
    aircraft_count: int | None = None
    msg_seq: int | None = None

def auth(x_api_key: str | None):
    if x_api_key != APP_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/api/adsb")
def receive_adsb(payload: ADSBPayload, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    ts_recv = time.time()
    conn.execute(
        "INSERT INTO logs (ts_send, ts_recv, aircraft_count, msg_seq) VALUES (?,?,?,?)",
        (payload.timestamp_send, ts_recv, payload.aircraft_count, payload.msg_seq)
    )
    conn.commit()
    return {"status": "success"}

@app.get("/api/stats")
def stats(x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    rows = conn.execute(
        "SELECT ts_send, ts_recv, aircraft_count, msg_seq FROM logs ORDER BY id DESC LIMIT 300"
    ).fetchall()
    rows = list(reversed(rows))
    if len(rows) < 2:
        return {"status": "need_more_data"}

    delays, seqs = [], []
    t_first, t_last = rows[0][1], rows[-1][1]

    for ts_send, ts_recv, aircraft_count, msg_seq in rows:
        if ts_send is not None and ts_recv is not None:
            delays.append(ts_recv - ts_send)
        if msg_seq is not None:
            seqs.append(msg_seq)

    avg_delay = sum(delays)/len(delays) if delays else None
    max_delay = max(delays) if delays else None

    duration = max(1e-6, (t_last - t_first))
    msg_rate = len(rows) / duration

    loss = None
    if len(seqs) >= 2:
        expected = (max(seqs) - min(seqs) + 1)
        received = len(seqs)
        loss = max(0, expected - received)

    return {
        "status": "ok",
        "samples": len(rows),
        "avg_delay_sec": avg_delay,
        "max_delay_sec": max_delay,
        "msg_rate_per_sec": msg_rate,
        "estimated_loss_count": loss
    }

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""
<!doctype html><html><head><meta charset="utf-8"/><title>ADSB QoS</title></head>
<body style="font-family:Arial;margin:24px">
<h2>ADSB QoS Dashboard</h2>
<p>Masukkan API key (APP_KEY)</p>
<input id="k" style="padding:8px;width:280px" placeholder="API Key"/>
<button onclick="loadAll()" style="padding:8px 12px">Refresh</button>
<pre id="out">-</pre>
<script>
async function loadAll(){
  const key = document.getElementById("k").value;
  const r = await fetch("/api/stats",{headers:{"x-api-key":key}});
  document.getElementById("out").textContent = JSON.stringify(await r.json(),null,2);
}
</script></body></html>
""")
