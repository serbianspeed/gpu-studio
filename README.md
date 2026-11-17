# GPU Studio

Read-only live dashboard for an AMD RX 580 (amdgpu), styled like a Lada 2106 instrument cluster:
analog gauges (load, temperature, power, fan), small gauges (core/mem clock, voltage, VRAM),
warning lamps, a paper tachograph and an hour meter.

- `gpu-studio.py` — stdlib Python server on `127.0.0.1:8767`, reads amdgpu sysfs/hwmon
  (`/api/info`, `/api/status`, `/api/history`, `/api/quit`)
- `index.html` — the whole dashboard (1920×1080 stage, scaled to fit)
- `gpu-studio-app.sh` — starts the server, opens Chromium in app mode, stops the server on close
- `GPU Studio.desktop` — desktop launcher

Run: `./gpu-studio-app.sh` (or `python3 gpu-studio.py` and open http://localhost:8767).
