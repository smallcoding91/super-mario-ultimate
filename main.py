import pygame
import sys
import numpy as np
import random
from enum import Enum

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

W, H = 1000, 500
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Super Mario Ultimate Edition")
clock = pygame.time.Clock()
FPS = 60

# 颜色定义
SKY        = (135, 206, 235)
WHITE      = (255, 255, 255)
RED        = (255,   0,   0)
YELLOW     = (255, 215,   0)
BROWN      = (139,  69,  19)
GREEN      = ( 34, 139,  34)
BLUE       = (  0,   0, 255)
PURPLE     = (128,   0, 128)
ORANGE     = (255, 165,   0)
PINK       = (255, 192, 203)
DARK_GREEN = (  0, 100,   0)
GRAY       = (128, 128, 128)
BLACK      = (  0,   0,   0)
DARK_RED   = (139,   0,   0)
ICE_BLUE   = (173, 216, 230)
DEEP_BLUE  = ( 25,  25, 112)
LAVA       = (255,  69,   0)
JUNGLE_GREEN = ( 34, 139,  34)
MUD_BROWN  = (101,  67,  33)

# ====================== 音效系统 ======================
def make_sound(freq, duration, wave_type="sine"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    if wave_type == "sine":
        wave = np.sin(2 * np.pi * freq * t)
    elif wave_type == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    elif wave_type == "sawtooth":
        wave = 2 * (t * freq - np.floor(0.5 + t * freq))
    mono = (wave * 32767 * 0.3).astype(np.int16)
    stereo = np.column_stack([mono, mono])
    return pygame.sndarray.make_sound(stereo)

jump_sound     = make_sound(440,  0.1,  "sine")
coin_sound     = make_sound(880,  0.1,  "square")
dead_sound     = make_sound(220,  0.3,  "sawtooth")
stomp_sound    = make_sound(660,  0.1,  "square")
powerup_sound  = make_sound(523,  0.2,  "sine")
shoot_sound    = make_sound(392,  0.05, "square")
teleport_sound = make_sound(1046, 0.15, "sine")
boss_hit_sound = make_sound(200, 0.15, "sawtooth")
boss_dead_sound = make_sound(100, 0.5, "sawtooth")
menu_select_sound = make_sound(600, 0.1, "square")

# ====================== 技能类型 ======================
class PowerType(Enum):
    NONE        = 0
    FIRE        = 1
    DOUBLE_JUMP = 2
    SPEED       = 3
    SHIELD      = 4

# ====================== 玩家类 ======================
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.base_size = (28, 42)
        self.image = pygame.Surface(self.base_size)
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.y = 418
        self.base_speed  = 5
        self.speed       = 5
        self.jump_power  = 15
        self.gravity     = 0.75
        self.vel_x       = 0
        self.vel_y       = 0
        self.on_ground   = True
        self.score       = 0
        self.lives       = 3
        self.coins       = 0
        self.invincible       = False
        self.invincible_timer = 0
        self.power_type  = PowerType.NONE
        self.power_timer = 0
        self.jumps_left  = 1
        self.fire_cooldown = 0
        self.shield_active = False
        self.shield_timer  = 0
        self.permanent_powers = False
        self.update_appearance()

    def update(self):
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False
        if not self.permanent_powers:
            if self.power_timer > 0:
                self.power_timer -= 1
                if self.power_timer <= 0:
                    self.power_type = PowerType.NONE
                    self.speed = self.base_speed
            if self.shield_active:
                self.shield_timer -= 1
                if self.shield_timer <= 0:
                    self.shield_active = False
        else:
            if self.power_timer <= 0:
                self.power_timer = 1
            if self.shield_active and self.shield_timer <= 0:
                self.shield_timer = 1

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        self.vel_y = min(self.vel_y + self.gravity, 15)
        self.update_appearance()

    def update_appearance(self):
        self.image = pygame.Surface(self.base_size)
        if self.shield_active:
            self.image.fill(BLUE)
        elif self.power_type == PowerType.FIRE:
            self.image.fill(ORANGE)
        elif self.power_type == PowerType.SPEED:
            self.image.fill(PINK)
        else:
            self.image.fill(RED)
        pygame.draw.circle(self.image, WHITE, ( 8, 8), 4)
        pygame.draw.circle(self.image, BLACK, ( 8, 8), 2)
        pygame.draw.circle(self.image, WHITE, (20, 8), 4)
        pygame.draw.circle(self.image, BLACK, (20, 8), 2)

    def activate_power(self, power_type, duration=600):
        self.power_type  = power_type
        self.power_timer = duration if not self.permanent_powers else 1
        powerup_sound.play()
        if power_type == PowerType.DOUBLE_JUMP:
            self.jumps_left = 2
        elif power_type == PowerType.SHIELD:
            self.shield_active = True
            self.shield_timer  = duration if not self.permanent_powers else 1
        elif power_type == PowerType.SPEED:
            self.speed = 10

    def shoot_fireball(self):
        if self.power_type == PowerType.FIRE and self.fire_cooldown <= 0:
            self.fire_cooldown = 20
            shoot_sound.play()
            direction = 1 if self.vel_x >= 0 else -1
            return Fireball(self.rect.centerx, self.rect.centery, direction, is_enemy=False)
        return None

# ====================== 火球 ======================
class Fireball(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, is_enemy=False):
        super().__init__()
        self.image = pygame.Surface((12, 12))
        self.image.fill(ORANGE if not is_enemy else DARK_RED)
        pygame.draw.circle(self.image, YELLOW if not is_enemy else BLACK, (6, 6), 4)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed    = 8 * direction
        self.lifetime = 90
        self.vel_y = -3 if not is_enemy else -2
        self.gravity = 0.3
        self.is_enemy = is_enemy

    def update(self, platforms):
        self.rect.x += self.speed
        self.vel_y += self.gravity
        self.rect.y += int(self.vel_y)
        self.lifetime -= 1
        for p in platforms:
            if self.rect.colliderect(p.rect):
                self.kill()
                break
        if self.lifetime <= 0 or self.rect.x < 0 or self.rect.x > 2000 or self.rect.top > H:
            self.kill()

# ====================== 平台 ======================
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, color=GREEN, has_grass=True):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(color)
        if has_grass and color == GREEN:
            for i in range(0, w, 5):
                pygame.draw.line(self.image, DARK_GREEN, (i, 0), (i, 3), 2)
        self.rect = self.image.get_rect(topleft=(x, y))

