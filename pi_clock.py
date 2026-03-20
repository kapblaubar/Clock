import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pygame
from PIL import Image, ImageSequence, UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "clock_config.json"

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


def load_config():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}

    config = DEFAULT_CONFIG.copy()
    config.update(data)
    return config


def resolve_asset(path_value):
    if not path_value:
        return None
    asset_path = Path(path_value)
    if not asset_path.is_absolute():
        asset_path = BASE_DIR / asset_path
    return asset_path if asset_path.exists() else None


def clamp_duration_ms(value):
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return 100
    return max(20, duration)


def pil_frame_to_surface(frame, target_size, fit_mode):
    image = frame.convert("RGBA")
    src_w, src_h = image.size
    dst_w, dst_h = target_size

    if src_w <= 0 or src_h <= 0:
        return pygame.Surface(target_size, pygame.SRCALPHA)

    scale = max(dst_w / src_w, dst_h / src_h) if fit_mode == "cover" else min(dst_w / src_w, dst_h / src_h)
    scaled_w = max(1, int(src_w * scale))
    scaled_h = max(1, int(src_h * scale))
    resized = image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
    surface = pygame.image.fromstring(resized.tobytes(), resized.size, resized.mode).convert_alpha()

    composed = pygame.Surface(target_size, pygame.SRCALPHA)
    offset = ((dst_w - scaled_w) // 2, (dst_h - scaled_h) // 2)
    composed.blit(surface, offset)
    return composed


@dataclass
class LayerAsset:
    frames: list
    durations_ms: list

    @classmethod
    def empty(cls, target_size):
        return cls([pygame.Surface(target_size, pygame.SRCALPHA)], [1000])

    @classmethod
    def from_path(cls, path_value, target_size, fit_mode):
        path = resolve_asset(path_value)
        if path is None:
            return cls.empty(target_size)

        try:
            with Image.open(path) as image:
                frames = []
                durations = []
                if getattr(image, "is_animated", False):
                    for frame in ImageSequence.Iterator(image):
                        frames.append(pil_frame_to_surface(frame, target_size, fit_mode))
                        durations.append(clamp_duration_ms(frame.info.get("duration", image.info.get("duration"))))
                else:
                    frames.append(pil_frame_to_surface(image, target_size, fit_mode))
                    durations.append(1000)
        except (UnidentifiedImageError, OSError):
            return cls.empty(target_size)

        return cls(frames or [pygame.Surface(target_size, pygame.SRCALPHA)], durations or [1000])


class LayerPlayer:
    def __init__(self, asset):
        self.asset = asset
        self.index = 0
        self.next_switch_ms = pygame.time.get_ticks() + self.asset.durations_ms[0]

    def current_frame(self):
        now = pygame.time.get_ticks()
        if len(self.asset.frames) > 1 and now >= self.next_switch_ms:
            self.index = (self.index + 1) % len(self.asset.frames)
            self.next_switch_ms = now + self.asset.durations_ms[self.index]
        return self.asset.frames[self.index]


def format_time(now, is_24_hour):
    return now.strftime("%H:%M:%S") if is_24_hour else now.strftime("%I:%M:%S %p").lstrip("0")


def draw_hand(screen, center, length, width, angle, color):
    cx, cy = center
    end_x = cx + math.sin(angle) * length
    end_y = cy - math.cos(angle) * length
    pygame.draw.line(screen, color, center, (end_x, end_y), width)


def draw_analog_clock(screen, now, width, height):
    cx = width // 2
    cy = height // 2
    radius = int(min(width, height) * 0.22)

    pygame.draw.circle(screen, (255, 255, 255), (cx, cy), radius, 4)

    for i in range(12):
        angle = (math.pi * 2 * i) / 12
        x1 = cx + math.sin(angle) * int(radius * 0.82)
        y1 = cy - math.cos(angle) * int(radius * 0.82)
        x2 = cx + math.sin(angle) * int(radius * 0.94)
        y2 = cy - math.cos(angle) * int(radius * 0.94)
        pygame.draw.line(screen, (235, 235, 235), (x1, y1), (x2, y2), 3)

    seconds = now.second + now.microsecond / 1_000_000
    minutes = now.minute + seconds / 60
    hours = (now.hour % 12) + minutes / 60

    draw_hand(screen, (cx, cy), radius * 0.5, 7, (math.pi * 2 * hours) / 12, (255, 255, 255))
    draw_hand(screen, (cx, cy), radius * 0.72, 5, (math.pi * 2 * minutes) / 60, (220, 220, 255))
    draw_hand(screen, (cx, cy), radius * 0.86, 2, (math.pi * 2 * seconds) / 60, (255, 120, 120))
    pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 7)


def default_runtime_dir():
    return f"/run/user/{os.getuid()}"


def init_display(config):
    if not os.environ.get("XDG_RUNTIME_DIR"):
        runtime_dir = default_runtime_dir()
        if Path(runtime_dir).exists():
            os.environ["XDG_RUNTIME_DIR"] = runtime_dir

    current_driver = os.environ.get("SDL_VIDEODRIVER")
    candidates = []
    if current_driver:
        candidates.append(current_driver)

    if os.environ.get("DISPLAY"):
        candidates.extend(["x11", "wayland"])

    candidates.extend(["kmsdrm", "fbcon"])

    errors = []
    seen = set()
    for driver in candidates:
        if driver in seen:
            continue
        seen.add(driver)

        os.environ["SDL_VIDEODRIVER"] = driver
        if driver == "fbcon" and Path("/dev/fb0").exists() and not os.environ.get("SDL_FBDEV"):
            os.environ["SDL_FBDEV"] = "/dev/fb0"

        try:
            pygame.display.quit()
            pygame.display.init()
            flags = pygame.FULLSCREEN if config.get("fullscreen", True) else 0
            size = (0, 0) if config.get("fullscreen", True) else (
                int(config.get("windowWidth", 1280)),
                int(config.get("windowHeight", 720)),
            )
            screen = pygame.display.set_mode(size, flags)
            return screen, driver
        except pygame.error as exc:
            errors.append(f"{driver}: {exc}")

    raise RuntimeError("Unable to initialize a video driver. Tried: " + "; ".join(errors))


def main():
    config = load_config()
    pygame.font.init()
    screen, driver = init_display(config)
    pygame.display.set_caption(f"Clock ({driver})")
    width, height = screen.get_size()
    fps = max(1, int(config.get("fps", 30)))

    bg_player = LayerPlayer(LayerAsset.from_path(config.get("bg"), (width, height), "cover"))
    clock_player = LayerPlayer(LayerAsset.from_path(config.get("clockImage"), (width, height), "contain"))
    fx_player = LayerPlayer(LayerAsset.from_path(config.get("fx"), (width, height), "contain"))

    font_size = max(36, width // 24)
    font = pygame.font.SysFont("Arial", font_size)
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return 0
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return 0

        screen.fill((0, 0, 0))
        screen.blit(bg_player.current_frame(), (0, 0))
        screen.blit(clock_player.current_frame(), (0, 0))
        screen.blit(fx_player.current_frame(), (0, 0))

        now = datetime.now()
        if config.get("analog", True):
            draw_analog_clock(screen, now, width, height)

        text = format_time(now, config.get("mode24", True))
        text_surface = font.render(text, True, (255, 255, 255))
        shadow_surface = font.render(text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=(width // 2, int(height * 0.82)))
        screen.blit(shadow_surface, text_rect.move(3, 3))
        screen.blit(text_surface, text_rect)

        pygame.display.flip()
        clock.tick(fps)


if __name__ == "__main__":
    sys.exit(main())
