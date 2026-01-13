#!/usr/bin/env bash
# Create project folder, write files (game.py + requirements.txt), create venv,
# attempt to install system SDL/dev packages (Debian/Ubuntu/Fedora/Arch) if needed,
# install pygame in venv, and run the game.
#
# Usage:
#   ./create_and_run_with_sysdeps.sh               # creates ~/space-dodger and runs
#   ./create_and_run_with_sysdeps.sh /path/to/dir  # use custom folder
set -e

TARGET_DIR="${1:-$HOME/space-dodger}"
PYTHON_CMD=""

echo "Project directory: $TARGET_DIR"

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

echo "Writing requirements.txt..."
cat > requirements.txt <<'REQ'
pygame>=2.1
REQ

echo "Writing game.py..."
cat > game.py <<'PY'
"""
Space Dodger (Pygame)
- Player moves left/right and shoots.
- Enemies spawn and follow one of several movement patterns.
- Score for destroying enemies. Difficulty ramps over time.
"""

import pygame
import random
import math
import sys
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
ENEMY_SPAWN_INTERVAL_MIN = 0.4

# Colors
COLOR_BG = (5, 8, 20)
COLOR_PLAYER = (94, 234, 212)
COLOR_BULLET = (255, 240, 160)
COLOR_ENEMY = (196, 182, 166)
COLOR_TEXT = (220, 220, 220)
COLOR_HUD = (180, 180, 180)

# ----- Data classes -----


@dataclass
class Bullet:
    x: float
    y: float
    dy: float = -BULLET_SPEED

    def rect(self):
        return pygame.Rect(int(self.x - BULLET_W / 2), int(self.y - BULLET_H),
                           BULLET_W, BULLET_H)


@dataclass
class Enemy:
    x: float
    y: float
    r: float
    speed: float
    kind: int  # 0 straight, 1 sine, 2 zigzag
    spawn_time: float
    extra: dict


# ----- Helper utilities -----


def clamp(v, a, b):
    return max(a, min(b, v))