class MovingPlatform(Platform):
    def __init__(self, x, y, w, h, move_range, speed, move_type="horizontal"):
        super().__init__(x, y, w, h, BLUE, False)
        self.start_x    = x
        self.start_y    = y
        self.move_range = move_range
        self.speed      = int(speed * 10)
        self.direction  = 1
        self.move_type  = move_type
        self.prev_x = x
        self.prev_y = y

    def update(self):
        self.prev_x = self.rect.x
        self.prev_y = self.rect.y
        if self.move_type == "horizontal":
            self.rect.x += (self.speed * self.direction) // 10
            if self.rect.x >= self.start_x + self.move_range:
                self.rect.x = self.start_x + self.move_range
                self.direction = -1
            elif self.rect.x <= self.start_x:
                self.rect.x = self.start_x
                self.direction = 1
        else:
            self.rect.y += (self.speed * self.direction) // 10
            if self.rect.y >= self.start_y + self.move_range:
                self.rect.y = self.start_y + self.move_range
                self.direction = -1
            elif self.rect.y <= self.start_y:
                self.rect.y = self.start_y
                self.direction = 1

    def get_delta(self):
        return (self.rect.x - self.prev_x, self.rect.y - self.prev_y)

class BreakablePlatform(Platform):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h, BROWN, False)
        self.health = 2

    def hit(self):
        self.health -= 1
        if self.health <= 0:
            self.kill()
            return True
        self.image.fill((180, 100, 30))
        return False

# ====================== 金币 ======================
class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y, value=100):
        super().__init__()
        self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(self.image, YELLOW, (10, 10), 8)
        self.rect         = self.image.get_rect(topleft=(x, y))
        self.value        = value
        self.float_offset = random.random() * 2 * np.pi
        self.base_y       = float(y)

    def update(self):
        self.rect.y = int(self.base_y +
                          np.sin(pygame.time.get_ticks() * 0.05 + self.float_offset) * 4)

# ====================== 问号砖块 ======================
class QuestionBlock(pygame.sprite.Sprite):
    def __init__(self, x, y, power_type=None):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill(YELLOW)
        pygame.draw.rect(self.image, BLACK, (0, 0, 32, 32), 2)
        font = pygame.font.Font(None, 28)
        txt  = font.render("?", True, BLACK)
        self.image.blit(txt, (10, 6))
        self.rect       = self.image.get_rect(topleft=(x, y))
        self.power_type = power_type
        self.activated  = False

    def hit(self):
        if not self.activated:
            self.activated = True
            self.image.fill(GRAY)
            pygame.draw.rect(self.image, BLACK, (0, 0, 32, 32), 2)
            coin_sound.play()
            return self.power_type
        return None

# ====================== 普通敌人 ======================
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, color=BROWN, speed=2):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill(color)
        pygame.draw.circle(self.image, RED, ( 8, 8), 4)
        pygame.draw.circle(self.image, RED, (24, 8), 4)
        self.rect      = self.image.get_rect(topleft=(x, y))
        self.speed     = speed
        self.direction = 1
        self.health    = 1
        self.vel_y     = 0
        self.gravity   = 0.5

    def update(self, platforms):
        self.vel_y = min(self.vel_y + self.gravity, 12)
        self.rect.y += int(self.vel_y)
        for p in platforms:
            if (self.rect.bottom >= p.rect.top and
                self.rect.bottom <= p.rect.top + 12 and
                self.rect.right > p.rect.left and
                self.rect.left  < p.rect.right and
                self.vel_y >= 0):
                self.rect.bottom = p.rect.top
                self.vel_y = 0
                break
        self.rect.x += int(self.speed * self.direction)
        if self.rect.left < 0 or self.rect.right > 2000:
            self.direction *= -1
        check_x = self.rect.right + 5 if self.direction > 0 else self.rect.left - 5
        on_ground = False
        for p in platforms:
            if self.rect.bottom == p.rect.top and p.rect.left <= check_x <= p.rect.right:
                on_ground = True
                break
        if not on_ground and self.vel_y >= 0:
            self.direction *= -1
        if self.rect.top > H:
            self.kill()

class FlyingEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, PURPLE, 3)
        self.float_offset = random.random() * 2 * np.pi
        self.base_y = float(y)

    def update(self, platforms):
        self.rect.x += int(self.speed * self.direction)
        if self.rect.left < 0 or self.rect.right > 2000:
            self.direction *= -1
        self.rect.y = int(self.base_y +
                          np.sin(pygame.time.get_ticks() * 0.01 + self.float_offset) * 20)
        if self.rect.top > H:
            self.kill()

class JungleEnemy(Enemy):
    """丛林蜘蛛：移动快，会跳"""
    def __init__(self, x, y):
        super().__init__(x, y, (139, 69, 19), 3)
        self.image = pygame.Surface((32, 32))
        self.image.fill((139, 69, 19))
        pygame.draw.circle(self.image, RED, (8, 8), 4)
        pygame.draw.circle(self.image, RED, (24, 8), 4)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.jump_timer = 0

    def update(self, platforms):
        self.vel_y = min(self.vel_y + self.gravity, 12)
        self.rect.y += int(self.vel_y)
        on_ground = False
        for p in platforms:
            if (self.rect.bottom >= p.rect.top and
                self.rect.bottom <= p.rect.top + 12 and
                self.rect.right > p.rect.left and
                self.rect.left  < p.rect.right and
                self.vel_y >= 0):
                self.rect.bottom = p.rect.top
                self.vel_y = 0
                on_ground = True
                break
        self.rect.x += int(self.speed * self.direction)
        if self.rect.left < 0 or self.rect.right > 2000:
            self.direction *= -1
        if on_ground and pygame.time.get_ticks() - self.jump_timer > 1500:
            self.vel_y = -12
            self.jump_timer = pygame.time.get_ticks()
        check_x = self.rect.right + 5 if self.direction > 0 else self.rect.left - 5
        edge = True
        for p in platforms:
            if self.rect.bottom == p.rect.top and p.rect.left <= check_x <= p.rect.right:
                edge = False
                break
        if edge and self.vel_y >= 0:
            self.direction *= -1
        if self.rect.top > H:
            self.kill()

