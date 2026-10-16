# SPE Expert PA Monitoring Server

Asynchroner Steuerungs- und Telemetrie-Server für SPE Expert Endstufen (2K-FA, 1.5K-FA, 1.3K-FA).
Kompatibel mit Raspberry Pi 4 / Linux (`ser2net`) und Windows.

---

## 1. Übersicht

* **Anbindung:** Verbindet sich per TCP mit `ser2net` (Standard: `192.168.84.220:22000`), welcher den seriellen Port `/dev/ttyUSB0` (115200 8N1) bereitstellt.
* **Multiplexing:** Ermöglicht mehreren Clients (Web-GUI, Windows-App, Logging-Tools) den gleichzeitigen Zugriff auf die Endstufe, ohne den seriellen Datenstrom zu stören.
* **REST-API & WebSocket:** Liefert strukturierte Telemetrie (Watt, SWR, Volt, Ampere, Temperaturen, Status, Alarme) in Echtzeit und nimmt Tastenbefehle entgegen.
* **Integrierter Hardware-Simulator:** Erlaubt vollständiges Offline-Entwickeln und Testen ohne physische Endstufe.

---

## 2. Installation

```bash
# Virtuelle Umgebung erstellen
python3 -m venv .venv
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r <(echo "fastapi uvicorn[standard] pydantic pytest websockets httpx")
```

---

## 3. Starten des Servers

### A. Im Produktivbetrieb (Verbindung zum Raspberry Pi mit ser2net)
```bash
python run_server.py --pa-host 192.168.84.220 --pa-port 22000 --port 8000
```

### B. Im Testmodus (mit lokalem PA-Simulator)
```bash
python run_server.py --simulator --port 8000
```
Der integrierte Simulator spiegelt das Verhalten einer echten 2K-FA (inklusive Wechsel zwischen STANDBY/OPERATE, Leistungsstufen LOW/MID/MAX, Bandwechsel und SWR/Leistungsberechnung).

### C. Standalone Simulator
```bash
python run_simulator.py --port 22000
```

---

## 4. API Endpunkte

* **Interaktive Swagger-Dokumentation:** `http://localhost:8000/docs`
* **Health Check:** `GET /api/health`
* **Verbindungsstatus:** `GET /api/connection`
* **Aktuelle Telemetrie:** `GET /api/status`
* **Befehl senden:** `POST /api/command/{name}`
  * Unterstützte Befehle: `operate`, `power`, `input`, `band_plus`, `band_minus`, `ant`, `tune`, `l_plus`, `l_minus`, `c_plus`, `c_minus`, `display`, `cat`, `left`, `right`, `set`, `backlight_on`, `backlight_off`, `switch_off`
* **Rohbefehl senden:** `POST /api/command/raw/{hex_byte}` (z. B. `0x0D`)
* **Echtzeit-WebSocket:** `ws://localhost:8000/ws/telemetry`

---

## 5. Tests ausführen

```bash
pytest -v
```
Führt alle 10 automatisierten Unit- und Integrationstests aus (Codec, Checksumme, Parser, Simulator, FastAPI REST & WebSocket).
