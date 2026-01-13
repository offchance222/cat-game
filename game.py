#!/usr/bin/env python3
"""
Space Dodger — Cat Attack (Pygame) — background image support

This is the full updated game.py that:
- Loads a background image named "background.png" from the project folder (and supports PyInstaller bundles).
- Draws the background with a translucent dark overlay for readability.
- Keeps all game features: cat enemies, enemy bullets, power-ups, boss, generated sounds, highscores.
"""

import pygame
import random
import math
import sys
import os
import json
import wave
import struct
from dataclasses import dataclass

# ----- Config -----
SCREEN_W = 480
SCREEN_H = 640
FPS = 60

PLAYER_SPEED = 320  # px/s
PLAYER_W = 36
PLAYER_H = 24
PLAYER_Y = SCREEN_H - 64
PLAYER_COOLDOWN = 0.22  # seconds between shots

BULLET_SPEED = 480
BULLET_W = 4
BULLET_H = 10

ENEMY_MIN_SPEED = 70
ENEMY_MAX_SPEED = 160
ENEMY_SPAWN_INTERVAL_START = 0.95
ENEMY_SPAWN_INTERVAL_MIN = 0.35

POWERUP_SPAWN_CHANCE = 0.04  # chance per spawn to drop a power-up
POWERUP_DURATION = 8.0  # seconds

BOSS_APPEAR_SCORE = 300  # score threshold to spawn boss

HIGHSCORE_FILE = "highscores.json"

# Sound filenames
SND_DIR = "snd"
SND_SHOOT = os.path.join(SND_DIR, "shoot.wav")
SND_EXPLODE = os.path.join(SND_DIR, "explode.wav")
SND_POWER = os.path.join(SND_DIR, "power.wav")
SND_BGM = os.path.join(SND_DIR, "bgm.wav")
SND_HIT = os.path.join(SND_DIR, "hit.wav")

# Background filename
BACKGROUND_FILE = "background.png"

# Colors
COLOR_BG = (5, 8, 20)
COLOR_PLAYER = (94, 234, 212)
COLOR_BULLET = (255, 240, 160)
COLOR_ENEMY_BASE = (196, 182, 166)
COLOR_TEXT = (220, 220, 220)
COLOR_HUD = (180, 180, 180)
COLOR_POWERUP = (130, 200, 255)
COLOR_BOSS = (220, 100, 100)
COLOR_ENEMY_BULLET = (255, 120, 120)

# ----- Data classes -----


@dataclass
class Bullet:
    x: float
    y: float
    dy: float = -BULLET_SPEED
    w: int = BULLET_W
    h: int = BULLET_H

    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h),
                           self.w, self.h)


@dataclass
class Enemy:
    x: float
    y: float
    r: float
    speed: float
    kind: int  # 0 straight, 1 sine, 2 zigzag
    spawn_time: float
    extra: dict
    can_shoot: bool = False
    shoot_timer: float = 0.0
    shoot_interval: float = 2.0  # seconds


@dataclass
class EnemyBullet:
    x: float
    y: float
    dx: float
    dy: float
    r: int = 4


@dataclass
class PowerUp:
    x: float
    y: float
    kind: str  # 'rapid', 'shield', 'spread'
    r: int = 10


@dataclass
class Boss:
    x: float
    y: float
    r: float
    hp: int
    vx: float
    shoot_timer: float = 0.0
    shoot_interval: float = 1.0


# ----- Helper utilities -----


def clamp(v, a, b):
    return max(a, min(b, v))