class PlantEnemy(pygame.sprite.Sprite):
    """食人花：固定在平台上，周期性伸出"""
    def __init__(self, x, y):
        super().__init__()
        self.base_y = y
        self.image = pygame.Surface((30, 40))
        self.image.fill(GREEN)
        pygame.draw.circle(self.image, RED, (15, 10), 8)
        self.rect = self.image.get_rect(topleft=(x, y - 40))
        self.timer = 0
        self.state = "hidden"  # hidden / rising / extended / retracting
        self.extend_speed = 2
        self.health = 1

    def update(self, platforms):
        self.timer += 1
        if self.state == "hidden":
            if self.timer > 120:
                self.state = "rising"
                self.timer = 0
        elif self.state == "rising":
            self.rect.y -= self.extend_speed
            if self.rect.y <= self.base_y - 40:
                self.rect.y = self.base_y - 40
                self.state = "extended"
                self.timer = 0
        elif self.state == "extended":
            if self.timer > 90:
                self.state = "retracting"
                self.timer = 0
        elif self.state == "retracting":
            self.rect.y += self.extend_speed
            if self.rect.y >= self.base_y:
                self.rect.y = self.base_y
                self.state = "hidden"
                self.timer = 0

    def hit(self):
        self.health -= 1
        if self.health <= 0:
            self.kill()
            return True
        return False

class BigEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, DARK_GREEN, 1)
        self.image = pygame.Surface((48, 48))
        self.image.fill(DARK_GREEN)
        pygame.draw.circle(self.image, RED, (12, 12), 6)
        pygame.draw.circle(self.image, RED, (36, 12), 6)
        self.rect   = self.image.get_rect(topleft=(x, y))
        self.health = 3

# ====================== Boss敌人 ======================
class BossEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((64, 64))
        self.image.fill(DARK_RED)
        pygame.draw.circle(self.image, YELLOW, (16, 16), 8)
        pygame.draw.circle(self.image, YELLOW, (48, 16), 8)
        pygame.draw.circle(self.image, BLACK, (16, 16), 4)
        pygame.draw.circle(self.image, BLACK, (48, 16), 4)
        pygame.draw.arc(self.image, WHITE, (20, 30, 24, 20), 0, np.pi, 4)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.max_health = 10
        self.health = self.max_health
        self.speed = 2
        self.direction = 1
        self.vel_y = 0
        self.gravity = 0.5
        self.jump_timer = 0
        self.shoot_timer = 0
        self.invincible = False
        self.invincible_timer = 0

    def update(self, platforms, player, fireballs_group, all_sprites):
        self.vel_y = min(self.vel_y + self.gravity, 12)
        self.rect.y += int(self.vel_y)

        on_ground = False
        for p in platforms:
            if (self.rect.bottom >= p.rect.top and
                self.rect.bottom <= p.rect.top + 12 and
                self.rect.right > p.rect.left and
                self.rect.left  < p.rect.right and
                self.vel_y >= 0):
                self.rect.bottom = p.rect.top
                self.vel_y = 0
                on_ground = True
                break

        if on_ground:
            self.rect.x += self.speed * self.direction
            if self.rect.left < 100 or self.rect.right > 1900:
                self.direction *= -1

        if on_ground and pygame.time.get_ticks() - self.jump_timer > 2000:
            self.vel_y = -18
            self.jump_timer = pygame.time.get_ticks()

        if pygame.time.get_ticks() - self.shoot_timer > 3000:
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            fb = Fireball(self.rect.centerx, self.rect.centery - 20, direction, is_enemy=True)
            fireballs_group.add(fb)
            all_sprites.add(fb)
            self.shoot_timer = pygame.time.get_ticks()

        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

        if self.rect.top > H:
            self.kill()

    def hit(self):
        if not self.invincible:
            self.health -= 1
            self.invincible = True
            self.invincible_timer = 30
            boss_hit_sound.play()
            if self.health <= 0:
                boss_dead_sound.play()
                self.kill()
                return True
        return False

# ====================== 装饰 ======================
class Cloud(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=0.5):
        super().__init__()
        self.image = pygame.Surface((80, 40), pygame.SRCALPHA)
        pygame.draw.circle(self.image, WHITE, (20, 20), 15)
        pygame.draw.circle(self.image, WHITE, (40, 15), 20)
        pygame.draw.circle(self.image, WHITE, (60, 20), 15)
        pygame.draw.rect(self.image, WHITE, (20, 10, 40, 20))
        self.rect  = self.image.get_rect(topleft=(x, y))
        self.speed = speed

    def update(self):
        self.rect.x -= self.speed
        if self.rect.right < 0:
            self.rect.x = 2000
            self.rect.y = random.randint(20, 150)

