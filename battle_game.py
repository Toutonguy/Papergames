#!/usr/bin/env python3
"""
Battle Game: Wave Shooter vs Directional Shooter
Two-player local battle game using PyQt6.

Controls
--------
Player 1 (Wave Shooter) – Blue circle
  WASD          – Move
  Space         – Fire expanding wave (limited range)

Player 2 (Directional Shooter) – Red triangle
  Left / Right  – Rotate
  Up / Down     – Move forward / backward
  Enter         – Fire projectile (unlimited range)

Press R to restart after game-over.
Press Escape to quit.
"""

import sys
import math
import random
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QPolygonF, QRadialGradient, QPainterPath,
)

# ── Constants ────────────────────────────────────────────────────────────────

WINDOW_WIDTH  = 960
WINDOW_HEIGHT = 700
HUD_HEIGHT    = 80
PLAY_H        = WINDOW_HEIGHT - HUD_HEIGHT   # usable play area height

FPS       = 60
FRAME_MS  = 1000 // FPS

# Players
PLAYER_SPEED = 4
P1_RADIUS    = 18
P2_RADIUS    = 18
MAX_HEALTH   = 100
INVINCIBLE_FRAMES = 30   # frames of invincibility after being hit

# Wave (Player 1)
WAVE_SPEED     = 5
WAVE_MAX_R     = 260
WAVE_DAMAGE    = 8
WAVE_COOLDOWN  = 28    # frames between waves
WAVE_THICKNESS = 4

# Projectile (Player 2)
PROJ_SPEED    = 8
PROJ_DAMAGE   = 20
PROJ_RADIUS   = 6
PROJ_COOLDOWN = 12     # frames between shots
ROT_SPEED     = 4.0   # degrees per frame

# Colours
BG_COLOUR    = QColor(12, 12, 28)
HUD_COLOUR   = QColor(20, 20, 45, 230)
P1_COLOUR    = QColor(60, 160, 255)
P1_WAVE_CLR  = QColor(80, 200, 255)
P2_COLOUR    = QColor(255, 80, 80)
P2_PROJ_CLR  = QColor(255, 220, 80)


# ── Particle ─────────────────────────────────────────────────────────────────

class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'colour', 'radius')

    def __init__(self, x: float, y: float, colour: QColor):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.5, 5.0)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(15, 35)
        self.max_life = self.life
        self.colour = colour
        self.radius = random.uniform(2.0, 5.0)

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= 1

    def draw(self, painter: QPainter) -> None:
        alpha = int(255 * self.life / self.max_life)
        c = QColor(self.colour)
        c.setAlpha(alpha)
        painter.setBrush(QBrush(c))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            QRectF(self.x - self.radius, self.y - self.radius,
                   self.radius * 2, self.radius * 2)
        )


# ── Wave (Player 1 projectile) ────────────────────────────────────────────────

class Wave:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.radius = 12.0
        self.active = True
        self.hit = False     # whether this wave already hit P2

    def update(self) -> None:
        self.radius += WAVE_SPEED
        if self.radius >= WAVE_MAX_R:
            self.active = False

    def draw(self, painter: QPainter) -> None:
        if not self.active:
            return
        t = self.radius / WAVE_MAX_R          # 0 → 1 as wave expands
        alpha = int(255 * (1.0 - t) ** 1.4)  # fade out
        r = int(P1_WAVE_CLR.red())
        g = int(P1_WAVE_CLR.green())
        b = int(P1_WAVE_CLR.blue())
        colour = QColor(r, g, b, alpha)
        pen = QPen(colour, WAVE_THICKNESS + (1 - t) * 3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            QRectF(self.x - self.radius, self.y - self.radius,
                   self.radius * 2, self.radius * 2)
        )


# ── Projectile (Player 2 projectile) ─────────────────────────────────────────

class Projectile:
    TRAIL_LEN = 6   # number of trail segments

    def __init__(self, x: float, y: float, angle_deg: float) -> None:
        rad = math.radians(angle_deg)
        self.vx = math.cos(rad) * PROJ_SPEED
        self.vy = math.sin(rad) * PROJ_SPEED
        self.x = x + self.vx * 2   # start slightly ahead of ship
        self.y = y + self.vy * 2
        self.active = True
        self.trail: list[tuple[float, float]] = []

    def update(self, w: int, h: int) -> None:
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        if not (0 <= self.x <= w and 0 <= self.y <= h):
            self.active = False

    def draw(self, painter: QPainter) -> None:
        if not self.active:
            return
        # Trail
        trail_len = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(200 * i / trail_len) if trail_len > 0 else 0
            r = int(PROJ_RADIUS * 0.4 * i / trail_len) if trail_len > 0 else 0
            if r < 1:
                r = 1
            c = QColor(P2_PROJ_CLR)
            c.setAlpha(alpha)
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(tx - r, ty - r, r * 2, r * 2))
        # Head
        painter.setBrush(QBrush(P2_PROJ_CLR))
        painter.setPen(QPen(QColor(255, 255, 200), 1))
        painter.drawEllipse(
            QRectF(self.x - PROJ_RADIUS, self.y - PROJ_RADIUS,
                   PROJ_RADIUS * 2, PROJ_RADIUS * 2)
        )


