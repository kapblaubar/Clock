# Clock Pi Web App

This project now supports multiple display modes with a stable management backend.

## Modes

- `graphic`: the existing photo/GIF clock screen
- `world-daylight`: a flat world map with daylight shading in UTC
- `airport-board`: a departures-style board showing up to 6 destinations using `City | Distance | Local Time`
- `lichtzeitpegel`: a six-group 24-hour band clock showing `H h M m S s`

## Airport-board model

- One manual `homeLocation`
- Up to 6 selected destination cities from the bundled city list
- Optional custom saved places for locations not in the bundled list
- `country` is used in the portal to filter the city dropdown, not shown as a separate display column

## Backend

- `server.py` runs the management portal and photo APIs
- `clock_state.json` stores the active display mode and settings
- `cities.json` provides bundled destination cities

## Pi packages

```bash
sudo apt update
sudo apt install -y python3-flask python3-pygame python3-pil
```

## Native display startup

The attached screen runs `native_display.py` through `start-clock-browser.sh`.

## Portal

Open `http://<pi-ip>:8000/manage` from another device on Wi-Fi.