def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller onefile bundle.
    """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def ensure_snd_dir():
    if not os.path.isdir(SND_DIR):
        os.makedirs(SND_DIR, exist_ok=True)


def write_wav(filename, samples, framerate=44100):
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(framerate)
        packed = b"".join(struct.pack("<h", int(max(-32767, min(32767, int(s * 32767))))) for s in samples)
        wf.writeframes(packed)


def generate_sine(duration_s, freq_hz, volume=0.2, framerate=44100):
    length = int(duration_s * framerate)
    samples = (math.sin(2.0 * math.pi * freq_hz * (i / framerate)) * volume for i in range(length))
    return samples


def build_default_sounds():
    """Generate simple WAV files (shoot, explosion, power, bgm, hit)."""
    ensure_snd_dir()
    if not os.path.exists(SND_SHOOT):
        samples = list(generate_sine(0.08, 880, 0.3))
        write_wav(SND_SHOOT, samples)
    if not os.path.exists(SND_EXPLODE):
        framerate = 44100
        samples = []
        for i in range(int(0.22 * framerate)):
            t = i / framerate
            freq = 400 + (1 - t / 0.22) * 800
            samples.append(math.sin(2.0 * math.pi * freq * t) * (0.35 * (1 - t / 0.22)))
        write_wav(SND_EXPLODE, samples)
    if not os.path.exists(SND_POWER):
        samples = list(generate_sine(0.18, 1320, 0.28))
        write_wav(SND_POWER, samples)
    if not os.path.exists(SND_HIT):
        samples = list(generate_sine(0.06, 440, 0.25))
        write_wav(SND_HIT, samples)
    if not os.path.exists(SND_BGM):
        framerate = 44100
        duration = 6.0
        samples = []
        for i in range(int(duration * framerate)):
            t = i / framerate
            s = (math.sin(2 * math.pi * 110 * t) * 0.08 +
                 math.sin(2 * math.pi * 220 * t) * 0.04)
            s *= 0.9 + 0.1 * math.sin(2 * math.pi * 0.1 * t)
            samples.append(s)
        write_wav(SND_BGM, samples)


# ----- Cat drawing helpers -----


def draw_cat_face(surf, x, y, r, base_color):
    """
    Draw a stylized cat face centered at (x,y) with radius r.
    base_color: tuple for face color
    """
    ix = int(x)
    iy = int(y)
    ir = int(max(4, r))

    # head
    pygame.draw.circle(surf, base_color, (ix, iy), ir)

    # ears (two triangles)
    ear_h = max(6, int(ir * 0.6))
    ear_w = max(6, int(ir * 0.6))
    left_ear = [(ix - int(ir * 0.6), iy - int(ir * 0.6)),
                (ix - int(ir * 0.25), iy - ir - ear_h // 2),
                (ix - int(ir * 0.0), iy - int(ir * 0.25))]
    right_ear = [(ix + int(ir * 0.6), iy - int(ir * 0.6)),
                 (ix + int(ir * 0.25), iy - ir - ear_h // 2),
                 (ix + int(ir * 0.0), iy - int(ir * 0.25))]
    pygame.draw.polygon(surf, base_color, left_ear)
    pygame.draw.polygon(surf, base_color, right_ear)

    # inner ear
    inner = (max(0, base_color[0] - 30), max(0, base_color[1] - 30), max(0, base_color[2] - 30))
    pygame.draw.polygon(surf, inner, [
        (left_ear[0][0] + 4, left_ear[0][1] + 4),
        (left_ear[1][0], left_ear[1][1] + 6),
        (left_ear[2][0] + 4, left_ear[2][1] + 4),
    ])
    pygame.draw.polygon(surf, inner, [
        (right_ear[0][0] - 4, right_ear[0][1] + 4),
        (right_ear[1][0], right_ear[1][1] + 6),
        (right_ear[2][0] - 4, right_ear[2][1] + 4),
    ])

    # eyes
    eye_w = max(3, int(ir * 0.35))
    eye_h = max(3, int(ir * 0.22))
    eye_y = iy - int(ir * 0.1)
    eye_x_off = int(ir * 0.32)
    pygame.draw.ellipse(surf, (255, 255, 255), (ix - eye_x_off - eye_w // 2, eye_y - eye_h // 2, eye_w, eye_h))
    pygame.draw.ellipse(surf, (255, 255, 255), (ix + eye_x_off - eye_w // 2, eye_y - eye_h // 2, eye_w, eye_h))
    # pupils
    pygame.draw.circle(surf, (30, 30, 30), (ix - eye_x_off, eye_y), max(1, eye_w // 4))
    pygame.draw.circle(surf, (30, 30, 30), (ix + eye_x_off, eye_y), max(1, eye_w // 4))

    # nose (triangle)
    nose_y = iy + int(ir * 0.05)
    nose_w = max(4, int(ir * 0.18))
    nose = [(ix, nose_y), (ix - nose_w, nose_y + nose_w), (ix + nose_w, nose_y + nose_w)]
    pygame.draw.polygon(surf, (220, 120, 120), nose)

    # mouth (two lines)
    mouth_y = nose_y + nose_w + 2
    pygame.draw.line(surf, (220, 120, 120), (ix, mouth_y), (ix - int(ir * 0.18), mouth_y + int(ir * 0.14)), 2)
    pygame.draw.line(surf, (220, 120, 120), (ix, mouth_y), (ix + int(ir * 0.18), mouth_y + int(ir * 0.14)), 2)

    # whiskers (three each side)
    whisk_y = iy + int(ir * 0.02)
    for i in (-1, 0, 1):
        off = int(i * (ir * 0.12))
        pygame.draw.line(surf, (200, 200, 200), (ix - int(ir * 0.25), whisk_y + off),
                         (ix - int(ir * 0.6), whisk_y + off - 2), 1)
        pygame.draw.line(surf, (200, 200, 200), (ix + int(ir * 0.25), whisk_y + off),
                         (ix + int(ir * 0.6), whisk_y + off - 2), 1)

    # subtle stripes for variety
    for i in range(2):
        stripe_x = ix - int(ir * 0.3) + i * int(ir * 0.3)
        pygame.draw.arc(surf, inner, (stripe_x, iy - int(ir * 0.1), int(ir * 0.4), int(ir * 0.5)), math.pi, 2 * math.pi, 1)


# ----- Game class -----


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.bigfont = pygame.font.SysFont(None, 48)
        self.sounds = {}
        build_default_sounds()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.load_sounds()

        # Load background (supports bundled executable via resource_path)
        self.bg = None
        try:
            bg_path = resource_path(BACKGROUND_FILE)
            if os.path.exists(bg_path):
                img = pygame.image.load(bg_path)
                # convert for fast blit; keep alpha if present
                if img.get_alpha() is not None:
                    img = img.convert_alpha()
                else:
                    img = img.convert()
                # scale to screen resolution
                self.bg = pygame.transform.smoothscale(img, (SCREEN_W, SCREEN_H))
        except Exception:
            self.bg = None

        self.reset()
        # start bgm
        try:
            pygame.mixer.music.load(resource_path(SND_BGM))
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def load_sounds(self):
        def safe_load(path):
            try:
                return pygame.mixer.Sound(resource_path(path))
            except Exception:
                try:
                    return pygame.mixer.Sound(path)
                except Exception:
                    return None
        self.sounds["shoot"] = safe_load(SND_SHOOT)
        self.sounds["explode"] = safe_load(SND_EXPLODE)
        self.sounds["power"] = safe_load(SND_POWER)
        self.sounds["hit"] = safe_load(SND_HIT)

    def play(self, name):
        s = self.sounds.get(name)
        if s:
            try:
                s.play()
            except Exception:
                pass

    def reset(self):
        self.player_x = SCREEN_W / 2
        self.player_y = PLAYER_Y
        self.player_vx = 0
        self.keys = {"left": False, "right": False}
        self.bullets = []
        self.bullet_cooldown = 0.0
        self.rapid_fire = False
        self.rapid_fire_timer = 0.0
        self.spread = False
        self.spread_timer = 0.0
        self.shield = False
        self.shield_timer = 0.0

        self.enemies = []
        self.enemy_bullets = []
        self.powerups = []

        self.spawn_timer = 0.0
        self.spawn_interval = ENEMY_SPAWN_INTERVAL_START

        self.elapsed = 0.0
        self.score = 0
        self.running = True
        self.game_over = False

        self.boss = None
        self.highscore = self.load_highscore()

    def load_highscore(self):
        try:
            if os.path.exists(HIGHSCORE_FILE):
                with open(HIGHSCORE_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("highscore", 0)
        except Exception:
            pass
        return 0

    def save_highscore(self):
        try:
            prev = self.load_highscore()
            if int(self.score) > int(prev):
                with open(HIGHSCORE_FILE, "w") as f:
                    json.dump({"highscore": int(self.score)}, f)
        except Exception:
            pass

    def spawn_enemy(self):
        size = random.uniform(14, 38)
        x = random.uniform(size / 2, SCREEN_W - size / 2)
        y = -size
        speed = random.uniform(ENEMY_MIN_SPEED, ENEMY_MAX_SPEED)
        kind = random.choices([0, 1, 2], weights=[45, 35, 20])[0]
        spawn_time = self.elapsed
        extra = {}
        if kind == 1:
            extra["amp"] = random.uniform(30, 90)
            extra["freq"] = random.uniform(0.8, 1.6)
            extra["base_x"] = x
        elif kind == 2:
            extra["hz_speed"] = random.uniform(50, 120)
            extra["dir"] = random.choice([-1, 1])
            extra["switch_time"] = random.uniform(0.35, 0.9)
            extra["since_switch"] = 0.0
        can_shoot = random.random() < 0.35 or (self.elapsed > 30 and random.random() < 0.5)
        e = Enemy(x, y, size / 2, speed, kind, spawn_time, extra, can_shoot, 0.0, random.uniform(1.0, 3.0))
        self.enemies.append(e)

    def spawn_powerup(self, x, y):
        kind = random.choice(["rapid", "shield", "spread"])
        self.powerups.append(PowerUp(x, y, kind))

    def spawn_boss(self):
        if self.boss:
            return
        self.boss = Boss(SCREEN_W / 2, -80, 60, hp=18, vx=60.0, shoot_timer=0.0, shoot_interval=1.0)

    def update(self, dt):
        if not self.running:
            return
        if self.game_over:
            return
        self.elapsed += dt

        difficulty_mul = 1.0 + self.elapsed / 60.0

        # Spawn regular enemies until boss appears
        if (self.boss is None) and (self.score < BOSS_APPEAR_SCORE):
            self.spawn_timer += dt
            self.spawn_interval = max(ENEMY_SPAWN_INTERVAL_MIN, ENEMY_SPAWN_INTERVAL_START - self.elapsed / 60.0)
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer = 0.0
                self.spawn_enemy()

        # if score threshold reached spawn boss
        if self.boss is None and self.score >= BOSS_APPEAR_SCORE:
            self.spawn_boss()

        # Player movement
        dir_x = (-1 if self.keys["left"] else 0) + (1 if self.keys["right"] else 0)
        self.player_vx = dir_x * PLAYER_SPEED * difficulty_mul
        self.player_x += self.player_vx * dt
        self.player_x = clamp(self.player_x, PLAYER_W / 2, SCREEN_W - PLAYER_W / 2)

        # Timers for power-ups
        if self.rapid_fire:
            self.rapid_fire_timer -= dt
            if self.rapid_fire_timer <= 0:
                self.rapid_fire = False
        if self.spread:
            self.spread_timer -= dt
            if self.spread_timer <= 0:
                self.spread = False
        if self.shield:
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shield = False

        # Update bullets
        for b in self.bullets[:]:
            b.y += b.dy * dt
            if b.y + b.h < 0:
                try:
                    self.bullets.remove(b)
                except ValueError:
                    pass

        # Enemy bullets
        for eb in self.enemy_bullets[:]:
            eb.x += eb.dx * dt
            eb.y += eb.dy * dt
            if eb.y - eb.r > SCREEN_H or eb.x < -20 or eb.x > SCREEN_W + 20:
                try:
                    self.enemy_bullets.remove(eb)
                except ValueError:
                    pass

        # Update enemies
        for e in self.enemies[:]:
            if e.kind == 0:
                e.y += e.speed * difficulty_mul * dt
            elif e.kind == 1:
                t = self.elapsed - e.spawn_time
                e.y += e.speed * difficulty_mul * dt
                e.x = e.extra["base_x"] + math.sin(t * e.extra["freq"] * 2.0 * math.pi) * e.extra["amp"]
                e.x = clamp(e.x, e.r, SCREEN_W - e.r)
            elif e.kind == 2:
                e.y += e.speed * difficulty_mul * dt
                e.extra["since_switch"] += dt
                if e.extra["since_switch"] >= e.extra["switch_time"]:
                    e.extra["since_switch"] = 0.0
                    e.extra["dir"] *= -1
                e.x += e.extra["dir"] * e.extra["hz_speed"] * dt
                if e.x < e.r:
                    e.x = e.r
                    e.extra["dir"] *= -1
                    e.extra["since_switch"] = 0.0
                if e.x > SCREEN_W - e.r:
                    e.x = SCREEN_W - e.r
                    e.extra["dir"] *= -1
                    e.extra["since_switch"] = 0.0

            # shooting
            if e.can_shoot:
                e.shoot_timer += dt
                if e.shoot_timer >= e.shoot_interval:
                    e.shoot_timer = 0.0
                    dx = self.player_x - e.x
                    dy = self.player_y - e.y
                    dist = math.hypot(dx, dy) or 1.0
                    speed = 180 + random.uniform(-30, 60)
                    self.enemy_bullets.append(EnemyBullet(e.x, e.y + e.r, dx / dist * speed, dy / dist * speed, r=5))

            if e.y - e.r > SCREEN_H:
                try:
                    self.enemies.remove(e)
                except ValueError:
                    pass

        # boss behavior
        if self.boss:
            if self.boss.y < 80:
                self.boss.y += 40 * dt
            else:
                self.boss.x += self.boss.vx * dt
                if self.boss.x < self.boss.r or self.boss.x > SCREEN_W - self.boss.r:
                    self.boss.vx *= -1
                self.boss.shoot_timer += dt
                if self.boss.shoot_timer >= self.boss.shoot_interval:
                    self.boss.shoot_timer = 0.0
                    for angle in (-0.5, -0.25, 0.0, 0.25, 0.5):
                        speed = 200
                        dx = math.sin(angle) * speed
                        dy = math.cos(angle) * speed
                        self.enemy_bullets.append(EnemyBullet(self.boss.x, self.boss.y + self.boss.r - 6, dx, dy))

        # Collisions: bullets vs enemies
        for b in self.bullets[:]:
            hit = False
            for e in self.enemies[:]:
                closest_x = clamp(b.x, e.x - e.r, e.x + e.r)
                closest_y = clamp(b.y, e.y - e.r, e.y + e.r)
                dx = b.x - closest_x
                dy = b.y - closest_y
                if dx * dx + dy * dy <= (e.r) * (e.r):
                    try:
                        self.enemies.remove(e)
                    except ValueError:
                        pass
                    try:
                        self.bullets.remove(b)
                    except ValueError:
                        pass
                    self.score += 10 + int(e.r)
                    self.play("explode")
                    if random.random() < POWERUP_SPAWN_CHANCE:
                        self.spawn_powerup(e.x, e.y)
                    hit = True
                    break
            if hit:
                continue
            if self.boss:
                dx = b.x - self.boss.x
                dy = b.y - self.boss.y
                if dx * dx + dy * dy <= (self.boss.r * self.boss.r):
                    try:
                        self.bullets.remove(b)
                    except ValueError:
                        pass
                    self.boss.hp -= 1
                    self.play("hit")
                    self.score += 15
                    if self.boss.hp <= 0:
                        self.score += 200
                        self.play("explode")
                        self.boss = None
                    continue

        # Collisions: enemy bullets vs player
        player_rect = pygame.Rect(int(self.player_x - PLAYER_W / 2), int(self.player_y - PLAYER_H / 2), PLAYER_W, PLAYER_H)
        for eb in self.enemy_bullets[:]:
            closest_x = clamp(eb.x, player_rect.left, player_rect.right)
            closest_y = clamp(eb.y, player_rect.top, player_rect.bottom)
            dx = eb.x - closest_x
            dy = eb.y - closest_y
            if dx * dx + dy * dy <= (eb.r * eb.r):
                try:
                    self.enemy_bullets.remove(eb)
                except ValueError:
                    pass
                if self.shield:
                    self.shield = False
                    self.play("power")
                else:
                    self.play("explode")
                    self.game_over = True
                    self.running = False
                    self.save_highscore()
                    return

        # Collision: enemies vs player (touch)
        for e in self.enemies[:]:
            closest_x = clamp(e.x, player_rect.left, player_rect.right)
            closest_y = clamp(e.y, player_rect.top, player_rect.bottom)
            dx = e.x - closest_x
            dy = e.y - closest_y
            if dx * dx + dy * dy <= e.r * e.r:
                if self.shield:
                    self.shield = False
                    try:
                        self.enemies.remove(e)
                    except ValueError:
                        pass
                    self.play("explode")
                    self.score += 5
                else:
                    self.play("explode")
                    self.game_over = True
                    self.running = False
                    self.save_highscore()
                    return

        # Powerup collection
        for p in self.powerups[:]:
            dx = p.x - self.player_x
            dy = p.y - self.player_y
            if dx * dx + dy * dy <= (p.r + PLAYER_W / 2) ** 2:
                if p.kind == "rapid":
                    self.rapid_fire = True
                    self.rapid_fire_timer = POWERUP_DURATION
                elif p.kind == "shield":
                    self.shield = True
                    self.shield_timer = POWERUP_DURATION
                elif p.kind == "spread":
                    self.spread = True
                    self.spread_timer = POWERUP_DURATION
                self.play("power")
                try:
                    self.powerups.remove(p)
                except ValueError:
                    pass

        # Powerup falling
        for p in self.powerups[:]:
            p.y += 90 * dt
            if p.y - p.r > SCREEN_H:
                try:
                    self.powerups.remove(p)
                except ValueError:
                    pass

        # Score increases slowly over time
        self.score += dt * 5 * difficulty_mul

    def fire_bullet(self):
        if self.bullet_cooldown > 0:
            return
        cooldown = PLAYER_COOLDOWN * (0.4 if self.rapid_fire else 1.0)
        if self.spread:
            offsets = (-8, 0, 8)
            for off in offsets:
                b = Bullet(self.player_x + off, self.player_y - PLAYER_H / 2)
                self.bullets.append(b)
        else:
            b = Bullet(self.player_x, self.player_y - PLAYER_H / 2)
            self.bullets.append(b)
        self.bullet_cooldown = cooldown
        self.play("shoot")

    def draw_player(self, surf):
        x = int(self.player_x)
        y = int(self.player_y)
        points = [(x, y - PLAYER_H // 2), (x - PLAYER_W // 2, y + PLAYER_H // 2), (x + PLAYER_W // 2, y + PLAYER_H // 2)]
        pygame.draw.polygon(surf, COLOR_PLAYER, points)
        if self.shield:
            pygame.draw.circle(surf, (120, 200, 255), (x, y), int(PLAYER_W), 2)

    def draw(self):
        # draw background image if available, otherwise fallback color
        if self.bg:
            self.screen.blit(self.bg, (0, 0))
            # subtle dark overlay so HUD/text remain readable over busy image
            dark = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 120))  # change alpha to taste
            self.screen.blit(dark, (0, 0))
        else:
            self.screen.fill(COLOR_BG)

        # starfield (decorative; will be drawn on top of background)
        for i in range(60):
            sx = (i * 37) % SCREEN_W
            sy = (i * 61 + int(self.elapsed * 10)) % SCREEN_H
            s = 1 if (i % 7) else 2
            shade = 90 + (i % 6) * 20
            pygame.draw.rect(self.screen, (shade, shade, shade), (sx, sy, s, s))

        # bullets
        for b in self.bullets:
            r = b.rect()
            pygame.draw.rect(self.screen, COLOR_BULLET, r)

        # enemy bullets
        for eb in self.enemy_bullets:
            pygame.draw.circle(self.screen, COLOR_ENEMY_BULLET, (int(eb.x), int(eb.y)), eb.r)

        # enemies as cats
        for e in self.enemies:
            tint = (int(COLOR_ENEMY_BASE[0] * (0.85 + (e.r % 10) * 0.02)) % 255,
                    int(COLOR_ENEMY_BASE[1] * (0.85 + (e.r % 8) * 0.02)) % 255,
                    int(COLOR_ENEMY_BASE[2] * (0.85 + (e.r % 6) * 0.02)) % 255)
            draw_cat_face(self.screen, e.x, e.y, e.r, tint)

        # powerups
        for p in self.powerups:
            pygame.draw.circle(self.screen, COLOR_POWERUP, (int(p.x), int(p.y)), p.r)
            txt = self.font.render(p.kind[0].upper(), True, (10, 10, 10))
            self.screen.blit(txt, (p.x - txt.get_width() / 2, p.y - txt.get_height() / 2))

        # boss as big cat (with slightly different color)
        if self.boss:
            draw_cat_face(self.screen, self.boss.x, self.boss.y, self.boss.r, COLOR_BOSS)
            hp_surf = self.font.render(f"Boss HP: {self.boss.hp}", True, (255, 200, 200))
            self.screen.blit(hp_surf, (SCREEN_W - hp_surf.get_width() - 8, 8))

        # player
        self.draw_player(self.screen)

        # HUD
        score_surf = self.font.render(f"Score: {int(self.score)}  High: {int(self.highscore)}", True, COLOR_TEXT)
        self.screen.blit(score_surf, (8, 8))
        time_surf = self.font.render(f"Time: {int(self.elapsed)}s", True, COLOR_HUD)
        self.screen.blit(time_surf, (8, 30))

        # power-up timers
        yoff = 54
        if self.rapid_fire:
            rf = self.font.render(f"Rapid: {int(self.rapid_fire_timer)}s", True, (200, 240, 200))
            self.screen.blit(rf, (8, yoff)); yoff += 18
        if self.spread:
            sp = self.font.render(f"Spread: {int(self.spread_timer)}s", True, (200, 240, 200))
            self.screen.blit(sp, (8, yoff)); yoff += 18
        if self.shield:
            sh = self.font.render(f"Shield: {int(self.shield_timer)}s", True, (200, 240, 200))
            self.screen.blit(sh, (8, yoff)); yoff += 18

        if self.game_over:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            txt = self.bigfont.render("GAME OVER", True, (255, 255, 255))
            sub = self.font.render(f"Score: {int(self.score)}  Press R to restart", True, (220, 220, 220))
            self.screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, SCREEN_H // 2 - 50))
            self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, SCREEN_H // 2 + 10))

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.keys["left"] = True
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.keys["right"] = True
                    elif event.key == pygame.K_SPACE:
                        if not self.game_over:
                            self.fire_bullet()
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
                elif event.type == pygame.KEYUP:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.keys["left"] = False
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.keys["right"] = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.game_over:
                        self.reset()

            # continuous firing
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                if not self.game_over:
                    self.fire_bullet()

            # cooldown tick
            self.bullet_cooldown = max(0.0, getattr(self, "bullet_cooldown", 0.0) - dt)

            self.update(dt)
            self.draw()


# ----- Main -----
def main():
    pygame.init()
    pygame.display.set_caption("Space Dodger — Cat Attack")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    game = Game(screen)
    game.run()


if __name__ == "__main__":
    main()