"""
FUNKY SPACE BLASTER 🚀
A colorful space game built with Python and PyQt6.

Controls:
  Arrow Keys / A/D  - Move spaceship
  Space             - Shoot
  P                 - Pause/Resume
  Q / ESC           - Quit
"""

import sys
import math
import random
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QRadialGradient,
    QLinearGradient, QPolygonF, QPainterPath
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 600
FPS = 60
FRAME_MS = 1000 // FPS

PLAYER_SPEED = 5
BULLET_SPEED = 12
ASTEROID_BASE_SPEED = 1.5
STAR_SPEED = 1.0
SPAWN_INTERVAL = 90          # frames between asteroid spawns (decreases with score)
BULLET_COOLDOWN = 15         # frames between shots

# Colour palette (funky!)
COL_BG        = QColor(8,    4,   30)
COL_PLAYER    = QColor(80,  220, 255)
COL_BULLET    = QColor(255, 240,  60)
COL_ASTEROID  = QColor(180, 100,  40)
COL_STAR_1    = QColor(80,  255, 120)   # green star  +10
COL_STAR_2    = QColor(255, 200,   0)   # gold star   +50
COL_HUD       = QColor(220, 220, 255)
COL_HEALTH    = QColor(80,  255, 100)
COL_DANGER    = QColor(255,  60,  60)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def rand_color():
    palette = [
        QColor(255, 80,  80),
        QColor(255, 160, 40),
        QColor(255, 240, 40),
        QColor(80,  255, 120),
        QColor(40,  200, 255),
        QColor(180, 80,  255),
        QColor(255, 80,  200),
    ]
    return random.choice(palette)


# ---------------------------------------------------------------------------
# Particle
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, color=None):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.5, 6.0)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(20, 45)
        self.max_life = self.life
        self.radius = random.uniform(2, 5)
        self.color = color or rand_color()

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= 1

    @property
    def alive(self):
        return self.life > 0

    def draw(self, painter: QPainter):
        alpha = int(255 * self.life / self.max_life)
        c = QColor(self.color)
        c.setAlpha(alpha)
        painter.setBrush(QBrush(c))
        painter.setPen(Qt.PenStyle.NoPen)
        r = self.radius * self.life / self.max_life
        painter.drawEllipse(QRectF(self.x - r, self.y - r, r * 2, r * 2))


