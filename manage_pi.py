import argparse
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "clock_config.json"
ASSET_DIR = BASE_DIR / "assets"

DEFAULT_CONFIG = {
    "bg": "assets/bg1.webp",
    "fx": "",
    "clockImage": "",
    "mode24": True,
    "analog": True,
    "fullscreen": True,
    "windowWidth": 1280,
    "windowHeight": 720,
    "fps": 30,
}

IMAGE_EXTENSIONS = {".gif", ".webp", ".png", ".jpg", ".jpeg", ".avif", ".svg"}


def load_config():
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}

    config = DEFAULT_CONFIG.copy()
    config.update(data)
    return config


def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def list_assets():
    if not ASSET_DIR.exists():
        return []
    return sorted(
        str(path.relative_to(BASE_DIR))
        for path in ASSET_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def parse_bool(value):
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def main():
    parser = argparse.ArgumentParser(description="Manage Clock Pi configuration")
    parser.add_argument("--show", action="store_true", help="Print the current config")
    parser.add_argument("--list-assets", action="store_true", help="List image assets")
    parser.add_argument("--bg", help="Background image path relative to project root")
    parser.add_argument("--fx", help="Overlay image path relative to project root, or empty string")
    parser.add_argument("--clock-image", help="Clock image path relative to project root, or empty string")
    parser.add_argument("--mode24", type=parse_bool, help="Set 24-hour mode on or off")
    parser.add_argument("--analog", type=parse_bool, help="Set analog clock on or off")
    parser.add_argument("--fullscreen", type=parse_bool, help="Set fullscreen on or off")
    parser.add_argument("--window-width", type=int, help="Window width when not fullscreen")
    parser.add_argument("--window-height", type=int, help="Window height when not fullscreen")
    parser.add_argument("--fps", type=int, help="Target frames per second")
    args = parser.parse_args()

    config = load_config()
    updated = False

    if args.bg is not None:
        config["bg"] = args.bg
        updated = True
    if args.fx is not None:
        config["fx"] = args.fx
        updated = True
    if args.clock_image is not None:
        config["clockImage"] = args.clock_image
        updated = True
    if args.mode24 is not None:
        config["mode24"] = args.mode24
        updated = True
    if args.analog is not None:
        config["analog"] = args.analog
        updated = True
    if args.fullscreen is not None:
        config["fullscreen"] = args.fullscreen
        updated = True
    if args.window_width is not None:
        config["windowWidth"] = args.window_width
        updated = True
    if args.window_height is not None:
        config["windowHeight"] = args.window_height
        updated = True
    if args.fps is not None:
        config["fps"] = args.fps
        updated = True

    if updated:
        save_config(config)

    if args.list_assets:
        for asset in list_assets():
            print(asset)

    if args.show or not any(vars(args).values()):
        print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