class Bush(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((60, 30), pygame.SRCALPHA)
        pygame.draw.circle(self.image, DARK_GREEN, (15, 20), 12)
        pygame.draw.circle(self.image, DARK_GREEN, (30, 15), 15)
        pygame.draw.circle(self.image, DARK_GREEN, (45, 20), 12)
        self.rect = self.image.get_rect(topleft=(x, y))

class Portal(pygame.sprite.Sprite):
    def __init__(self, x, y, target_level):
        super().__init__()
        self.image = pygame.Surface((40, 80))
        self.image.fill(PURPLE)
        pygame.draw.ellipse(self.image, PINK, (5, 5, 30, 70))
        self.rect         = self.image.get_rect(topleft=(x, y))
        self.target_level = target_level
        self.active       = True

# ====================== 背景生成器 ======================
def generate_background(level_num, width=2000):
    bg = pygame.Surface((width, H))
    if level_num == 1:
        bg.fill(SKY)
        for i in range(6):
            color = (100 + i*30, 130 + i*20, 100)
            points = [(0, H), (150 + i*200, 300), (350 + i*150, 200), (600 + i*180, 320), (width, H)]
            pygame.draw.polygon(bg, color, points)
        for cx, cy in [(200, 80), (700, 120), (500, 60), (1200, 90), (1600, 70)]:
            pygame.draw.circle(bg, WHITE, (cx, cy), 25)
            pygame.draw.circle(bg, WHITE, (cx+25, cy-5), 30)
            pygame.draw.circle(bg, WHITE, (cx+50, cy), 20)
    elif level_num == 2:
        for y in range(H):
            r = int(180 + 75 * (y / H))
            g = int(60 + 40 * (y / H))
            b = int(40)
            pygame.draw.line(bg, (r, g, b), (0, y), (width, y))
        volcano_color = (80, 40, 20)
        pygame.draw.polygon(bg, volcano_color, [(300, H), (500, 250), (700, H)])
        pygame.draw.polygon(bg, DARK_RED, [(450, H), (500, 250), (550, H)])
        lava_glow = pygame.Surface((100, 100), pygame.SRCALPHA)
        pygame.draw.circle(lava_glow, (255, 100, 0, 100), (50, 50), 50)
        bg.blit(lava_glow, (450, 150))
        for i in range(3):
            pygame.draw.circle(bg, (100, 100, 100), (500 + i*20, 200 - i*15), 20 + i*5)
    elif level_num == 3:
        for y in range(H):
            c = min(255, int(180 + 75 * (y / H)))
            pygame.draw.line(bg, (c, min(255, c+40), 255), (0, y), (width, y))
        ice_color = (200, 230, 255)
        for i in range(6):
            x_base = 100 + i * 350
            points = [(x_base, H), (x_base+50, 350), (x_base+150, 280), (x_base+250, 350), (x_base+300, H)]
            pygame.draw.polygon(bg, ice_color, points)
            pygame.draw.polygon(bg, WHITE, [(x_base+150, 280), (x_base+120, 320), (x_base+180, 320)])
        for _ in range(50):
            x = random.randint(0, width)
            y = random.randint(0, H)
            pygame.draw.circle(bg, WHITE, (x, y), 2)
    elif level_num == 4:
        for y in range(H):
            r = int(20 + 30 * (y / H))
            g = int(50 + 80 * (y / H))
            b = int(120 + 100 * (y / H))
            pygame.draw.line(bg, (r, g, b), (0, y), (width, y))
        for i in range(10):
            x = 100 + i * 200
            pygame.draw.polygon(bg, (80, 150, 220, 50), [(x, 0), (x+60, 0), (x+100, H)])
        for _ in range(30):
            x = random.randint(0, width)
            y = random.randint(0, H)
            radius = random.randint(2, 6)
            pygame.draw.circle(bg, WHITE, (x, y), radius, 1)
        pygame.draw.rect(bg, (210, 180, 140), (0, H-30, width, 30))
        for i in range(16):
            x = 50 + i*120
            for j in range(3):
                pygame.draw.arc(bg, DARK_GREEN, (x+j*10, H-50, 20, 40), 0, np.pi, 3)
    elif level_num == 5:
        for y in range(H):
            r = int(60 + 40 * (y / H))
            g = int(30 + 20 * (y / H))
            b = int(40 + 30 * (y / H))
            pygame.draw.line(bg, (r, g, b), (0, y), (width, y))
        pygame.draw.rect(bg, (80, 60, 70), (600, 200, 300, 260))
        for i in range(3):
            pygame.draw.rect(bg, (100, 80, 90), (620 + i*90, 150, 40, 50))
        pygame.draw.rect(bg, YELLOW, (650, 250, 50, 70))
        pygame.draw.rect(bg, YELLOW, (780, 250, 50, 70))
        pygame.draw.rect(bg, BROWN, (450, 420, 150, 20))
        for i in range(30):
            x = i * 60
            pygame.draw.ellipse(bg, LAVA, (x, 440, 60, 30))
    else:  # level 6 丛林探险
        # 深绿色渐变背景
        for y in range(H):
            r = int(20 + 30 * (y / H))
            g = int(80 + 40 * (y / H))
            b = int(20 + 20 * (y / H))
            pygame.draw.line(bg, (r, g, b), (0, y), (width, y))
        # 树木剪影
        tree_color = (60, 80, 30)
        for i in range(12):
            x = 50 + i * 160
            pygame.draw.rect(bg, (101, 67, 33), (x, 300, 20, 160))
            pygame.draw.circle(bg, tree_color, (x+10, 280), 40)
            pygame.draw.circle(bg, tree_color, (x-15, 300), 35)
            pygame.draw.circle(bg, tree_color, (x+35, 300), 35)
        # 藤蔓
        for i in range(20):
            x = random.randint(0, width)
            y = random.randint(50, 300)
            pygame.draw.line(bg, (34, 139, 34), (x, y), (x+5, y+30), 3)
        # 地面细节
        pygame.draw.rect(bg, MUD_BROWN, (0, H-30, width, 30))
    return bg

# ====================== 游戏管理 ======================
GROUND_Y = 460
PLAYER_H = 42
SPAWN_Y = GROUND_Y - PLAYER_H

class Game:
    def __init__(self):
        self.level      = 1
        self.max_level  = 6
        self.game_state = "menu"
        self.next_level = None
        self.menu_selection = 0
        self.camera_x = 0
        self.world_width = 2000  # 默认地图宽度

        self.all_sprites    = pygame.sprite.Group()
        self.platforms      = pygame.sprite.Group()
        self.coins          = pygame.sprite.Group()
        self.enemies        = pygame.sprite.Group()
        self.fireballs      = pygame.sprite.Group()
        self.decorations    = pygame.sprite.Group()
        self.question_blocks = pygame.sprite.Group()
        self.portals        = pygame.sprite.Group()

        self.player   = None
        self.font     = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 72)
        self.background = None
        self.boss = None

        self.menu_background = generate_background(1, 2000)

    def _add(self, sprite, *groups):
        self.all_sprites.add(sprite)
        for g in groups:
            g.add(sprite)

    def load_background(self, level_num, width=2000):
        try:
            img_path = f"assets/bg_level{level_num}.png"
            self.background = pygame.image.load(img_path).convert()
            self.background = pygame.transform.scale(self.background, (width, H))
        except Exception:
            self.background = generate_background(level_num, width)
    
    def load_level(self, level_num):
        self.level = level_num
        # 设置世界宽度
        if level_num == 6:
            self.world_width = 2000
        else:
            self.world_width = 1000
        self.camera_x = 0
        self.load_background(level_num, self.world_width)
        
        for g in [self.all_sprites, self.platforms, self.coins, self.enemies,
                  self.fireballs, self.decorations, self.question_blocks, self.portals]:
            g.empty()

        self.player = Player()
        if level_num == 5:
            self.player.permanent_powers = True
        self.all_sprites.add(self.player)

        ground = Platform(0, GROUND_Y, self.world_width, 40)
        self._add(ground, self.platforms)

        for _ in range(8):
            self._add(Cloud(random.randint(0, self.world_width), random.randint(20, 150)), self.decorations)
        for _ in range(12):
            self._add(Bush(random.randint(0, self.world_width-60), GROUND_Y - 20), self.decorations)

        if level_num == 1:
            for x, y, w, h in [
                (150, 360, 120, 20),
                (350, 300, 120, 20),
                (560, 240, 120, 20),
                (780, 300, 120, 20),
            ]:
                self._add(Platform(x, y, w, h), self.platforms)
            for cx, cy in [(80,440),(200,340),(300,440),(400,280),
                           (520,220),(640,440),(720,280),(860,440)]:
                self._add(Coin(cx, cy), self.coins)
            self._add(QuestionBlock(420, 205, PowerType.FIRE), self.question_blocks)
            self._add(Enemy(260, SPAWN_Y), self.enemies)
            self._add(Enemy(600, SPAWN_Y), self.enemies)

        elif level_num == 2:
            for x, y, w, h in [
                (100, 380, 100, 20),
                (270, 320, 100, 20),
                (450, 260, 100, 20),
                (650, 200, 100, 20),
            ]:
                self._add(Platform(x, y, w, h), self.platforms)
            mp1 = MovingPlatform(280, 360, 100, 20, 160, 1.5)
            mp2 = MovingPlatform(550, 180, 100, 20, 100, 1.5, "vertical")
            self._add(mp1, self.platforms)
            self._add(mp2, self.platforms)
            for cx, cy in [(120,440),(220,300),(340,440),(470,240),(580,160),
                           (700,440),(780,180),(880,440),(930,280),(50,280)]:
                self._add(Coin(cx, cy), self.coins)
            self._add(QuestionBlock(680, 155, PowerType.DOUBLE_JUMP), self.question_blocks)
            self._add(Enemy(200, SPAWN_Y), self.enemies)
            self._add(FlyingEnemy(500, 160), self.enemies)

        elif level_num == 3:
            for x, y, w, h in [
                (100, 380, 120, 20),
                (280, 320, 120, 20),
                (460, 260, 120, 20),
                (640, 200, 120, 20),
            ]:
                self._add(BreakablePlatform(x, y, w, h), self.platforms)
            solid = Platform(800, 240, 130, 20)
            self._add(solid, self.platforms)
            for cx, cy in [(80,440),(160,360),(260,300),(360,440),(440,240),
                           (540,440),(620,180),(700,440),(820,220),(900,440),
                           (950,300),(30,300)]:
                self._add(Coin(cx, cy), self.coins)
            self._add(QuestionBlock(300, 275, PowerType.SPEED),  self.question_blocks)
            self._add(QuestionBlock(820, 195, PowerType.SHIELD), self.question_blocks)
            self._add(BigEnemy(350, GROUND_Y - 48), self.enemies)
            self._add(FlyingEnemy(600, 160), self.enemies)

        elif level_num == 4:
            for x, y, w, h in [
                (150, 380, 180, 20),
                (420, 320, 150, 20),
                (300, 240, 120, 20),
                (580, 180, 120, 20),
                (800, 280, 130, 20),
            ]:
                self._add(Platform(x, y, w, h), self.platforms)
            mp1 = MovingPlatform(80,  300, 100, 20, 200, 2)
            mp2 = MovingPlatform(720, 140, 100, 20, 140, 1.5, "vertical")
            self._add(mp1, self.platforms)
            self._add(mp2, self.platforms)
            for i in range(15):
                cx = 50 + i * 62
                cy = random.choice([200, 280, 360, 440])
                self._add(Coin(cx, cy), self.coins)
            for i, pt in enumerate([PowerType.FIRE, PowerType.DOUBLE_JUMP, PowerType.SPEED]):
                self._add(QuestionBlock(200 + i * 220, 140, pt), self.question_blocks)
            self._add(BigEnemy(430, GROUND_Y - 48), self.enemies)
            self._add(FlyingEnemy(200,  90), self.enemies)
            self._add(Enemy(700, SPAWN_Y), self.enemies)
            self._add(FlyingEnemy(850, 140), self.enemies)
            portal = Portal(930, GROUND_Y - 80, 1)
            self._add(portal, self.portals)

        elif level_num == 5:
            for x, y, w, h in [
                (100, 380, 150, 20),
                (350, 300, 150, 20),
                (600, 220, 150, 20),
                (200, 150, 150, 20),
            ]:
                self._add(Platform(x, y, w, h), self.platforms)
            mp = MovingPlatform(450, 360, 120, 20, 200, 1.8, "horizontal")
            self._add(mp, self.platforms)
            for cx, cy in [(80,440),(250,360),(500,280),(700,200),(850,150)]:
                self._add(Coin(cx, cy), self.coins)
            self._add(QuestionBlock(300, 250, PowerType.FIRE), self.question_blocks)
            self._add(QuestionBlock(650, 170, PowerType.SHIELD), self.question_blocks)
            self.boss = BossEnemy(700, GROUND_Y - 64)
            self._add(self.boss, self.enemies)

        elif level_num == 6:
            # 丛林探险 - 长地图
            # 平台布局
            platforms_data = [
                (150, 380, 100, 20), (350, 340, 100, 20), (550, 300, 100, 20),
                (750, 350, 100, 20), (950, 280, 100, 20), (1150, 320, 100, 20),
                (1350, 250, 100, 20), (1550, 300, 100, 20), (1750, 350, 100, 20),
                (250, 240, 80, 20), (650, 200, 80, 20), (1050, 180, 80, 20),
                (1450, 160, 80, 20), (1700, 200, 80, 20)
            ]
            for x, y, w, h in platforms_data:
                self._add(Platform(x, y, w, h, GREEN), self.platforms)
            
            # 移动平台
            mp1 = MovingPlatform(450, 420, 100, 20, 200, 1.8, "horizontal")
            mp2 = MovingPlatform(1250, 200, 100, 20, 150, 2, "vertical")
            self._add(mp1, self.platforms)
            self._add(mp2, self.platforms)

            # 破碎平台
            self._add(BreakablePlatform(850, 380, 80, 20), self.platforms)
            self._add(BreakablePlatform(1550, 380, 80, 20), self.platforms)

            # 金币（20个）
            coin_positions = [
                (60,440), (200,360), (350,320), (500,420), (650,180),
                (800,440), (950,260), (1100,440), (1250,300), (1400,230),
                (1500,420), (1650,280), (1750,330), (1850,440), (250,220),
                (700,440), (1150,160), (1350,420), (1600,420), (1900,440)
            ]
            for cx, cy in coin_positions:
                self._add(Coin(cx, cy), self.coins)

            # 问号砖块
            self._add(QuestionBlock(200, 300, PowerType.DOUBLE_JUMP), self.question_blocks)
            self._add(QuestionBlock(1050, 135, PowerType.SPEED), self.question_blocks)
            self._add(QuestionBlock(1450, 115, PowerType.FIRE), self.question_blocks)

            # 敌人
            self._add(Enemy(300, SPAWN_Y), self.enemies)
            self._add(Enemy(700, SPAWN_Y), self.enemies)
            self._add(JungleEnemy(1100, SPAWN_Y), self.enemies)
            self._add(JungleEnemy(1600, SPAWN_Y), self.enemies)
            self._add(FlyingEnemy(500, 200), self.enemies)
            self._add(FlyingEnemy(1300, 150), self.enemies)
            self._add(PlantEnemy(450, GROUND_Y), self.enemies)
            self._add(PlantEnemy(1400, GROUND_Y), self.enemies)
            self._add(BigEnemy(1800, GROUND_Y - 48), self.enemies)

            # 传送门（回到第一关）
            portal = Portal(1900, GROUND_Y - 80, 1)
            self._add(portal, self.portals)

        self.game_state = "level_intro"

    def update_camera(self):
        """更新相机位置，使玩家保持在屏幕中央偏左区域"""
        if self.player.rect.centerx > W // 2:
            self.camera_x = self.player.rect.centerx - W // 2
        if self.player.rect.centerx < W // 3:
            self.camera_x = max(0, self.player.rect.centerx - W // 3)
        self.camera_x = max(0, min(self.camera_x, self.world_width - W))

    def update(self):
        if self.next_level is not None:
            self.load_level(self.next_level)
            self.next_level = None
            return

        if self.game_state != "playing":
            return

        self.player.update()

        for p in self.platforms:
            if isinstance(p, MovingPlatform):
                p.update()
        for enemy in self.enemies:
            if isinstance(enemy, BossEnemy):
                enemy.update(self.platforms, self.player, self.fireballs, self.all_sprites)
            else:
                enemy.update(self.platforms)
        for fb in self.fireballs:
            fb.update(self.platforms)
        for coin in self.coins:
            coin.update()
        for deco in self.decorations:
            if isinstance(deco, Cloud):
                deco.update()

        self._move_player()

        # 更新相机
        self.update_camera()

        # 边界限制（相对于世界宽度）
        if self.player.rect.left < 0:
            self.player.rect.left = 0
        if self.player.rect.right > self.world_width:
            self.player.rect.right = self.world_width

        if self.player.rect.top > H:
            self.player_die()
            return

        for coin in pygame.sprite.spritecollide(self.player, self.coins, True):
            self.player.score += coin.value
            self.player.coins += 1
            coin_sound.play()

        for block in pygame.sprite.spritecollide(self.player, self.question_blocks, False):
            if self.player.vel_y < 0 and self.player.rect.top < block.rect.bottom + 5:
                pt = block.hit()
                if pt:
                    self.player.activate_power(pt)

        for enemy in pygame.sprite.spritecollide(self.player, self.enemies, False):
            self.handle_enemy_collision(enemy)

        for fb in list(self.fireballs):
            if fb.is_enemy:
                if fb.rect.colliderect(self.player.rect) and not self.player.invincible:
                    self.player_hit_by_fireball()
                    fb.kill()
            else:
                for enemy in pygame.sprite.spritecollide(fb, self.enemies, False):
                    if isinstance(enemy, BossEnemy):
                        if enemy.hit():
                            self.player.score += 1000
                    elif isinstance(enemy, PlantEnemy):
                        if enemy.hit():
                            self.player.score += 200
                    else:
                        enemy.health -= 1
                        if enemy.health <= 0:
                            enemy.kill()
                            self.player.score += 300
                    fb.kill()
                    break

        for portal in pygame.sprite.spritecollide(self.player, self.portals, False):
            if portal.active:
                teleport_sound.play()
                self.next_level = portal.target_level
                return

        if self.level == 5:
            if self.boss is not None and not self.boss.alive():
                self.game_state = "win"
                return
        else:
            if len(self.coins) == 0 and self.game_state == "playing":
                if self.level < self.max_level:
                    self.next_level = self.level + 1
                else:
                    self.game_state = "win"
                return

        if self.player.lives <= 0:
            self.game_state = "game_over"

    def player_hit_by_fireball(self):
        if self.player.shield_active:
            self.player.shield_active = False
            stomp_sound.play()
        else:
            self.player.lives -= 1
            if self.player.lives > 0:
                self.player.invincible = True
                self.player.invincible_timer = 120
                self.player.rect.x = 50
                self.player.rect.y = SPAWN_Y
                self.player.vel_y = 0
                dead_sound.play()
            else:
                self.game_state = "game_over"

    def _move_player(self):
        p = self.player
        p.rect.x += int(p.vel_x)
        for plat in self.platforms:
            if p.rect.colliderect(plat.rect):
                if p.vel_x > 0:
                    p.rect.right = plat.rect.left
                elif p.vel_x < 0:
                    p.rect.left = plat.rect.right

        p.rect.y += int(p.vel_y)
        p.on_ground = False
        for plat in self.platforms:
            if p.rect.colliderect(plat.rect):
                if p.vel_y > 0:
                    p.rect.bottom = plat.rect.top
                    p.vel_y = 0
                    p.on_ground = True
                    p.jumps_left = 2 if p.power_type == PowerType.DOUBLE_JUMP else 1
                    if isinstance(plat, MovingPlatform) and plat.move_type == "horizontal":
                        delta_x, _ = plat.get_delta()
                        p.rect.x += delta_x
                elif p.vel_y < 0:
                    p.rect.top = plat.rect.bottom
                    p.vel_y = 0
                    if isinstance(plat, BreakablePlatform):
                        if plat.hit():
                            stomp_sound.play()

        if not p.on_ground and p.vel_y >= 0:
            test_rect = p.rect.copy()
            test_rect.y += 8
            for plat in self.platforms:
                if test_rect.colliderect(plat.rect) and p.rect.bottom <= plat.rect.top + 8:
                    p.rect.bottom = plat.rect.top
                    p.vel_y = 0
                    p.on_ground = True
                    p.jumps_left = 2 if p.power_type == PowerType.DOUBLE_JUMP else 1
                    break

    def handle_enemy_collision(self, enemy):
        p = self.player
        if p.invincible:
            return
        if isinstance(enemy, BossEnemy):
            if p.shield_active:
                p.shield_active = False
                stomp_sound.play()
            else:
                p.lives -= 1
                p.invincible = True
                p.invincible_timer = 120
                p.rect.x = 50
                p.rect.y = SPAWN_Y
                p.vel_y = 0
                dead_sound.play()
            return

        if isinstance(enemy, PlantEnemy):
            if p.vel_y > 0 and p.rect.bottom < enemy.rect.centery:
                if enemy.hit():
                    p.score += 200
                p.vel_y = -10
                stomp_sound.play()
            else:
                self._player_hurt()
            return

        if p.vel_y > 0 and p.rect.bottom < enemy.rect.centery:
            enemy.health -= 1
            if enemy.health <= 0:
                enemy.kill()
                p.score += 200
            p.vel_y = -10
            stomp_sound.play()
        else:
            self._player_hurt()

    def _player_hurt(self):
        p = self.player
        if p.shield_active:
            p.shield_active = False
            stomp_sound.play()
        else:
            p.lives -= 1
            p.invincible = True
            p.invincible_timer = 120
            p.rect.x = 50
            p.rect.y = SPAWN_Y
            p.vel_y = 0
            dead_sound.play()

    def player_die(self):
        self.player.lives -= 1
        if self.player.lives > 0:
            dead_sound.play()
            self.next_level = self.level
        else:
            self.game_state = "game_over"

    def draw(self, screen):
        # 绘制背景（滚动）
        if self.background:
            screen.blit(self.background, (-self.camera_x * 0.3, 0))  # 视差效果
        else:
            screen.fill(SKY)

        # 绘制所有精灵（应用相机偏移）
        for sprite in self.all_sprites:
            if (sprite == self.player and
                self.player.invincible and
                pygame.time.get_ticks() % 200 < 100):
                continue
            if isinstance(sprite, BossEnemy) and sprite.invincible:
                if pygame.time.get_ticks() % 100 < 50:
                    continue
            screen.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y))

        for fb in self.fireballs:
            screen.blit(fb.image, (fb.rect.x - self.camera_x, fb.rect.y))

        # UI
        if self.player is not None and self.game_state not in ["menu", "level_intro"]:
            screen.blit(self.font.render(f"Score: {self.player.score}", True, WHITE), (10, 10))
            screen.blit(self.font.render(f"Lives: {self.player.lives}", True, WHITE), (10, 50))
            screen.blit(self.font.render(f"Coins: {self.player.coins}", True, YELLOW), (10, 90))
            screen.blit(self.font.render(f"Level: {self.level}/{self.max_level}", True, WHITE), (W-160, 10))

            power_names = {
                PowerType.FIRE:        "[FIRE]",
                PowerType.DOUBLE_JUMP: "[2-JUMP]",
                PowerType.SPEED:       "[SPEED]",
                PowerType.SHIELD:      "[SHIELD]",
            }
            if self.player.power_type != PowerType.NONE:
                name = power_names.get(self.player.power_type, "")
                screen.blit(self.font.render(name, True, ORANGE), (W - 180, 50))
            if self.player.shield_active:
                screen.blit(self.font.render("[SHIELD]", True, BLUE), (W - 180, 80))

            if self.level == 5 and self.boss is not None and self.boss.alive():
                bar_width = 400
                bar_height = 20
                bar_x = W//2 - bar_width//2
                bar_y = 30
                pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
                health_width = int(bar_width * (self.boss.health / self.boss.max_health))
                pygame.draw.rect(screen, GREEN, (bar_x, bar_y, health_width, bar_height))
                pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 2)
                boss_text = self.font.render("BOSS", True, RED)
                screen.blit(boss_text, (bar_x - 70, bar_y - 5))

        if self.game_state == "menu":
            self.draw_menu(screen)
        elif self.game_state == "level_intro":
            self.draw_level_intro(screen)
        elif self.game_state == "paused":
            self._draw_center_text("PAUSED", self.big_font, WHITE, H//2 - 50)
            self._draw_center_text("P: Resume   R: Restart", self.font, WHITE, H//2 + 20)
        elif self.game_state == "game_over":
            self._draw_center_text("GAME OVER", self.big_font, RED, H//2 - 50)
            self._draw_center_text("Press R to Restart", self.font, WHITE, H//2 + 20)
        elif self.game_state == "win":
            self._draw_center_text("YOU WIN!", self.big_font, YELLOW, H//2 - 60)
            if self.player is not None:
                self._draw_center_text(f"Final Score: {self.player.score}", self.font, WHITE, H//2 + 10)
            self._draw_center_text("Press R to Restart", self.font, WHITE, H//2 + 55)

    def draw_menu(self, screen):
        screen.blit(self.menu_background, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        title = self.big_font.render("SUPER MARIO ULTIMATE", True, YELLOW)
        screen.blit(title, (W//2 - title.get_width()//2, 50))

        level_names = [
            "1 - Grass Land",
            "2 - Volcano",
            "3 - Ice Mountain",
            "4 - Ocean",
            "5 - Boss Castle",
            "6 - Jungle Expedition"
        ]

        start_y = 120
        for i, name in enumerate(level_names):
            color = YELLOW if i == self.menu_selection else WHITE
            text = self.font.render(name, True, color)
            x = W//2 - text.get_width()//2
            y = start_y + i * 45
            screen.blit(text, (x, y))
            if i == self.menu_selection:
                pygame.draw.rect(screen, YELLOW, (x-20, y-5, text.get_width()+40, text.get_height()+10), 3)

        hint1 = self.font.render("Use UP/DOWN to select, ENTER to start", True, WHITE)
        hint2 = self.font.render("Press R to restart game anytime", True, WHITE)
        screen.blit(hint1, (W//2 - hint1.get_width()//2, H - 100))
        screen.blit(hint2, (W//2 - hint2.get_width()//2, H - 60))

    def _draw_center_text(self, text, font, color, y):
        surf = font.render(text, True, color)
        screen.blit(surf, (W//2 - surf.get_width()//2, y))

    def draw_level_intro(self, screen):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))
        title_surf = self.big_font.render(f"Level  {self.level}", True, YELLOW)
        screen.blit(title_surf, (W//2 - title_surf.get_width()//2, 40))

        intro_lines = {
            1: ["--- Basic Stage ---", "", "LEFT / RIGHT : Move", "SPACE : Jump",
                "F : Shoot fireball (after power-up)", "", "Collect ALL coins to clear!",
                "Hit '?' block to get FIRE power.", "Stomp enemies from above."],
            2: ["--- Moving Platforms ---", "", "Blue platforms move.",
                "Stand on them to ride.", "Hit '?' block for DOUBLE-JUMP.",
                "Press SPACE again mid-air for 2nd jump.", "", "Watch out for flying enemies!"],
            3: ["--- Breakable Platforms ---", "", "Brown platforms break after 2 hits.",
                "Don't fall!", "'?' blocks give SPEED and SHIELD.",
                "SHIELD absorbs one hit.", "Big enemy requires 3 stomps."],
            4: ["--- Ocean Stage ---", "", "The deep blue sea!",
                "Collect ALL coins to proceed.", "Portal can take you back to Level 1.",
                "Watch out for enemies!"],
            5: ["--- BOSS STAGE ---", "", "Defeat the BOSS to win!",
                "All power-ups are PERMANENT in this stage!",
                "Use fireballs and avoid his attacks.",
                "Good luck, hero!"],
            6: ["--- Jungle Expedition ---", "", "A long journey through the jungle!",
                "New enemies: Jungle Spiders and Piranha Plants.",
                "Find all 20 coins to complete the stage.",
                "Use moving platforms wisely.",
                "Watch your step!"]
        }
        lines = intro_lines.get(self.level, [])
        y = 130
        for line in lines:
            surf = self.font.render(line, True, WHITE)
            screen.blit(surf, (W//2 - surf.get_width()//2, y))
            y += 34
        if pygame.time.get_ticks() % 1000 < 700:
            prompt = self.font.render(">>> Press any key to start <<<", True, YELLOW)
            screen.blit(prompt, (W//2 - prompt.get_width()//2, H - 70))

    def reset(self):
        self.level = 1
        self.menu_selection = 0
        self.game_state = "menu"
        self.next_level = None
        self.player = None
        self.boss = None
        self.camera_x = 0
        for g in [self.all_sprites, self.platforms, self.coins, self.enemies,
                  self.fireballs, self.decorations, self.question_blocks, self.portals]:
            g.empty()

# ====================== 主循环 ======================
def main():
    game = Game()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset()
                    pygame.event.clear()
                    continue

                if game.game_state == "menu":
                    if event.key == pygame.K_UP:
                        game.menu_selection = (game.menu_selection - 1) % 6
                        menu_select_sound.play()
                    elif event.key == pygame.K_DOWN:
                        game.menu_selection = (game.menu_selection + 1) % 6
                        menu_select_sound.play()
                    elif event.key == pygame.K_RETURN:
                        selected_level = game.menu_selection + 1
                        game.load_level(selected_level)
                        game.game_state = "level_intro"
                        continue
                    continue

                if event.key == pygame.K_p:
                    if game.game_state == "playing":
                        game.game_state = "paused"
                    elif game.game_state == "paused":
                        game.game_state = "playing"
                    continue

                if game.game_state == "level_intro":
                    game.game_state = "playing"
                    continue

                if game.game_state == "playing":
                    if event.key == pygame.K_SPACE:
                        p = game.player
                        if p.on_ground:
                            p.vel_y = -p.jump_power
                            p.on_ground = False
                            jump_sound.play()
                        elif (p.power_type == PowerType.DOUBLE_JUMP and p.jumps_left > 0):
                            p.vel_y = -p.jump_power
                            p.jumps_left -= 1
                            jump_sound.play()
                    if event.key == pygame.K_f:
                        fb = game.player.shoot_fireball()
                        if fb:
                            game.fireballs.add(fb)
                            game.all_sprites.add(fb)
                    if event.key == pygame.K_LSHIFT and game.player.power_type == PowerType.SPEED:
                        game.player.speed = 12

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LSHIFT:
                    if game.player is not None:
                        game.player.speed = 10 if game.player.power_type == PowerType.SPEED else game.player.base_speed

        if game.game_state == "playing":
            keys = pygame.key.get_pressed()
            if game.player is not None:
                game.player.vel_x = 0
                if keys[pygame.K_LEFT]:
                    game.player.vel_x = -game.player.speed
                if keys[pygame.K_RIGHT]:
                    game.player.vel_x = game.player.speed

        game.update()
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()