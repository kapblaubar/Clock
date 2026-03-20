#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pygame
from PIL import Image, ImageSequence, UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "clock_state.json"
CITIES_PATH = BASE_DIR / "cities.json"
WORLD_MAP_PATH = BASE_DIR / "assets" / "tz-map-1518922800.png"
DEFAULT_STATE = {
    "displayMode": "graphic",
    "defaultPhoto": "assets/bg1.webp",
    "showAnalog": True,
    "mode24": True,
    "rotation": "portrait",
    "airportDestinations": ["nyc-us"],
    "homeLocation": None,
    "customPlaces": [],
}
ALLOWED_EXTENSIONS = {".gif", ".webp", ".png", ".jpg", ".jpeg", ".avif"}
STATE_POLL_MS = 3000
IDLE_FPS = 4
WORLD_POLL_FPS = 2


@dataclass
class MediaAsset:
    frames: list[pygame.Surface]
    durations_ms: list[int]

    @classmethod
    def empty(cls, logical_size: tuple[int, int]) -> "MediaAsset":
        return cls([pygame.Surface(logical_size).convert()], [1000])


class MediaPlayer:
    def __init__(self, asset: MediaAsset) -> None:
        self.asset = asset
        self.index = 0
        self.current = self.asset.frames[0]
        self.next_switch_ms = pygame.time.get_ticks() + self.asset.durations_ms[0]

    def update(self, now: int) -> bool:
        if len(self.asset.frames) > 1 and now >= self.next_switch_ms:
            self.index = (self.index + 1) % len(self.asset.frames)
            self.current = self.asset.frames[self.index]
            self.next_switch_ms = now + self.asset.durations_ms[self.index]
            return True
        return False

    def frame(self) -> pygame.Surface:
        return self.current


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def load_state() -> dict:
    if not STATE_PATH.exists():
        STATE_PATH.write_text(json.dumps(DEFAULT_STATE, indent=2), encoding="utf-8")
        return DEFAULT_STATE.copy()
    state = DEFAULT_STATE.copy()
    state.update(load_json(STATE_PATH, {}))
    return state


def load_cities() -> list[dict]:
    return load_json(CITIES_PATH, [])


def city_lookup() -> dict[str, dict]:
    return {city["id"]: city for city in load_cities()}


def resolve_asset(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    if not candidate.exists() or not candidate.is_file():
        return None
    if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None
    return candidate


def clamp_duration(value) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return 120
    return max(80, duration)


def fit_cover(image: Image.Image, logical_size: tuple[int, int]) -> pygame.Surface:
    src_w, src_h = image.size
    dst_w, dst_h = logical_size
    if src_w <= 0 or src_h <= 0:
        return pygame.Surface(logical_size).convert()
    scale = max(dst_w / src_w, dst_h / src_h)
    scaled = image.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))), Image.Resampling.LANCZOS).convert("RGB")
    surface = pygame.image.fromstring(scaled.tobytes(), scaled.size, scaled.mode).convert()
    composed = pygame.Surface(logical_size).convert()
    offset = ((dst_w - scaled.width) // 2, (dst_h - scaled.height) // 2)
    composed.blit(surface, offset)
    return composed


def scale_contain(image: Image.Image, bounds: tuple[int, int]) -> tuple[pygame.Surface, pygame.Rect]:
    src_w, src_h = image.size
    dst_w, dst_h = bounds
    scale = min(dst_w / src_w, dst_h / src_h)
    scaled_w = max(1, int(src_w * scale))
    scaled_h = max(1, int(src_h * scale))
    scaled = image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS).convert("RGB")
    surface = pygame.image.fromstring(scaled.tobytes(), scaled.size, scaled.mode).convert()
    rect = surface.get_rect()
    return surface, rect


def load_media(path: Path | None, logical_size: tuple[int, int]) -> MediaAsset:
    if path is None:
        return MediaAsset.empty(logical_size)
    try:
        with Image.open(path) as image:
            frames = []
            durations = []
            if getattr(image, "is_animated", False):
                for index, frame in enumerate(ImageSequence.Iterator(image)):
                    if index >= 24:
                        break
                    frames.append(fit_cover(frame.convert("RGB"), logical_size))
                    durations.append(clamp_duration(frame.info.get("duration", image.info.get("duration"))))
                if not frames:
                    frames.append(fit_cover(image.convert("RGB"), logical_size))
                    durations.append(1000)
            else:
                frames.append(fit_cover(image.convert("RGB"), logical_size))
                durations.append(1000)
    except (UnidentifiedImageError, OSError):
        return MediaAsset.empty(logical_size)
    return MediaAsset(frames or [pygame.Surface(logical_size).convert()], durations or [1000])