# ── Player 1: Wave Shooter ────────────────────────────────────────────────────

class Player1:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.health = MAX_HEALTH
        self.score = 0
        self.waves: list[Wave] = []
        self.fire_cd = 0
        self.invincible = 0
        self.flash = 0

    # ── per-frame update ──

    def update(self) -> None:
        if self.fire_cd > 0:
            self.fire_cd -= 1
        if self.invincible > 0:
            self.invincible -= 1
        if self.flash > 0:
            self.flash -= 1
        for w in self.waves:
            w.update()
        self.waves = [w for w in self.waves if w.active]

    def move(self, keys: set, play_h: int) -> None:
        dx = dy = 0.0
        if Qt.Key.Key_W in keys:
            dy -= PLAYER_SPEED
        if Qt.Key.Key_S in keys:
            dy += PLAYER_SPEED
        if Qt.Key.Key_A in keys:
            dx -= PLAYER_SPEED
        if Qt.Key.Key_D in keys:
            dx += PLAYER_SPEED
        self.x = max(P1_RADIUS, min(WINDOW_WIDTH - P1_RADIUS, self.x + dx))
        self.y = max(P1_RADIUS, min(play_h - P1_RADIUS, self.y + dy))

    def fire(self) -> None:
        if self.fire_cd == 0:
            self.waves.append(Wave(self.x, self.y))
            self.fire_cd = WAVE_COOLDOWN

    def take_damage(self, amount: int) -> None:
        if self.invincible > 0:
            return
        self.health = max(0, self.health - amount)
        self.invincible = INVINCIBLE_FRAMES
        self.flash = 10

    @property
    def dead(self) -> bool:
        return self.health <= 0

    # ── drawing ──

    def draw(self, painter: QPainter) -> None:
        # waves drawn behind player
        for w in self.waves:
            w.draw(painter)
        self._draw_body(painter)

    def _draw_body(self, painter: QPainter) -> None:
        # Invincibility blink
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            return
        cx, cy = self.x, self.y
        r = float(P1_RADIUS)

        # Glow
        grad = QRadialGradient(cx, cy, r * 1.8)
        glow = QColor(P1_COLOUR)
        glow.setAlpha(60)
        grad.setColorAt(0.0, glow)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - r * 1.8, cy - r * 1.8, r * 3.6, r * 3.6))

        # Body
        body_col = QColor(255, 255, 255) if self.flash > 0 else P1_COLOUR
        painter.setBrush(QBrush(body_col))
        painter.setPen(QPen(QColor(180, 220, 255), 2))
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Core dot
        painter.setBrush(QBrush(QColor(180, 230, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - r * 0.4, cy - r * 0.4, r * 0.8, r * 0.8))

        # "W" label
        painter.setPen(QColor(20, 60, 120))
        f = QFont('Arial', 9, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(QRectF(cx - 8, cy - 7, 16, 14), Qt.AlignmentFlag.AlignCenter, 'W')


# ── Player 2: Directional Shooter ────────────────────────────────────────────

class Player2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.angle = 180.0   # degrees; 0 = right, 90 = down
        self.health = MAX_HEALTH
        self.score = 0
        self.projectiles: list[Projectile] = []
        self.fire_cd = 0
        self.invincible = 0
        self.flash = 0

    def update(self, w: int, h: int) -> None:
        if self.fire_cd > 0:
            self.fire_cd -= 1
        if self.invincible > 0:
            self.invincible -= 1
        if self.flash > 0:
            self.flash -= 1
        for p in self.projectiles:
            p.update(w, h)
        self.projectiles = [p for p in self.projectiles if p.active]

    def move(self, keys: set, play_h: int) -> None:
        if Qt.Key.Key_Left in keys:
            self.angle = (self.angle - ROT_SPEED) % 360
        if Qt.Key.Key_Right in keys:
            self.angle = (self.angle + ROT_SPEED) % 360
        if Qt.Key.Key_Up in keys:
            rad = math.radians(self.angle)
            self.x = max(P2_RADIUS, min(WINDOW_WIDTH - P2_RADIUS, self.x + math.cos(rad) * PLAYER_SPEED))
            self.y = max(P2_RADIUS, min(play_h - P2_RADIUS, self.y + math.sin(rad) * PLAYER_SPEED))
        if Qt.Key.Key_Down in keys:
            rad = math.radians(self.angle)
            self.x = max(P2_RADIUS, min(WINDOW_WIDTH - P2_RADIUS, self.x - math.cos(rad) * PLAYER_SPEED))
            self.y = max(P2_RADIUS, min(play_h - P2_RADIUS, self.y - math.sin(rad) * PLAYER_SPEED))

    def fire(self) -> None:
        if self.fire_cd == 0:
            self.projectiles.append(Projectile(self.x, self.y, self.angle))
            self.fire_cd = PROJ_COOLDOWN

    def take_damage(self, amount: int) -> None:
        if self.invincible > 0:
            return
        self.health = max(0, self.health - amount)
        self.invincible = INVINCIBLE_FRAMES
        self.flash = 10

    @property
    def dead(self) -> bool:
        return self.health <= 0

    def draw(self, painter: QPainter) -> None:
        for p in self.projectiles:
            p.draw(painter)
        self._draw_body(painter)

    def _draw_body(self, painter: QPainter) -> None:
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            return
        cx, cy = self.x, self.y
        r = float(P2_RADIUS)

        # Glow
        grad = QRadialGradient(cx, cy, r * 1.8)
        glow = QColor(P2_COLOUR)
        glow.setAlpha(60)
        grad.setColorAt(0.0, glow)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - r * 1.8, cy - r * 1.8, r * 3.6, r * 3.6))

        # Triangle body (pointing in angle direction)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle)
        body_col = QColor(255, 255, 255) if self.flash > 0 else P2_COLOUR
        tri = QPolygonF([
            QPointF(r,        0.0),
            QPointF(-r,      -r * 0.75),
            QPointF(-r * 0.5, 0.0),
            QPointF(-r,       r * 0.75),
        ])
        painter.setBrush(QBrush(body_col))
        painter.setPen(QPen(QColor(255, 200, 200), 2))
        painter.drawPolygon(tri)

        # Engine glow dot
        painter.setBrush(QBrush(QColor(255, 200, 100, 180)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(-r - 4, -4, 8, 8))
        painter.restore()

        # "D" label
        painter.setPen(QColor(120, 20, 20))
        f = QFont('Arial', 9, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(QRectF(cx - 7, cy - 7, 14, 14), Qt.AlignmentFlag.AlignCenter, 'D')


# ── Game Widget ───────────────────────────────────────────────────────────────

class GameWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Battle Game – Wave vs Directional')
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._keys: set[int] = set()
        self._particles: list[Particle] = []
        self._state: str = 'countdown'   # 'countdown' | 'playing' | 'over'
        self._winner: int = 0            # 1 or 2
        self._countdown: int = 3 * FPS  # 3-second countdown

        self._init_players()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._loop)
        self._timer.start(FRAME_MS)

    # ── init ──

    def _init_players(self) -> None:
        self._p1 = Player1(WINDOW_WIDTH // 4,   PLAY_H // 2)
        self._p2 = Player2(WINDOW_WIDTH * 3 // 4, PLAY_H // 2)
        self._particles.clear()

    def _reset(self) -> None:
        p1_score = self._p1.score if hasattr(self, '_p1') else 0
        p2_score = self._p2.score if hasattr(self, '_p2') else 0
        self._init_players()
        # Scores persist across rounds
        self._p1.score = p1_score
        self._p2.score = p2_score
        self._state = 'countdown'
        self._countdown = 3 * FPS
        self._winner = 0

    # ── main loop ──

    def _loop(self) -> None:
        if self._state == 'countdown':
            self._countdown -= 1
            if self._countdown <= 0:
                self._state = 'playing'
        elif self._state == 'playing':
            self._handle_held_keys()
            self._p1.move(self._keys, PLAY_H)
            self._p2.move(self._keys, PLAY_H)
            self._p1.update()
            self._p2.update(WINDOW_WIDTH, PLAY_H)
            self._check_collisions()
            self._update_particles()
            self._check_win()
        self.update()

    # ── input ──

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key = event.key()
        self._keys.add(key)
        if self._state == 'over' and key == Qt.Key.Key_R:
            self._reset()
        if key == Qt.Key.Key_Escape:
            self.close()

    def keyReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._keys.discard(event.key())

    def _handle_held_keys(self) -> None:
        if Qt.Key.Key_Space in self._keys:
            self._p1.fire()
        if Qt.Key.Key_Return in self._keys or Qt.Key.Key_Enter in self._keys:
            self._p2.fire()

    # ── collision ──

    def _check_collisions(self) -> None:
        p2x, p2y = self._p2.x, self._p2.y
        p1x, p1y = self._p1.x, self._p1.y

        # Waves → Player 2
        for wave in self._p1.waves:
            if wave.hit:
                continue
            dist = math.hypot(wave.x - p2x, wave.y - p2y)
            if abs(dist - wave.radius) <= P2_RADIUS + WAVE_THICKNESS:
                wave.hit = True
                self._p2.take_damage(WAVE_DAMAGE)
                self._p1.score += 10
                self._spawn_particles(p2x, p2y, P1_WAVE_CLR, 10)

        # Projectiles → Player 1
        for proj in self._p2.projectiles:
            if not proj.active:
                continue
            dist = math.hypot(proj.x - p1x, proj.y - p1y)
            if dist <= P1_RADIUS + PROJ_RADIUS:
                proj.active = False
                self._p1.take_damage(PROJ_DAMAGE)
                self._p2.score += 10
                self._spawn_particles(p1x, p1y, P2_PROJ_CLR, 10)

    def _check_win(self) -> None:
        if self._p1.dead:
            self._state = 'over'
            self._winner = 2
        elif self._p2.dead:
            self._state = 'over'
            self._winner = 1

    # ── particles ──

    def _spawn_particles(self, x: float, y: float, colour: QColor, n: int) -> None:
        for _ in range(n):
            self._particles.append(Particle(x, y, colour))

    def _update_particles(self) -> None:
        for p in self._particles:
            p.update()
        self._particles = [p for p in self._particles if p.alive]

    # ── painting ──

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._draw_background(painter)

        if self._state in ('playing', 'over'):
            self._p1.draw(painter)
            self._p2.draw(painter)
            for part in self._particles:
                part.draw(painter)
            self._draw_hud(painter)

        if self._state == 'countdown':
            self._draw_countdown(painter)

        if self._state == 'over':
            self._draw_overlay(painter)

        painter.end()

    # ── background ──

    def _draw_background(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), BG_COLOUR)
        # subtle grid
        painter.setPen(QPen(QColor(30, 30, 55), 1))
        grid = 60
        for x in range(0, WINDOW_WIDTH, grid):
            painter.drawLine(x, 0, x, PLAY_H)
        for y in range(0, PLAY_H, grid):
            painter.drawLine(0, y, WINDOW_WIDTH, y)

    # ── HUD ──

    def _draw_hud(self, painter: QPainter) -> None:
        hx = 0
        hy = PLAY_H
        hw = WINDOW_WIDTH
        hh = HUD_HEIGHT
        painter.fillRect(hx, hy, hw, hh, HUD_COLOUR)

        bar_w  = 280
        bar_h  = 18
        margin = 20
        bar_y  = hy + hh // 2 - bar_h // 2

        f_lbl = QFont('Arial', 11, QFont.Weight.Bold)
        f_scr = QFont('Arial', 10)

        # ── P1 side ──
        painter.setFont(f_lbl)
        painter.setPen(P1_COLOUR)
        painter.drawText(margin, hy + 18, 'P1  Wave Shooter')
        self._draw_health_bar(painter, margin, bar_y, bar_w, bar_h, self._p1.health)
        painter.setFont(f_scr)
        painter.setPen(QColor(160, 210, 255))
        painter.drawText(margin, hy + hh - 8, f'Score: {self._p1.score}')

        # cooldown pip
        self._draw_cooldown_pip(painter, margin + bar_w + 10, bar_y, self._p1.fire_cd, WAVE_COOLDOWN, P1_WAVE_CLR)

        # ── P2 side ──
        p2_x = WINDOW_WIDTH - margin - bar_w
        painter.setFont(f_lbl)
        painter.setPen(P2_COLOUR)
        painter.drawText(p2_x, hy + 18, 'P2  Directional Shooter')
        self._draw_health_bar(painter, p2_x, bar_y, bar_w, bar_h, self._p2.health)
        painter.setFont(f_scr)
        painter.setPen(QColor(255, 180, 180))
        painter.drawText(p2_x, hy + hh - 8, f'Score: {self._p2.score}')

        self._draw_cooldown_pip(painter, p2_x - 20, bar_y, self._p2.fire_cd, PROJ_COOLDOWN, P2_PROJ_CLR)

        # controls hint (centre)
        f_hint = QFont('Arial', 8)
        painter.setFont(f_hint)
        painter.setPen(QColor(90, 90, 110))
        painter.drawText(
            0, hy, WINDOW_WIDTH, hh,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            'P1: WASD + Space  |  P2: Arrows + Enter  |  R = restart  |  Esc = quit',
        )

    @staticmethod
    def _draw_health_bar(
        painter: QPainter, x: int, y: int, w: int, h: int, health: int
    ) -> None:
        # Background
        painter.setBrush(QBrush(QColor(40, 40, 60)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
        # Fill
        ratio = health / MAX_HEALTH
        if ratio > 0.6:
            col = QColor(50, 210, 80)
        elif ratio > 0.3:
            col = QColor(230, 190, 20)
        else:
            col = QColor(220, 50, 50)
        fill_w = max(0.0, w * ratio)
        painter.setBrush(QBrush(col))
        painter.drawRoundedRect(QRectF(x, y, fill_w, h), 4, 4)
        # HP text
        painter.setPen(QColor(240, 240, 240))
        f = QFont('Arial', 8, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(QRectF(x, y, w, h), Qt.AlignmentFlag.AlignCenter, f'{health} HP')

    @staticmethod
    def _draw_cooldown_pip(
        painter: QPainter, x: int, y: int, cd: int, max_cd: int, colour: QColor
    ) -> None:
        """Small circular cooldown indicator."""
        r = 7.0
        painter.setBrush(QBrush(QColor(40, 40, 60)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(x - r, y, r * 2, r * 2))
        if cd == 0:
            c = QColor(colour)
            c.setAlpha(220)
            painter.setBrush(QBrush(c))
            painter.drawEllipse(QRectF(x - r, y, r * 2, r * 2))

    # ── countdown screen ──

    def _draw_countdown(self, painter: QPainter) -> None:
        # dim
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        num = (self._countdown // FPS) + 1
        text = str(num) if num > 0 else 'GO!'

        f = QFont('Arial', 96, QFont.Weight.Bold)
        painter.setFont(f)

        alpha = 255
        c = QColor(255, 220, 60, alpha)
        painter.setPen(c)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

        f2 = QFont('Arial', 22)
        painter.setFont(f2)
        painter.setPen(QColor(180, 180, 200))
        painter.drawText(
            QRectF(0, WINDOW_HEIGHT * 0.65, WINDOW_WIDTH, 40),
            Qt.AlignmentFlag.AlignCenter,
            'P1 (Blue Circle) – WASD + Space     |     P2 (Red Triangle) – Arrows + Enter',
        )

    # ── game-over overlay ──

    def _draw_overlay(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

        if self._winner == 1:
            title   = 'Player 1 Wins!'
            sub     = 'Wave Shooter Triumphs!'
            col     = P1_COLOUR
        else:
            title   = 'Player 2 Wins!'
            sub     = 'Directional Shooter Triumphs!'
            col     = P2_COLOUR

        cy = WINDOW_HEIGHT // 2

        f1 = QFont('Arial', 56, QFont.Weight.Bold)
        painter.setFont(f1)
        painter.setPen(col)
        painter.drawText(
            QRectF(0, cy - 90, WINDOW_WIDTH, 80),
            Qt.AlignmentFlag.AlignCenter, title,
        )

        f2 = QFont('Arial', 26)
        painter.setFont(f2)
        painter.setPen(QColor(220, 220, 220))
        painter.drawText(
            QRectF(0, cy, WINDOW_WIDTH, 40),
            Qt.AlignmentFlag.AlignCenter, sub,
        )

        f3 = QFont('Arial', 20)
        painter.setFont(f3)
        painter.setPen(QColor(180, 180, 200))
        painter.drawText(
            QRectF(0, cy + 55, WINDOW_WIDTH, 35),
            Qt.AlignmentFlag.AlignCenter,
            f'P1 Score: {self._p1.score}   |   P2 Score: {self._p2.score}',
        )

        f4 = QFont('Arial', 15)
        painter.setFont(f4)
        painter.setPen(QColor(120, 120, 140))
        painter.drawText(
            QRectF(0, cy + 105, WINDOW_WIDTH, 30),
            Qt.AlignmentFlag.AlignCenter,
            'Press  R  to play again   |   Press  Esc  to quit',
        )


# ── entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    app = QApplication(sys.argv)
    win = GameWidget()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