# ---------------------------------------------------------------------------
# Star field (background decoration)
# ---------------------------------------------------------------------------
class StarField:
    def __init__(self, count=120):
        self.stars = [
            (random.randint(0, WIDTH),
             random.randint(0, HEIGHT),
             random.uniform(0.5, 2.5),
             random.randint(60, 200))
            for _ in range(count)
        ]

    def draw(self, painter: QPainter):
        painter.setPen(Qt.PenStyle.NoPen)
        for x, y, r, alpha in self.stars:
            c = QColor(255, 255, 255, alpha)
            painter.setBrush(QBrush(c))
            painter.drawEllipse(QRectF(x - r, y - r, r * 2, r * 2))


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    WIDTH  = 40
    HEIGHT = 48
    MAX_HP = 3

    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 80
        self.hp = self.MAX_HP
        self.invincible = 0          # frames of invincibility after hit
        self.bullet_cooldown = 0
        self.engine_flicker = 0      # animation frame

    @property
    def rect(self):
        hw = self.WIDTH  // 2
        hh = self.HEIGHT // 2
        return QRectF(self.x - hw, self.y - hh, self.WIDTH, self.HEIGHT)

    def move(self, dx, dy):
        hw = self.WIDTH  // 2
        hh = self.HEIGHT // 2
        self.x = max(hw, min(WIDTH  - hw, self.x + dx * PLAYER_SPEED))
        self.y = max(hh, min(HEIGHT - hh, self.y + dy * PLAYER_SPEED))

    def hit(self):
        if self.invincible > 0:
            return False
        self.hp -= 1
        self.invincible = 90   # 1.5 s invincibility
        return True

    def update(self):
        if self.invincible > 0:
            self.invincible -= 1
        if self.bullet_cooldown > 0:
            self.bullet_cooldown -= 1
        self.engine_flicker = (self.engine_flicker + 1) % 8

    def can_shoot(self):
        return self.bullet_cooldown == 0

    def shoot(self):
        self.bullet_cooldown = BULLET_COOLDOWN
        return Bullet(self.x, self.y - self.HEIGHT // 2)

    def draw(self, painter: QPainter):
        if self.invincible > 0 and (self.invincible // 6) % 2 == 0:
            return   # blink while invincible

        cx, cy = self.x, self.y
        hw, hh = self.WIDTH // 2, self.HEIGHT // 2

        # Engine flame
        flame_h = 12 + (4 if self.engine_flicker < 4 else 0)
        flame_colors = [QColor(255, 160, 30), QColor(255, 60, 20)]
        flame_grad = QLinearGradient(cx, cy + hh, cx, cy + hh + flame_h)
        flame_grad.setColorAt(0, QColor(255, 200, 60, 220))
        flame_grad.setColorAt(1, QColor(255, 60,  20, 0))
        painter.setBrush(QBrush(flame_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        flame_poly = QPolygonF([
            QPointF(cx - 8,  cy + hh - 2),
            QPointF(cx + 8,  cy + hh - 2),
            QPointF(cx,      cy + hh + flame_h),
        ])
        painter.drawPolygon(flame_poly)

        # Ship body gradient
        grad = QRadialGradient(cx, cy - hh // 2, hw + 10)
        grad.setColorAt(0, QColor(140, 240, 255))
        grad.setColorAt(1, QColor(30,  100, 180))
        painter.setBrush(QBrush(grad))
        pen = QPen(QColor(180, 240, 255), 1.5)
        painter.setPen(pen)

        # Main hull
        hull = QPolygonF([
            QPointF(cx,          cy - hh),
            QPointF(cx + hw,     cy + hh * 0.6),
            QPointF(cx + hw * 0.4, cy + hh * 0.3),
            QPointF(cx,          cy + hh * 0.6),
            QPointF(cx - hw * 0.4, cy + hh * 0.3),
            QPointF(cx - hw,     cy + hh * 0.6),
        ])
        painter.drawPolygon(hull)

        # Cockpit
        cockpit_grad = QRadialGradient(cx, cy - hh * 0.2, 8)
        cockpit_grad.setColorAt(0, QColor(200, 255, 255, 220))
        cockpit_grad.setColorAt(1, QColor(60,  160, 220, 180))
        painter.setBrush(QBrush(cockpit_grad))
        painter.setPen(QPen(QColor(180, 240, 255), 1))
        painter.drawEllipse(QRectF(cx - 8, cy - hh * 0.55, 16, 16))

        # Wing accents
        painter.setPen(QPen(QColor(255, 220, 60), 1.5))
        painter.drawLine(QPointF(cx - hw * 0.7, cy + hh * 0.4),
                         QPointF(cx - hw * 0.15, cy + hh * 0.1))
        painter.drawLine(QPointF(cx + hw * 0.7, cy + hh * 0.4),
                         QPointF(cx + hw * 0.15, cy + hh * 0.1))


# ---------------------------------------------------------------------------
# Bullet
# ---------------------------------------------------------------------------
class Bullet:
    RADIUS = 4

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.alive = True
        self.trail = []

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        self.y -= BULLET_SPEED
        if self.y < -10:
            self.alive = False

    def rect(self):
        r = self.RADIUS
        return QRectF(self.x - r, self.y - r, r * 2, r * 2)

    def draw(self, painter: QPainter):
        # Trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(180 * i / len(self.trail))
            c = QColor(255, 240, 60, alpha)
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.PenStyle.NoPen)
            r = self.RADIUS * 0.5 * i / max(1, len(self.trail))
            painter.drawEllipse(QRectF(tx - r, ty - r, r * 2, r * 2))

        # Core
        grad = QRadialGradient(self.x, self.y, self.RADIUS * 2)
        grad.setColorAt(0, QColor(255, 255, 200))
        grad.setColorAt(0.5, QColor(255, 220, 40))
        grad.setColorAt(1, QColor(255, 140, 0, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        r = self.RADIUS
        painter.drawEllipse(QRectF(self.x - r, self.y - r, r * 2, r * 2))


# ---------------------------------------------------------------------------
# Asteroid
# ---------------------------------------------------------------------------
class Asteroid:
    def __init__(self, difficulty=1.0):
        self.radius = random.randint(18, 38)
        self.x = float(random.randint(self.radius, WIDTH - self.radius))
        self.y = float(-self.radius)
        speed = ASTEROID_BASE_SPEED * difficulty * random.uniform(0.8, 1.4)
        angle = random.uniform(math.pi * 0.3, math.pi * 0.7)
        self.vx = math.cos(angle - math.pi / 2) * speed * random.uniform(-0.5, 0.5)
        self.vy = speed
        self.rot = 0.0
        self.rot_speed = random.uniform(-3, 3)
        self.alive = True
        self.hp = 1 if self.radius < 28 else 2
        # Random irregular shape offsets
        n = random.randint(8, 12)
        self.shape = [
            (1.0 + random.uniform(-0.3, 0.3)) * self.radius
            for _ in range(n)
        ]
        self.color = QColor(
            random.randint(140, 200),
            random.randint(80,  130),
            random.randint(30,  80)
        )
        self.highlight = QColor(
            min(255, self.color.red()   + 60),
            min(255, self.color.green() + 40),
            min(255, self.color.blue()  + 20),
        )

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rot += self.rot_speed
        if self.y > HEIGHT + self.radius + 10:
            self.alive = False

    def rect(self):
        r = self.radius
        return QRectF(self.x - r, self.y - r, r * 2, r * 2)

    def draw(self, painter: QPainter):
        n = len(self.shape)
        poly = QPolygonF()
        for i, r in enumerate(self.shape):
            angle = math.radians(self.rot + 360 * i / n)
            poly.append(QPointF(
                self.x + math.cos(angle) * r,
                self.y + math.sin(angle) * r,
            ))

        grad = QRadialGradient(
            self.x - self.radius * 0.3,
            self.y - self.radius * 0.3,
            self.radius * 1.2
        )
        grad.setColorAt(0, self.highlight)
        grad.setColorAt(1, self.color.darker(150))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(self.color.darker(180), 1.5))
        painter.drawPolygon(poly)

        # Crater details
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.color.darker(170)))
        for i in range(2):
            angle = math.radians(self.rot * 0.5 + 120 * i)
            cr = self.radius * 0.22
            cx_ = self.x + math.cos(angle) * self.radius * 0.45
            cy_ = self.y + math.sin(angle) * self.radius * 0.45
            painter.drawEllipse(QRectF(cx_ - cr, cy_ - cr, cr * 2, cr * 2))


# ---------------------------------------------------------------------------
# Collectible
# ---------------------------------------------------------------------------
class Collectible:
    """Stars that the player can fly over for points."""
    def __init__(self, kind="green"):
        self.kind  = kind   # "green" (+10) or "gold" (+50)
        self.x     = float(random.randint(20, WIDTH - 20))
        self.y     = float(-20)
        self.vy    = STAR_SPEED * random.uniform(0.8, 1.2)
        self.alive = True
        self.angle = 0.0
        self.bob   = 0.0
        self.bob_v = 0.0
        self.radius = 14
        self.glow_frame = 0
        self.color  = COL_STAR_1 if kind == "green" else COL_STAR_2
        self.points = 10 if kind == "green" else 50

    def update(self):
        self.y += self.vy
        self.angle = (self.angle + 3) % 360
        self.glow_frame = (self.glow_frame + 1) % 60
        if self.y > HEIGHT + 30:
            self.alive = False

    def rect(self):
        r = self.radius
        return QRectF(self.x - r, self.y - r, r * 2, r * 2)

    def _star_polygon(self, cx, cy, outer, inner, n=5, offset=0):
        pts = []
        for i in range(n * 2):
            angle = math.radians(offset + 360 * i / (n * 2) - 90)
            r = outer if i % 2 == 0 else inner
            pts.append(QPointF(cx + math.cos(angle) * r,
                                cy + math.sin(angle) * r))
        return QPolygonF(pts)

    def draw(self, painter: QPainter):
        # Glow
        glow_alpha = int(60 + 40 * math.sin(self.glow_frame * math.tau / 60))
        glow_r = self.radius * 2.2
        glow_grad = QRadialGradient(self.x, self.y, glow_r)
        gc = QColor(self.color)
        gc.setAlpha(glow_alpha)
        glow_grad.setColorAt(0, gc)
        gc2 = QColor(self.color)
        gc2.setAlpha(0)
        glow_grad.setColorAt(1, gc2)
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(
            self.x - glow_r, self.y - glow_r, glow_r * 2, glow_r * 2))

        # Star shape
        star = self._star_polygon(self.x, self.y,
                                   self.radius, self.radius * 0.45,
                                   offset=self.angle)
        c_fill = QColor(self.color)
        c_fill.setAlpha(240)
        painter.setBrush(QBrush(c_fill))
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        painter.drawPolygon(star)

        # Centre highlight
        painter.setBrush(QBrush(QColor(255, 255, 255, 160)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(self.x - 3, self.y - 3, 6, 6))


# ---------------------------------------------------------------------------
# Floating score text
# ---------------------------------------------------------------------------
class FloatText:
    def __init__(self, x, y, text, color=QColor(255, 255, 255)):
        self.x = float(x)
        self.y = float(y)
        self.text = text
        self.color = color
        self.life = 50
        self.max_life = 50

    def update(self):
        self.y -= 1.2
        self.life -= 1

    @property
    def alive(self):
        return self.life > 0

    def draw(self, painter: QPainter):
        alpha = int(255 * self.life / self.max_life)
        c = QColor(self.color)
        c.setAlpha(alpha)
        painter.setPen(QPen(c))
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QPointF(self.x - 20, self.y), self.text)


# ---------------------------------------------------------------------------
# Main Game Widget
# ---------------------------------------------------------------------------
class GameWidget(QWidget):
    STATE_PLAYING   = "playing"
    STATE_PAUSED    = "paused"
    STATE_GAMEOVER  = "gameover"
    STATE_START     = "start"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Funky Space Blaster")
        self.setFixedSize(WIDTH, HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._state = self.STATE_START
        self._keys  = set()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(FRAME_MS)

        self._star_field = StarField()
        self._reset_game()

    # ------------------------------------------------------------------
    def _reset_game(self):
        self.player      = Player()
        self.bullets     : list[Bullet]      = []
        self.asteroids   : list[Asteroid]    = []
        self.collectibles: list[Collectible] = []
        self.particles   : list[Particle]    = []
        self.float_texts : list[FloatText]   = []
        self.score       = 0
        self.frame       = 0
        self.spawn_timer = 0
        self.collect_timer = 0
        self.hi_score    = getattr(self, 'hi_score', 0)

    # ------------------------------------------------------------------
    @property
    def difficulty(self):
        return 1.0 + self.score / 300.0

    @property
    def spawn_interval(self):
        return max(25, int(SPAWN_INTERVAL / self.difficulty))

    @property
    def collect_interval(self):
        return max(80, 160 - int(self.score / 10))

    # ------------------------------------------------------------------
    def _tick(self):
        if self._state != self.STATE_PLAYING:
            self.update()
            return

        self.frame += 1
        self._handle_input()
        self._update_objects()
        self._spawn_objects()
        self._check_collisions()
        self.update()   # triggers paintEvent

    # ------------------------------------------------------------------
    def _handle_input(self):
        dx = dy = 0
        keys = self._keys
        if Qt.Key.Key_Left  in keys or Qt.Key.Key_A in keys:
            dx -= 1
        if Qt.Key.Key_Right in keys or Qt.Key.Key_D in keys:
            dx += 1
        if Qt.Key.Key_Up    in keys or Qt.Key.Key_W in keys:
            dy -= 1
        if Qt.Key.Key_Down  in keys or Qt.Key.Key_S in keys:
            dy += 1
        if dx or dy:
            self.player.move(dx, dy)

        if Qt.Key.Key_Space in keys and self.player.can_shoot():
            bullet = self.player.shoot()
            self.bullets.append(bullet)

    # ------------------------------------------------------------------
    def _update_objects(self):
        self.player.update()

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.alive]

        for a in self.asteroids:
            a.update()
        self.asteroids = [a for a in self.asteroids if a.alive]

        for c in self.collectibles:
            c.update()
        self.collectibles = [c for c in self.collectibles if c.alive]

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

        for ft in self.float_texts:
            ft.update()
        self.float_texts = [ft for ft in self.float_texts if ft.alive]

    # ------------------------------------------------------------------
    def _spawn_objects(self):
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self.asteroids.append(Asteroid(self.difficulty))

        self.collect_timer += 1
        if self.collect_timer >= self.collect_interval:
            self.collect_timer = 0
            kind = "gold" if random.random() < 0.2 else "green"
            self.collectibles.append(Collectible(kind))

    # ------------------------------------------------------------------
    def _explode(self, x, y, count=24, color=None):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    # ------------------------------------------------------------------
    def _check_collisions(self):
        pr = self.player.rect

        # Bullet ↔ Asteroid
        for bullet in list(self.bullets):
            for asteroid in list(self.asteroids):
                if bullet.rect().intersects(asteroid.rect()):
                    bullet.alive = False
                    asteroid.hp -= 1
                    self._explode(asteroid.x, asteroid.y, count=16)
                    if asteroid.hp <= 0:
                        asteroid.alive = False
                        pts = 20 if asteroid.radius < 28 else 35
                        self.score += pts
                        self.float_texts.append(FloatText(
                            asteroid.x, asteroid.y,
                            f"+{pts}", QColor(255, 180, 60)))
                        self._explode(asteroid.x, asteroid.y,
                                      count=30, color=QColor(220, 120, 40))
                    break

        # Player ↔ Asteroid
        for asteroid in list(self.asteroids):
            if pr.intersects(asteroid.rect()):
                if self.player.hit():
                    self._explode(self.player.x, self.player.y,
                                  count=20, color=QColor(80, 200, 255))
                    asteroid.alive = False
                    if self.player.hp <= 0:
                        self._game_over()

        # Player ↔ Collectible
        for col in list(self.collectibles):
            if pr.intersects(col.rect()):
                col.alive = False
                self.score += col.points
                self.float_texts.append(FloatText(
                    col.x, col.y,
                    f"+{col.points}",
                    QColor(80, 255, 120) if col.kind == "green"
                    else QColor(255, 200, 0)
                ))
                self._explode(col.x, col.y, count=12, color=col.color)

    # ------------------------------------------------------------------
    def _game_over(self):
        self._state = self.STATE_GAMEOVER
        self.hi_score = max(self.hi_score, self.score)

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key()
        self._keys.add(key)

        if key == Qt.Key.Key_P:
            if self._state == self.STATE_PLAYING:
                self._state = self.STATE_PAUSED
            elif self._state == self.STATE_PAUSED:
                self._state = self.STATE_PLAYING

        elif key in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            QApplication.quit()

        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Space:
            if self._state in (self.STATE_START, self.STATE_GAMEOVER):
                self._state = self.STATE_PLAYING
                self._reset_game()

    def keyReleaseEvent(self, event):
        self._keys.discard(event.key())

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._draw_background(painter)
        self._star_field.draw(painter)

        if self._state == self.STATE_START:
            self._draw_start_screen(painter)
        elif self._state == self.STATE_GAMEOVER:
            self._draw_game_objects(painter)
            self._draw_gameover_screen(painter)
        elif self._state == self.STATE_PAUSED:
            self._draw_game_objects(painter)
            self._draw_pause_screen(painter)
        else:
            self._draw_game_objects(painter)
            self._draw_hud(painter)

        painter.end()

    # ------------------------------------------------------------------
    def _draw_background(self, painter: QPainter):
        # Deep space gradient
        grad = QLinearGradient(0, 0, 0, HEIGHT)
        grad.setColorAt(0.0, QColor( 8,  4, 30))
        grad.setColorAt(0.5, QColor(12,  6, 45))
        grad.setColorAt(1.0, QColor( 6,  2, 20))
        painter.fillRect(0, 0, WIDTH, HEIGHT, QBrush(grad))

        # Subtle nebula blobs
        for cx, cy, col, r in [
            (200, 150, QColor(60, 20, 100,  25), 180),
            (600, 300, QColor(20, 60, 120,  20), 160),
            (400, 450, QColor(80, 30,  80,  18), 140),
        ]:
            nb = QRadialGradient(cx, cy, r)
            nb.setColorAt(0, col)
            nc = QColor(col)
            nc.setAlpha(0)
            nb.setColorAt(1, nc)
            painter.setBrush(QBrush(nb))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

    # ------------------------------------------------------------------
    def _draw_game_objects(self, painter: QPainter):
        for c in self.collectibles:
            c.draw(painter)
        for a in self.asteroids:
            a.draw(painter)
        for b in self.bullets:
            b.draw(painter)
        for p in self.particles:
            p.draw(painter)
        for ft in self.float_texts:
            ft.draw(painter)
        if self._state != self.STATE_GAMEOVER:
            self.player.draw(painter)

    # ------------------------------------------------------------------
    def _draw_hud(self, painter: QPainter):
        # Score
        painter.setPen(QPen(COL_HUD))
        painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        painter.drawText(QRectF(10, 8, 200, 30), Qt.AlignmentFlag.AlignLeft,
                         f"Score: {self.score}")

        # Hi-score
        painter.setFont(QFont("Arial", 12))
        painter.setPen(QPen(QColor(180, 180, 220)))
        painter.drawText(QRectF(10, 36, 200, 22), Qt.AlignmentFlag.AlignLeft,
                         f"Best: {self.hi_score}")

        # Health bar
        bar_x, bar_y, bar_w, bar_h = WIDTH - 170, 10, 150, 18
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.setBrush(QBrush(QColor(30, 30, 50)))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 4, 4)

        fill = bar_w * self.player.hp / Player.MAX_HP
        hp_color = COL_HEALTH if self.player.hp > 1 else COL_DANGER
        painter.setBrush(QBrush(hp_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_x, bar_y, fill, bar_h), 4, 4)

        painter.setPen(QPen(QColor(200, 220, 255)))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(bar_x, bar_y, bar_w, bar_h),
                         Qt.AlignmentFlag.AlignCenter,
                         f"HP  {self.player.hp}/{Player.MAX_HP}")

        # Difficulty
        diff_txt = f"Level {int(self.difficulty)}"
        painter.setPen(QPen(QColor(160, 120, 255)))
        painter.setFont(QFont("Arial", 11))
        painter.drawText(QRectF(WIDTH // 2 - 50, 8, 100, 22),
                         Qt.AlignmentFlag.AlignCenter, diff_txt)

        # Controls hint (top bar)
        hint = "P=Pause  Q=Quit  Space=Shoot"
        painter.setPen(QPen(QColor(100, 100, 140)))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(QRectF(0, HEIGHT - 18, WIDTH, 16),
                         Qt.AlignmentFlag.AlignCenter, hint)

    # ------------------------------------------------------------------
    def _draw_overlay(self, painter: QPainter, alpha=180):
        painter.setBrush(QBrush(QColor(0, 0, 0, alpha)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, WIDTH, HEIGHT)

    def _draw_title_text(self, painter: QPainter, title, subtitle,
                         title_color=QColor(80, 220, 255), y_offset=0):
        cy = HEIGHT // 2 + y_offset
        # Title glow
        for r in range(3, 0, -1):
            c = QColor(title_color)
            c.setAlpha(40 // r)
            painter.setPen(QPen(c, r * 3))
            painter.setFont(QFont("Arial", 42, QFont.Weight.Bold))
            painter.drawText(QRectF(0, cy - 80, WIDTH, 60),
                             Qt.AlignmentFlag.AlignCenter, title)

        painter.setPen(QPen(title_color))
        painter.setFont(QFont("Arial", 42, QFont.Weight.Bold))
        painter.drawText(QRectF(0, cy - 80, WIDTH, 60),
                         Qt.AlignmentFlag.AlignCenter, title)

        painter.setPen(QPen(QColor(200, 200, 255)))
        painter.setFont(QFont("Arial", 16))
        painter.drawText(QRectF(0, cy - 10, WIDTH, 30),
                         Qt.AlignmentFlag.AlignCenter, subtitle)

    def _draw_start_screen(self, painter: QPainter):
        self._draw_overlay(painter, alpha=160)
        self._draw_title_text(painter,
                              "🚀 FUNKY SPACE BLASTER",
                              "Press ENTER or SPACE to start",
                              QColor(80, 220, 255))

        # Controls
        controls = [
            ("Arrow Keys / WASD", "Move"),
            ("Space",             "Shoot"),
            ("P",                 "Pause / Resume"),
            ("Q / ESC",           "Quit"),
        ]
        painter.setFont(QFont("Arial", 13))
        cy = HEIGHT // 2 + 60
        for i, (key, action) in enumerate(controls):
            row_y = cy + i * 26
            painter.setPen(QPen(QColor(255, 200, 60)))
            painter.drawText(QRectF(WIDTH // 2 - 200, row_y, 180, 22),
                             Qt.AlignmentFlag.AlignRight, key)
            painter.setPen(QPen(QColor(180, 180, 220)))
            painter.drawText(QRectF(WIDTH // 2 + 20, row_y, 180, 22),
                             Qt.AlignmentFlag.AlignLeft, action)

    def _draw_pause_screen(self, painter: QPainter):
        self._draw_overlay(painter, alpha=140)
        self._draw_title_text(painter,
                              "⏸  PAUSED",
                              "Press P to resume",
                              QColor(255, 180, 60))

    def _draw_gameover_screen(self, painter: QPainter):
        self._draw_overlay(painter, alpha=180)
        self._draw_title_text(painter,
                              "GAME OVER",
                              f"Score: {self.score}   Best: {self.hi_score}",
                              QColor(255, 80, 80))
        painter.setPen(QPen(QColor(180, 200, 255)))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(QRectF(0, HEIGHT // 2 + 50, WIDTH, 28),
                         Qt.AlignmentFlag.AlignCenter,
                         "Press ENTER or SPACE to play again")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Funky Space Blaster")
    window = GameWidget()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