def format_time(now: datetime, mode24: bool) -> str:
    return now.strftime("%H:%M:%S") if mode24 else now.strftime("%I:%M:%S %p").lstrip("0")


def draw_hand(surface: pygame.Surface, center: tuple[float, float], length: float, width: int, angle: float, color: tuple[int, int, int]) -> None:
    cx, cy = center
    end_x = cx + math.sin(angle) * length
    end_y = cy - math.cos(angle) * length
    pygame.draw.line(surface, color, center, (end_x, end_y), width)


def draw_analog(surface: pygame.Surface, now: datetime) -> None:
    width, height = surface.get_size()
    cx = width / 2
    cy = height * 0.39
    radius = min(width, height) * 0.22
    pygame.draw.circle(surface, (248, 244, 237), (int(cx), int(cy)), int(radius), 4)
    for i in range(12):
        angle = (math.pi * 2 * i) / 12
        x1 = cx + math.sin(angle) * radius * 0.8
        y1 = cy - math.cos(angle) * radius * 0.8
        x2 = cx + math.sin(angle) * radius * 0.94
        y2 = cy - math.cos(angle) * radius * 0.94
        pygame.draw.line(surface, (255, 255, 255), (x1, y1), (x2, y2), 3)
    seconds = now.second
    minutes = now.minute + seconds / 60
    hours = (now.hour % 12) + minutes / 60
    draw_hand(surface, (cx, cy), radius * 0.48, 8, (math.pi * 2 * hours) / 12, (255, 255, 255))
    draw_hand(surface, (cx, cy), radius * 0.70, 5, (math.pi * 2 * minutes) / 60, (236, 236, 248))
    draw_hand(surface, (cx, cy), radius * 0.84, 2, (math.pi * 2 * seconds) / 60, (255, 132, 122))
    pygame.draw.circle(surface, (255, 255, 255), (int(cx), int(cy)), 6)


def initialize_display() -> pygame.Surface:
    os.environ.setdefault("DISPLAY", ":0")
    pygame.display.init()
    return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)


def compute_layout(screen_size: tuple[int, int], rotation: str, display_mode: str) -> tuple[tuple[int, int], bool]:
    screen_w, screen_h = screen_size
    rotate = rotation == "portrait" and display_mode == "graphic" and screen_w > screen_h
    if rotate:
        return (screen_h, screen_w), True
    return (screen_w, screen_h), False