# ----- Game class -----


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.bigfont = pygame.font.SysFont(None, 48)

        self.reset()

    def reset(self):
        self.player_x = SCREEN_W / 2
        self.player_y = PLAYER_Y
        self.player_vx = 0
        self.keys = {"left": False, "right": False}
        self.touch_pressed = {"left": False, "right": False}  # placeholder for extension

        self.bullets = []
        self.bullet_cooldown = 0.0

        self.enemies = []
        self.spawn_timer = 0.0
        self.spawn_interval = ENEMY_SPAWN_INTERVAL_START

        self.elapsed = 0.0
        self.score = 0
        self.running = True
        self.game_over = False
        self.lives = 1

    def spawn_enemy(self):
        # choose size and pattern
        size = random.uniform(14, 38)
        x = random.uniform(size / 2, SCREEN_W - size / 2)
        y = -size
        speed = random.uniform(ENEMY_MIN_SPEED, ENEMY_MAX_SPEED)
        kind = random.choices([0, 1, 2], weights=[45, 35, 20])[0]
        spawn_time = self.elapsed
        extra = {}
        if kind == 1:
            # sine: amplitude and frequency
            extra["amp"] = random.uniform(30, 90)
            extra["freq"] = random.uniform(0.8, 1.6)
            extra["base_x"] = x
        elif kind == 2:
            # zigzag: horizontal speed and time until switch
            extra["hz_speed"] = random.uniform(50, 120)
            extra["dir"] = random.choice([-1, 1])
            extra["switch_time"] = random.uniform(0.35, 0.9)
            extra["since_switch"] = 0.0
        self.enemies.append(Enemy(x, y, size / 2, speed, kind, spawn_time, extra))

    def update(self, dt):
        if not self.running:
            return

        if self.game_over:
            return

        self.elapsed += dt

        # Difficulty ramp
        difficulty_mul = 1.0 + self.elapsed / 40.0

        # Spawn
        self.spawn_timer += dt
        # shrink spawn interval over time but not below min
        self.spawn_interval = max(ENEMY_SPAWN_INTERVAL_MIN, ENEMY_SPAWN_INTERVAL_START - self.elapsed / 60.0)
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_enemy()

        # Input -> velocity
        dir_x = (-1 if self.keys["left"] else 0) + (1 if self.keys["right"] else 0)
        self.player_vx = dir_x * PLAYER_SPEED * difficulty_mul
        self.player_x += self.player_vx * dt
        self.player_x = clamp(self.player_x, PLAYER_W / 2, SCREEN_W - PLAYER_W / 2)

        # Update bullets
        for b in self.bullets[:]:
            b.y += b.dy * dt
            if b.y + BULLET_H < 0:
                self.bullets.remove(b)

        # Bullet cooldown
        self.bullet_cooldown = max(0.0, self.bullet_cooldown - dt)

        # Update enemies
        for e in self.enemies[:]:
            # movement depending on kind
            if e.kind == 0:
                # straight down
                e.y += e.speed * difficulty_mul * dt
            elif e.kind == 1:
                # sine wave horizontally around base_x
                t = self.elapsed - e.spawn_time
                e.y += e.speed * difficulty_mul * dt
                e.x = e.extra["base_x"] + math.sin(t * e.extra["freq"] * 2.0 * math.pi) * e.extra["amp"]
                e.x = clamp(e.x, e.r, SCREEN_W - e.r)
            elif e.kind == 2:
                # zigzag: move down and horizontally switching direction
                e.y += e.speed * difficulty_mul * dt
                e.extra["since_switch"] += dt
                if e.extra["since_switch"] >= e.extra["switch_time"]:
                    e.extra["since_switch"] = 0.0
                    e.extra["dir"] *= -1
                e.x += e.extra["dir"] * e.extra["hz_speed"] * dt
                # bounce off walls
                if e.x < e.r:
                    e.x = e.r
                    e.extra["dir"] *= -1
                    e.extra["since_switch"] = 0.0
                if e.x > SCREEN_W - e.r:
                    e.x = SCREEN_W - e.r
                    e.extra["dir"] *= -1
                    e.extra["since_switch"] = 0.0

            # remove if off-screen (bottom)
            if e.y - e.r > SCREEN_H:
                self.enemies.remove(e)

        # Collisions: bullets vs enemies
        for b in self.bullets[:]:
            br = b.rect()
            hit = False
            for e in self.enemies[:]:
                # circle-rect collision approx by closest point
                closest_x = clamp(b.x, e.x - e.r, e.x + e.r)
                closest_y = clamp(b.y, e.y - e.r, e.y + e.r)
                dx = b.x - closest_x
                dy = b.y - closest_y
                if dx * dx + dy * dy <= (e.r) * (e.r):
                    # hit
                    try:
                        self.enemies.remove(e)
                    except ValueError:
                        pass
                    try:
                        self.bullets.remove(b)
                    except ValueError:
                        pass
                    self.score += 10 + int(e.r)  # bigger enemies worth more
                    hit = True
                    break
            if hit:
                continue

        # Collision: enemies vs player
        player_rect = pygame.Rect(int(self.player_x - PLAYER_W / 2), int(self.player_y - PLAYER_H / 2), PLAYER_W, PLAYER_H)
        for e in self.enemies[:]:
            # rect-circle collision
            closest_x = clamp(e.x, player_rect.left, player_rect.right)
            closest_y = clamp(e.y, player_rect.top, player_rect.bottom)
            dx = e.x - closest_x
            dy = e.y - closest_y
            if dx * dx + dy * dy <= e.r * e.r:
                # collision -> game over
                self.game_over = True
                self.running = False
                break

    def fire_bullet(self):
        if self.bullet_cooldown > 0:
            return
        b = Bullet(self.player_x, self.player_y - PLAYER_H / 2)
        self.bullets.append(b)
        self.bullet_cooldown = PLAYER_COOLDOWN

    def draw_player(self, surf):
        # draw triangle ship
        x = int(self.player_x)
        y = int(self.player_y)
        points = [(x, y - PLAYER_H // 2), (x - PLAYER_W // 2, y + PLAYER_H // 2), (x + PLAYER_W // 2, y + PLAYER_H // 2)]
        pygame.draw.polygon(surf, COLOR_PLAYER, points)

    def draw(self):
        self.screen.fill(COLOR_BG)
        # starfield (simple)
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

        # enemies
        for e in self.enemies:
            # draw simple circle with small shadow/crater
            pygame.draw.circle(self.screen, COLOR_ENEMY, (int(e.x), int(e.y)), int(e.r))
            crater_x = int(e.x - e.r * 0.25)
            crater_y = int(e.y - e.r * 0.2)
            pygame.draw.circle(self.screen, (0, 0, 0, 20), (crater_x, crater_y), max(1, int(e.r * 0.35)))

        # player
        self.draw_player(self.screen)

        # HUD
        score_surf = self.font.render(f"Score: {int(self.score)}", True, COLOR_TEXT)
        self.screen.blit(score_surf, (8, 8))
        time_surf = self.font.render(f"Time: {int(self.elapsed)}s", True, COLOR_HUD)
        self.screen.blit(time_surf, (8, 30))

        if self.game_over:
            # overlay
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
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
                        # restart
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
                        # if clicked while gameover, restart
                        mx, my = event.pos
                        self.reset()

            # continuous firing by holding space? (optional)
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                # allow holding space to rapid-fire
                if not self.game_over:
                    self.fire_bullet()

            self.update(dt)
            self.draw()


# ----- Main -----
def main():
    pygame.init()
    pygame.display.set_caption("Space Dodger (Pygame)")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    game = Game(screen)
    game.run()


if __name__ == "__main__":
    main()
PY

# Choose python command
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "ERROR: No python interpreter found. Install Python 3 and re-run."
  exit 1
fi

echo "Creating virtual environment using: $PYTHON_CMD -m venv venv"
$PYTHON_CMD -m venv venv

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

echo "Upgrading pip/tools..."
python -m pip install --upgrade pip setuptools wheel >/dev/null

echo "Installing dependencies (pygame)..."
# try pip install; if it fails we'll attempt to install system deps
if pip install -r requirements.txt; then
  echo "Pygame installed successfully."
else
  echo
  echo "pip install failed. Attempting to detect package manager to install system dependencies."
  PKG_MGR=""
  if command -v apt-get >/dev/null 2>&1; then
    PKG_MGR="apt"
  elif command -v dnf >/dev/null 2>&1; then
    PKG_MGR="dnf"
  elif command -v pacman >/dev/null 2>&1; then
    PKG_MGR="pacman"
  else
    PKG_MGR="unknown"
  fi

  case "$PKG_MGR" in
    apt)
      echo "Detected apt (Debian/Ubuntu). Required system packages:"
      echo "  sudo apt update && sudo apt install -y python3-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev libfreetype6-dev libjpeg-dev libpng-dev build-essential"
      read -p "Run the apt install command now with sudo? [Y/n] " ans
      ans="${ans:-Y}"
      if [[ "$ans" =~ ^[Yy] ]]; then
        sudo apt update
        sudo apt install -y python3-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev libfreetype6-dev libjpeg-dev libpng-dev build-essential
      else
        echo "Skipping system package install. You must install the above packages manually and re-run this script."
        exit 1
      fi
      ;;
    dnf)
      echo "Detected dnf (Fedora/RHEL). Required system packages (approx):"
      echo "  sudo dnf install -y python3-devel SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel portmidi-devel freetype-devel libpng-devel libjpeg-turbo-devel"
      read -p "Run the dnf install command now with sudo? [Y/n] " ans
      ans="${ans:-Y}"
      if [[ "$ans" =~ ^[Yy] ]]; then
        sudo dnf install -y python3-devel SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel portmidi-devel freetype-devel libpng-devel libjpeg-turbo-devel
      else
        echo "Skipping system package install. You must install the above packages manually and re-run this script."
        exit 1
      fi
      ;;
    pacman)
      echo "Detected pacman (Arch). Required system packages (approx):"
      echo "  sudo pacman -S --needed --noconfirm base-devel python sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi libpng libjpeg-turbo freetype"
      read -p "Run the pacman install command now with sudo? [Y/n] " ans
      ans="${ans:-Y}"
      if [[ "$ans" =~ ^[Yy] ]]; then
        sudo pacman -S --needed --noconfirm base-devel python sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi libpng libjpeg-turbo freetype
      else
        echo "Skipping system package install. You must install the above packages manually and re-run this script."
        exit 1
      fi
      ;;
    *)
      echo "Could not detect a supported package manager. Please install the system SDL and dev packages manually."
      echo "See the README or ask me for exact commands for your distribution."
      exit 1
      ;;
  esac

  echo "Retrying pip install..."
  if pip install -r requirements.txt; then
    echo "Pygame installed successfully after system packages."
  else
    echo "pip install still failed. You may need to install additional development packages for your distribution."
    echo "Exiting."
    exit 1
  fi
fi

echo "Running the game (press Esc to quit)..."
python game.py

# When game exits, deactivate venv (only affects the subshell)
deactivate 2>/dev/null || true

echo "Done."