#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU STUDIO — kontrolna tabla za AMD grafičku (amdgpu), samo čitanje.
Čist Python (standardna biblioteka), ništa se ne instalira.

Pokretanje:  python3 ~/Desktop/gpu-studio/gpu-studio.py
Otvaranje:   http://localhost:8767
"""
import os, glob, json, time, threading, collections
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("GPU_STUDIO_PORT", "8767"))

def find_card():
    for dev in sorted(glob.glob("/sys/class/drm/card[0-9]*/device")):
        try:
            if os.path.basename(os.readlink(dev + "/driver")) == "amdgpu":
                return dev
        except OSError:
            pass
    return None

DEV = find_card()
HWMON = (glob.glob(DEV + "/hwmon/hwmon*") or [None])[0] if DEV else None

def rd(path, conv=int, default=None):
    try:
        with open(path) as f:
            return conv(f.read().strip())
    except Exception:
        return default

def hw(name, conv=int):
    return rd(f"{HWMON}/{name}", conv) if HWMON else None

def levels(name):
    try:
        out = []
        for line in open(f"{DEV}/{name}"):
            mhz = int(line.split(":")[1].strip().rstrip("*").strip().lower().replace("mhz", ""))
            out.append(mhz)
        return out
    except Exception:
        return []

def card_info():
    if not DEV:
        return {}
    name, maker = "AMD Radeon", ""
    try:
        import subprocess
        slot = os.path.basename(os.path.realpath(DEV))
        out = subprocess.run(["lspci", "-vmm", "-s", slot], capture_output=True, text=True).stdout
        f = dict(l.split(":\t", 1) for l in out.splitlines() if ":\t" in l)
        maker = f.get("SVendor", "").replace("Pine Group Inc.", "").replace("Inc.", "").strip()
        name = f.get("SDevice") or name
        if "Radeon" not in name:
            name = "Radeon " + name
    except Exception:
        pass
    return {
        "name": name, "maker": maker,
        "vbios": rd(DEV + "/vbios_version", str, "?"),
        "pcie": f'{rd(DEV + "/current_link_speed", str, "?").replace(" PCIe", "")} x{rd(DEV + "/current_link_width", str, "?")}',
        "vram_total": rd(DEV + "/mem_info_vram_total", int, 0),
        "sclk_levels": levels("pp_dpm_sclk"),
        "mclk_levels": levels("pp_dpm_mclk"),
        "temp_crit": (hw("temp1_crit") or 94000) / 1000,
        "power_cap": (hw("power1_cap") or 0) / 1e6,
        "fan_max": hw("fan1_max") or 3500,
        "kernel": os.uname().release,
    }

INFO = card_info()
START = time.time()

def sample():
    if not DEV:
        return {"ok": False}
    p = hw("power1_average") or hw("power1_input")
    pwm = hw("pwm1")
    return {
        "ok": True, "t": time.time(),
        "load": rd(DEV + "/gpu_busy_percent"),
        "temp": (hw("temp1_input") or 0) / 1000,
        "power": (p or 0) / 1e6,
        "fan_rpm": hw("fan1_input"),
        "fan_pct": round(pwm * 100 / 255) if pwm is not None else None,
        "sclk": (hw("freq1_input") or 0) / 1e6,
        "mclk": (hw("freq2_input") or 0) / 1e6,
        "volt": (hw("in0_input") or 0) / 1000,
        "vram_used": rd(DEV + "/mem_info_vram_used", int, 0),
        "uptime": time.time() - START,
        "sys_uptime": rd("/proc/uptime", lambda x: float(x.split()[0]), 0),
    }

# istorija: 1 uzorak u sekundi, 15 minuta
HIST = collections.deque(maxlen=900)
LAST = {"s": sample()}
PEAK = {"temp": 0, "power": 0, "load": 0}

def loop():
    n = 0
    while True:
        s = sample()
        LAST["s"] = s
        if s.get("ok"):
            for k in PEAK:
                PEAK[k] = max(PEAK[k], s[k] or 0)
            n += 1
            if n % 4 == 0:
                HIST.append([round(s["t"], 1), s["temp"], s["load"], round(s["power"], 1)])
        time.sleep(0.25)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            self.send(200, open(os.path.join(HERE, "index.html"), "rb").read(), "text/html; charset=utf-8")
        elif p == "/api/info":
            self.send(200, json.dumps(INFO))
        elif p == "/api/status":
            s = dict(LAST["s"]); s["peak"] = PEAK
            self.send(200, json.dumps(s))
        elif p == "/api/history":
            self.send(200, json.dumps(list(HIST)))
        elif p == "/api/quit":
            self.send(200, '{"ok":true}')
            threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)), daemon=True).start()
        elif p == "/icon.svg":
            self.send(200, open(os.path.join(HERE, "gpu-studio.svg"), "rb").read(), "image/svg+xml")
        else:
            self.send(404, '{"error":"nema"}')

if __name__ == "__main__":
    if not DEV:
        print("Nije pronađena AMD (amdgpu) grafička.")
    threading.Thread(target=loop, daemon=True).start()
    print(f"GPU Studio: http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