def draw_graphic_mode(surface: pygame.Surface, state: dict, media: MediaPlayer, now: datetime, font: pygame.font.Font) -> None:
    logical_size = surface.get_size()
    surface.blit(media.frame(), (0, 0))
    if state.get("showAnalog", True):
        draw_analog(surface, now)
    time_text = format_time(now, state.get("mode24", True))
    text = font.render(time_text, True, (246, 241, 232))
    shadow = font.render(time_text, True, (0, 0, 0))
    text_rect = text.get_rect(center=(logical_size[0] // 2, int(logical_size[1] * 0.9)))
    surface.blit(shadow, text_rect.move(3, 3))
    surface.blit(text, text_rect)


def solar_position(now_utc: datetime) -> tuple[float, float]:
    day = now_utc.timetuple().tm_yday
    hour = now_utc.hour + now_utc.minute / 60 + now_utc.second / 3600
    decl = math.radians(-23.44 * math.cos((2 * math.pi / 365) * (day + 10)))
    subsolar_lon = math.radians((12 - hour) * 15)
    return decl, subsolar_lon


def is_daylight(lat_rad: float, lon_rad: float, decl: float, subsolar_lon: float) -> bool:
    cos_zenith = math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.cos(lon_rad - subsolar_lon)
    return cos_zenith > 0


def load_world_map(bounds: tuple[int, int]) -> tuple[pygame.Surface | None, pygame.Rect | None]:
    if not WORLD_MAP_PATH.exists():
        return None, None
    try:
        with Image.open(WORLD_MAP_PATH) as image:
            surface, rect = scale_contain(image.convert("RGB"), bounds)
            return surface, rect
    except (UnidentifiedImageError, OSError):
        return None, None


def draw_world_daylight(surface: pygame.Surface, now: datetime, world_map_cache: tuple[pygame.Surface | None, pygame.Rect | None]) -> None:
    width, height = surface.get_size()
    surface.fill((7, 22, 41))
    map_frame = pygame.Rect(int(width * 0.04), int(height * 0.08), int(width * 0.92), int(height * 0.68))
    pygame.draw.rect(surface, (17, 47, 78), map_frame, border_radius=22)

    map_surface, map_rect = world_map_cache
    if map_surface is not None and map_rect is not None:
        placed = map_surface.get_rect(center=map_frame.center)
        surface.blit(map_surface, placed)
        active_rect = placed
    else:
        active_rect = map_frame
        pygame.draw.rect(surface, (30, 73, 112), active_rect, border_radius=18)

    daylight_overlay = pygame.Surface((active_rect.width, active_rect.height), pygame.SRCALPHA)
    night_color = (8, 13, 26, 132)
    now_utc = now.astimezone(timezone.utc)
    decl, subsolar_lon = solar_position(now_utc)
    step = 4
    for y in range(0, active_rect.height, step):
        lat = math.radians(90 - (y / active_rect.height) * 180)
        for x in range(0, active_rect.width, step):
            lon = math.radians((x / active_rect.width) * 360 - 180)
            if not is_daylight(lat, lon, decl, subsolar_lon):
                pygame.draw.rect(daylight_overlay, night_color, pygame.Rect(x, y, step, step))
    surface.blit(daylight_overlay, active_rect.topleft)

    title_font = pygame.font.SysFont("Arial", max(38, width // 20), bold=True)
    small_font = pygame.font.SysFont("Arial", max(22, width // 40))
    title = title_font.render("WORLD DAYLIGHT", True, (245, 240, 230))
    subtitle = small_font.render(now_utc.strftime("UTC %H:%M:%S  ·  Greenwich-referenced map"), True, (186, 204, 218))
    local_time = title_font.render(now.strftime("%H:%M:%S"), True, (245, 240, 230))
    surface.blit(title, (map_frame.left, int(height * 0.80)))
    surface.blit(subtitle, (map_frame.left, int(height * 0.88)))
    surface.blit(local_time, local_time.get_rect(right=map_frame.right, top=int(height * 0.82)))


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(a))


def draw_airport_board(surface: pygame.Surface, state: dict, now: datetime, cities: dict[str, dict]) -> None:
    width, height = surface.get_size()
    surface.fill((17, 14, 11))
    board = pygame.Rect(int(width * 0.06), int(height * 0.10), int(width * 0.88), int(height * 0.72))
    pygame.draw.rect(surface, (22, 19, 15), board, border_radius=20)
    pygame.draw.rect(surface, (83, 69, 53), board, 2, border_radius=20)

    header_font = pygame.font.SysFont("Courier New", max(26, width // 32), bold=True)
    row_font = pygame.font.SysFont("Courier New", max(22, width // 40), bold=True)
    local_font = pygame.font.SysFont("Courier New", max(42, width // 18), bold=True)

    destination_ids = state.get("airportDestinations") or []
    home = state.get("homeLocation") or None
    header = header_font.render("AIRPORT BOARD", True, (250, 228, 167))
    home_text = header_font.render(f"HOME  {home.get('city', 'NOT SET').upper()}" if home else "HOME  NOT SET", True, (196, 177, 139))
    surface.blit(header, (board.x + 18, board.y + 18))
    surface.blit(home_text, (board.right - home_text.get_width() - 18, board.y + 18))

    columns = [
        ("CITY", board.x + 26),
        ("DISTANCE", board.x + int(board.width * 0.48)),
        ("LOCAL TIME", board.x + int(board.width * 0.72)),
    ]
    column_y = board.y + 76
    for label, x in columns:
        heading = row_font.render(label, True, (195, 178, 143))
        surface.blit(heading, (x, column_y))

    row_y = column_y + 42
    row_h = max(48, height // 12)
    if not destination_ids:
        empty = row_font.render("NO DESTINATIONS SELECTED", True, (255, 240, 196))
        surface.blit(empty, (board.x + 26, row_y + 20))
    else:
        for destination_id in destination_ids[:6]:
            city = cities.get(destination_id)
            if not city:
                continue
            row_rect = pygame.Rect(board.x + 18, row_y, board.width - 36, row_h)
            pygame.draw.rect(surface, (34, 26, 21), row_rect, border_radius=8)
            pygame.draw.rect(surface, (60, 51, 44), row_rect, 1, border_radius=8)
            city_text = row_font.render(city["city"].upper(), True, (255, 240, 196))
            if home:
                distance_value = f"{haversine_miles(home['lat'], home['lon'], city['lat'], city['lon']):,.0f} MI"
            else:
                distance_value = "SET HOME"
            distance_text = row_font.render(distance_value, True, (255, 240, 196))
            local_time_text = row_font.render(datetime.now(ZoneInfo(city["timezone"])).strftime("%H:%M:%S"), True, (255, 240, 196))
            surface.blit(city_text, (board.x + 26, row_y + 12))
            surface.blit(distance_text, (board.x + int(board.width * 0.48), row_y + 12))
            surface.blit(local_time_text, (board.x + int(board.width * 0.72), row_y + 12))
            row_y += row_h + 10

    footer_label = header_font.render("PI LOCAL TIME", True, (196, 177, 139))
    footer_time = local_font.render(now.strftime("%H:%M:%S"), True, (255, 240, 196))
    surface.blit(footer_label, (board.x + 18, board.bottom + 20))
    surface.blit(footer_time, (board.x + 18, board.bottom + 56))


def main() -> int:
    pygame.init()
    pygame.font.init()
    screen = initialize_display()
    pygame.display.set_caption("Clock Display")
    clock = pygame.time.Clock()

    cities = city_lookup()
    state = load_state()
    logical_size, rotate_output = compute_layout(screen.get_size(), state.get("rotation", "portrait"), state.get("displayMode", "graphic"))
    work_surface = pygame.Surface(logical_size).convert()
    graphic_font = pygame.font.SysFont("Arial", max(32, logical_size[0] // 18))
    media = MediaPlayer(load_media(resolve_asset(state.get("defaultPhoto")), logical_size))
    world_map_cache = load_world_map((int(logical_size[0] * 0.92), int(logical_size[1] * 0.68)))

    state_signature = json.dumps(state, sort_keys=True)
    next_state_poll = 0
    last_second = -1
    needs_render = True

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 0
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return 0

        now_ms = pygame.time.get_ticks()
        if now_ms >= next_state_poll:
            next_state_poll = now_ms + STATE_POLL_MS
            latest_state = load_state()
            latest_signature = json.dumps(latest_state, sort_keys=True)
            if latest_signature != state_signature:
                state = latest_state
                state_signature = latest_signature
                logical_size, rotate_output = compute_layout(screen.get_size(), state.get("rotation", "portrait"), state.get("displayMode", "graphic"))
                work_surface = pygame.Surface(logical_size).convert()
                graphic_font = pygame.font.SysFont("Arial", max(32, logical_size[0] // 18))
                media = MediaPlayer(load_media(resolve_asset(state.get("defaultPhoto")), logical_size))
                world_map_cache = load_world_map((int(logical_size[0] * 0.92), int(logical_size[1] * 0.68)))
                cities = city_lookup()
                last_second = -1
                needs_render = True

        if state.get("displayMode") == "graphic" and media.update(now_ms):
            needs_render = True

        now = datetime.now()
        if now.second != last_second:
            last_second = now.second
            needs_render = True

        if needs_render:
            work_surface.fill((0, 0, 0))
            mode = state.get("displayMode", "graphic")
            if mode == "graphic":
                draw_graphic_mode(work_surface, state, media, now, graphic_font)
            elif mode == "world-daylight":
                draw_world_daylight(work_surface, now, world_map_cache)
            elif mode == "airport-board":
                draw_airport_board(work_surface, state, now, cities)

            screen.fill((0, 0, 0))
            if rotate_output:
                rotated = pygame.transform.rotate(work_surface, -90)
                rect = rotated.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                screen.blit(rotated, rect)
            else:
                screen.blit(work_surface, (0, 0))
            pygame.display.flip()
            needs_render = False

        fps = IDLE_FPS if state.get("displayMode") == "graphic" else WORLD_POLL_FPS
        clock.tick(fps)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
