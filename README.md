# Clock

Photo-backed clock display and management app.

## Contents

- `server.py`: Flask management portal and photo/state API
- `manage.html` / `manage.js`: management UI
- `index.html` / `app.js`: display UI
- `native_display.py`: local native fullscreen display
- `display.py`: GTK/WebKit fullscreen browser wrapper

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install Flask pygame Pillow
python server.py
```

Open `http://localhost:8000/manage`.

## Raspberry Pi notes

See `README-pi.md` for Pi-specific setup details.
