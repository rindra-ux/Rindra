import pygame
import random
import math
import os
import sys
import json
import asyncio

# ================= INIT =================
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
WIDTH, HEIGHT = 420, 720
SCREEN_W, SCREEN_H = 420, 720
flags = pygame.SCALED | pygame.RESIZABLE
real_screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
screen = pygame.Surface((WIDTH, HEIGHT)) # Virtual Surface that scales
pygame.display.set_caption("Space Meteor Hunter 🚀")
clock = pygame.time.Clock()

# ================= ASSET PATH =================
def asset_path(filename):
    base = os.path.dirname(os.path.abspath(__file__))
    for p in [os.path.join(base, "assets", filename), os.path.join(base, filename)]:
        if os.path.exists(p):
            return p
    return os.path.join(base, "assets", filename)

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save.json")

def load_high_score():
    try:
        with open(SAVE_FILE, "r") as f:
            return json.load(f).get("high_score", 0)
    except Exception:
        return 0

def save_high_score(hs):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump({"high_score": hs}, f)
    except Exception:
        pass

# ================= LOAD ASSETS =================
heart_img = pygame.image.load(asset_path("heart.png")).convert_alpha()
heart_img = pygame.transform.scale(heart_img, (28, 28))
rocket_img = pygame.image.load(asset_path("rocket.png")).convert_alpha()
rocket_img = pygame.transform.scale(rocket_img, (48, 56))
meteor_img_base = pygame.image.load(asset_path("meteor.png")).convert_alpha()

meteor_cache = {}
def get_meteor_img(size):
    sz = max(4, size * 2)
    if sz not in meteor_cache:
        meteor_cache[sz] = pygame.transform.scale(meteor_img_base, (sz, sz))
    return meteor_cache[sz]

# Tinted meteor images per type
tinted_meteor_cache = {}
def get_tinted_meteor(size, tint):
    key = (size * 2, tint)
    if key not in tinted_meteor_cache:
        img = get_meteor_img(size).copy()
        tint_surf = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        tint_surf.fill((*tint, 80))
        img.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        tinted_meteor_cache[key] = img
    return tinted_meteor_cache[key]

# ================= GENERATE SOUNDS =================
def gen_sound(freq, ms, vol=0.3, wave="square"):
    sr = 22050
    n = int(sr * ms / 1000)
    buf = bytearray()
    for i in range(n):
        t = i / sr
        if wave == "square":
            v = 32767 if math.sin(2*math.pi*freq*t) > 0 else -32767
        elif wave == "noise":
            v = random.randint(-32767, 32767)
        else:
            v = int(32767 * math.sin(2*math.pi*freq*t))
        v = int(v * vol)
        b = v.to_bytes(2, byteorder='little', signed=True)
        buf += b + b
    return pygame.mixer.Sound(buffer=bytes(buf))

shoot_sfx     = gen_sound(880,  60,  0.12, "square")
hit_sfx       = gen_sound(220,  150, 0.20, "noise")
explode_sfx   = gen_sound(120,  200, 0.18, "noise")
powerup_sfx   = gen_sound(1200, 120, 0.18, "sine")
gameover_sfx  = gen_sound(150,  500, 0.25, "sine")
levelup_sfx   = gen_sound(660,  100, 0.14, "sine")
combo_sfx     = gen_sound(1000, 50,  0.10, "square")
boss_sfx      = gen_sound(80,   400, 0.22, "noise")
warning_sfx   = gen_sound(440,  200, 0.18, "square")
laser_sfx     = gen_sound(300,  80,  0.14, "square")
dash_sfx      = gen_sound(600,  80,  0.12, "sine")
nuke_sfx      = gen_sound(80,   350, 0.28, "noise")
slowmo_sfx    = gen_sound(200,  120, 0.12, "sine")
boss_shoot_sfx= gen_sound(500,  80,  0.10, "square")
bomb_sfx      = gen_sound(60,   400, 0.30, "noise")
weapon_up_sfx = gen_sound(900,  150, 0.18, "sine")
shower_sfx    = gen_sound(300,  200, 0.15, "noise")

# ================= COLORS =================
WHITE       = (255, 255, 255)
YELLOW      = (255, 220, 100)
RED         = (255, 80,  80)
CYAN        = (0,   220, 255)
GREEN       = (80,  255, 120)
ORANGE      = (255, 160, 40)
PURPLE      = (180, 80,  255)
LIGHT_PURPLE= (220, 150, 255)
MAGENTA     = (255, 50,  200)
DARK_BG     = (5,   5,   20)
BLUE        = (60,  120, 255)
PINK        = (255, 100, 180)

# Meteor type palettes
METEOR_COLORS = {
    "normal":  None,
    "fast":    (255, 180, 50),   # orange tint
    "tanky":   (100, 50,  180),  # purple tint
    "zigzag":  (50,  220, 200),  # teal tint
    "splitter":(255, 60,  60),   # red tint
}
SPARK_COLORS = {
    "normal":  [PURPLE, LIGHT_PURPLE, MAGENTA, (150,60,230)],
    "fast":    [YELLOW, ORANGE, (255,220,50)],
    "tanky":   [BLUE,   CYAN,   (80,80,255)],
    "zigzag":  [CYAN,   GREEN,  (50,255,200)],
    "splitter":[RED,    ORANGE, PINK],
}

# ================= FONTS =================
font_tiny  = pygame.font.SysFont("consolas", 12, bold=True)
font_small = pygame.font.SysFont("consolas", 16, bold=True)
font_med   = pygame.font.SysFont("consolas", 22, bold=True)
font_large = pygame.font.SysFont("consolas", 36, bold=True)
font_title = pygame.font.SysFont("consolas", 42, bold=True)
font_combo = pygame.font.SysFont("consolas", 28, bold=True)

# ================= GAME STATE =================
STATE_MENU     = 0
STATE_PLAYING  = 1
STATE_GAME_OVER= 2
STATE_PAUSED   = 3
game_state = STATE_MENU
high_score = load_high_score()
frame_count = 0

# Transitions
transition_timer = 0
transition_state = None
transition_alpha = 0
is_transitioning = False

def start_transition(next_state):
    global is_transitioning, transition_timer, transition_state, transition_alpha
    if not is_transitioning:
        is_transitioning = True
        transition_timer = 30 # half second fade out
        transition_state = next_state
        transition_alpha = 0

def update_draw_transition():
    global is_transitioning, transition_timer, transition_state, game_state, transition_alpha
    if not is_transitioning: return
    
    fs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    if transition_timer > 0:
        # Fading to black
        transition_timer -= 1
        transition_alpha = min(255, int(255 * (1.0 - transition_timer/30)))
        if transition_timer <= 0:
            # Swap state
            game_state = transition_state
            if game_state == STATE_PLAYING: reset_game()
            transition_timer = -30 # Fade back in
    else:
        # Fading from black
        transition_timer += 1
        transition_alpha = max(0, int(255 * abs(transition_timer/30)))
        if transition_timer >= 0:
            is_transitioning = False
            return
            
    pygame.draw.rect(fs, (0,0,0, transition_alpha), (0,0,WIDTH,HEIGHT))
    screen.blit(fs, (0,0))

# ================= STARS (3-LAYER PARALLAX) =================
stars_bg = [] # Far, slow, dark
stars_md = [] # Mid, medium, gray
stars_fg = [] # Near, fast, white

for _ in range(80): stars_bg.append([random.randint(0, WIDTH), random.randint(0, HEIGHT)])
for _ in range(50): stars_md.append([random.randint(0, WIDTH), random.randint(0, HEIGHT)])
for _ in range(30): stars_fg.append([random.randint(0, WIDTH), random.randint(0, HEIGHT)])

# Parallax nebula layers
nebula_layers = [
    {"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT//2),
     "r": random.randint(60, 120), "color": (100, 40, 180), "speed": 0.1}
    for _ in range(6)
]

def draw_background():
    # Shift bg color based on level
    bg_r = min(20, 5 + level)
    bg_g = min(10, 5 + level // 3)
    bg_b = min(40, 20 + level)
    screen.fill((bg_r, bg_g, bg_b))

    # Scrolling nebula blobs
    for nb in nebula_layers:
        nb["y"] += nb["speed"]
        if nb["y"] > HEIGHT + nb["r"]:
            nb["y"] = -nb["r"]
            nb["x"] = random.randint(0, WIDTH)
        ns = pygame.Surface((nb["r"]*2, nb["r"]*2), pygame.SRCALPHA)
        pulse = int(abs(math.sin(frame_count/60 + nb["x"])) * 10)
        pygame.draw.circle(ns, (*nb["color"], 18 + pulse), (nb["r"], nb["r"]), nb["r"])
        screen.blit(ns, (int(nb["x"]-nb["r"]), int(nb["y"]-nb["r"])))

    # Parallax Stars
    # Layer 1: Background (slowest)
    for s in stars_bg:
        s[1] += 0.3
        if s[1] > HEIGHT: s[1] = 0; s[0] = random.randint(0, WIDTH)
        col = (80,80,100) if random.random() > 0.05 else (150,150,180) # Twinkle
        pygame.draw.circle(screen, col, (int(s[0]), int(s[1])), 1)

    # Layer 2: Midground
    for s in stars_md:
        s[1] += 0.8
        if s[1] > HEIGHT: s[1] = 0; s[0] = random.randint(0, WIDTH)
        col = (140,140,170) if random.random() > 0.05 else (200,200,255) # Twinkle
        pygame.draw.circle(screen, col, (int(s[0]), int(s[1])), 2)

    # Layer 3: Foreground (fastest)
    for s in stars_fg:
        s[1] += 1.8
        if s[1] > HEIGHT: s[1] = 0; s[0] = random.randint(0, WIDTH)
        col = (220,220,255) if random.random() > 0.05 else (255,255,255) # Twinkle
        pygame.draw.circle(screen, col, (int(s[0]), int(s[1])), 2)

# ================= UI UTILS =================
def draw_text_shadow(surface, text, font, color, x, y, shadow_col=(0,0,0), offset=2):
    """Draw text with a drop shadow for professional contrast."""
    sh = font.render(text, True, shadow_col)
    surface.blit(sh, (x+offset, y+offset))
    tx = font.render(text, True, color)
    surface.blit(tx, (x, y))

# ================= PARTICLES =================
particles     = []
score_popups  = []
trail_points  = []   # player movement trail

def spawn_explosion(x, y, color=(255,140,40), count=15):
    for _ in range(count):
        a = random.uniform(0, math.pi*2)
        s = random.uniform(1.5, 6)
        particles.append({"x":x,"y":y,"vx":math.cos(a)*s,"vy":math.sin(a)*s,
                           "size":random.uniform(2,5),"lifetime":random.randint(15,35),
                           "max_life":35,"color":color,"type":"normal"})

def spawn_sparks(x, y, size, mtype="normal"):
    colors = SPARK_COLORS.get(mtype, SPARK_COLORS["normal"])
    for _ in range(3):
        a = random.uniform(0, math.pi*2)
        d = random.uniform(size*0.4, size*1.0)
        c = random.choice(colors)
        particles.append({"x":x+math.cos(a)*d,"y":y+math.sin(a)*d,
                           "vx":random.uniform(-1,1),"vy":random.uniform(-0.5,1.5),
                           "size":random.uniform(1.5,3.5),"lifetime":random.randint(10,25),
                           "max_life":25,"color":c,"type":"spark"})

def spawn_trail_particle(x, y, size, mtype="normal"):
    c = random.choice(SPARK_COLORS.get(mtype, SPARK_COLORS["normal"]))
    particles.append({"x":x+random.uniform(-size*0.3,size*0.3),"y":y-size*0.6,
                      "vx":random.uniform(-0.3,0.3),"vy":random.uniform(-1.5,-0.5),
                      "size":random.uniform(2,4),"lifetime":random.randint(10,20),
                      "max_life":20,"color":c,"type":"trail"})

def spawn_thruster(x, y):
    for _ in range(2):
        particles.append({"x":x+random.uniform(-6,6),"y":y,
                          "vx":random.uniform(-0.5,0.5),"vy":random.uniform(1,3),
                          "size":random.uniform(2,4),"lifetime":random.randint(8,16),
                          "max_life":16,"color":random.choice([(255,200,50),(255,120,20),(255,80,10)]),
                          "type":"normal"})

def add_player_trail(x, y, moving):
    """Ekor biru di belakang roket saat bergerak."""
    if moving and random.random() < 0.5:
        trail_points.append({"x":x,"y":y+22,"lifetime":12,"max_life":12})

def update_particles():
    for p in particles[:]:
        p["x"] += p["vx"]; p["y"] += p["vy"]; p["lifetime"] -= 1
        if p["lifetime"] <= 0: particles.remove(p); continue
        a = p["lifetime"] / p["max_life"]
        r,g,b = p["color"]
        col = (int(r*a), int(g*a), int(b*a))
        if p["type"] == "spark":
            sz = max(1, int(p["size"]*(0.5+a*0.5)))
            glow = (int(r*a*0.3), int(g*a*0.3), int(b*a*0.3))
            if sz>=2: pygame.draw.circle(screen, glow, (int(p["x"]),int(p["y"])), sz+2)
            pygame.draw.circle(screen, col, (int(p["x"]),int(p["y"])), sz)
        else:
            pygame.draw.circle(screen, col, (int(p["x"]),int(p["y"])), max(1,int(p["size"]*a)))

def update_trail():
    for t in trail_points[:]:
        t["lifetime"] -= 1
        if t["lifetime"] <= 0: trail_points.remove(t); continue
        a = t["lifetime"] / t["max_life"]
        c = (int(100*a), int(200*a), int(255*a))
        pygame.draw.circle(screen, c, (int(t["x"]), int(t["y"])), max(1, int(4*a)))

def spawn_score_popup(x, y, text, color=YELLOW):
    score_popups.append({"x":x,"y":y,"text":text,"color":color,"lifetime":50,"max_life":50})

def update_score_popups():
    for sp in score_popups[:]:
        sp["y"] -= 1.2; sp["lifetime"] -= 1
        if sp["lifetime"] <= 0: score_popups.remove(sp); continue
        a = sp["lifetime"] / sp["max_life"]
        r,g,b = sp["color"]
        col = (int(r*a), int(g*a), int(b*a))
        t = font_small.render(sp["text"], True, col)
        screen.blit(t, (int(sp["x"])-t.get_width()//2, int(sp["y"])))

# ================= SCREEN EFFECTS =================
shake_timer = 0; shake_intensity = 0
flash_timer = 0; flash_color = (255,0,0)
hit_stop_frames = 0 # Freeze frames for game juice

def trigger_hit_stop(frames):
    global hit_stop_frames
    hit_stop_frames = max(hit_stop_frames, frames)

def trigger_shake(i=6, d=12):
    global shake_timer, shake_intensity
    shake_timer = d; shake_intensity = i

def get_shake():
    global shake_timer
    if shake_timer > 0:
        shake_timer -= 1
        return random.randint(-shake_intensity, shake_intensity), random.randint(-shake_intensity, shake_intensity)
    return 0, 0

def trigger_flash(color=(255,0,0), duration=8):
    global flash_timer, flash_color
    flash_timer = duration; flash_color = color

def draw_flash():
    global flash_timer
    if flash_timer > 0:
        flash_timer -= 1
        alpha = min(255, max(0, int(180 * flash_timer / 8)))
        fs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fs.fill((*flash_color, alpha))
        screen.blit(fs, (0,0))

# ================= ACHIEVEMENTS =================
achievements = []  # {"text": ..., "lifetime": ...}

def push_achievement(text, color=YELLOW):
    achievements.append({"text": text, "color": color, "lifetime": 120, "y_off": 0})

def draw_achievements():
    y = 90
    for ac in achievements[:]:
        ac["lifetime"] -= 1
        if ac["lifetime"] <= 0:
            achievements.remove(ac)
            continue
        a = min(1.0, ac["lifetime"] / 40)
        r,g,b = ac["color"]
        col = (int(r*a), int(g*a), int(b*a))
        t = font_small.render(f"★ {ac['text']}", True, col)
        # Draw background pill
        bg = pygame.Surface((t.get_width()+16, t.get_height()+6), pygame.SRCALPHA)
        bg.fill((0,0,0,int(120*a)))
        screen.blit(bg, (WIDTH//2 - bg.get_width()//2, y-3))
        screen.blit(t, (WIDTH//2 - t.get_width()//2, y))
        y += t.get_height() + 10

# ================= POWER-UPS =================
POWER_RAPID  = "rapid"
POWER_SHIELD = "shield"
POWER_LIFE   = "life"
POWER_SPREAD = "spread"
POWER_MAGNET = "magnet"
POWER_LASER  = "laser"
POWER_NUKE   = "nuke"
POWER_SLOWMO = "slowmo"

power_up_defs = {
    POWER_RAPID:  {"color": YELLOW,  "symbol": "R", "duration": 300, "name": "RAPID FIRE"},
    POWER_SHIELD: {"color": CYAN,    "symbol": "S", "duration": 360, "name": "SHIELD"},
    POWER_LIFE:   {"color": RED,     "symbol": "+", "duration": 0,   "name": "EXTRA LIFE"},
    POWER_SPREAD: {"color": ORANGE,  "symbol": "W", "duration": 360, "name": "SPREAD SHOT"},
    POWER_MAGNET: {"color": GREEN,   "symbol": "M", "duration": 420, "name": "MAGNET"},
    POWER_LASER:  {"color": MAGENTA, "symbol": "L", "duration": 180, "name": "LASER"},
    POWER_NUKE:   {"color": (255,80,40),  "symbol": "N", "duration": 0,   "name": "NUKE!"},
    POWER_SLOWMO: {"color": (80,180,255), "symbol": "T", "duration": 360, "name": "SLOW-MO"},
}

# ================= GAME VARIABLES =================
def reset_game():
    global player_pos, player_speed, lives, max_lives, score, level
    global bullets, enemy_bullets, meteors, powerups, particles, score_popups, trail_points
    global shoot_cooldown, meteor_timer, level_timer, invincible_timer
    global active_powers, difficulty_mult
    global combo_count, combo_timer, total_kills, boss_spawned
    global wave_warning_timer, danger_flash, last_kill_time
    global achievements, kill_streak
    global dash_cooldown, dash_timer, dash_dx, dash_dy

    player_pos = [WIDTH//2, HEIGHT-80]
    player_speed = 5
    lives = 3; max_lives = 7
    score = 0; level = 1
    bullets = []; enemy_bullets = []; meteors = []; powerups = []
    particles.clear(); score_popups.clear(); trail_points.clear()
    achievements.clear()
    shoot_cooldown = 0; meteor_timer = 0; level_timer = 0; invincible_timer = 0
    active_powers = {POWER_RAPID:0, POWER_SHIELD:0, POWER_SPREAD:0,
                     POWER_MAGNET:0, POWER_LASER:0, POWER_SLOWMO:0}
    difficulty_mult = 1.0
    combo_count = 0; combo_timer = 0; total_kills = 0; boss_spawned = False
    wave_warning_timer = 0; danger_flash = 0; last_kill_time = 0
    kill_streak = 0
    # XP / Weapon tier
    global xp, weapon_tier, xp_thresholds
    xp = 0; weapon_tier = 1
    # Bomb
    global bomb_count, bomb_timer
    bomb_count = 3; bomb_timer = 0
    # Comets
    global comets
    comets.clear()
    # Meteor shower
    global shower_timer, shower_active
    shower_timer = random.randint(600, 1200); shower_active = 0

# Initial vars
player_pos = [WIDTH//2, HEIGHT-80]; player_speed = 5
lives = 3; max_lives = 7; score = 0; level = 1
bullets = []; enemy_bullets = []; meteors = []; powerups = []
shoot_cooldown = 0; meteor_timer = 0; level_timer = 0; invincible_timer = 0
active_powers = {POWER_RAPID:0, POWER_SHIELD:0, POWER_SPREAD:0,
                 POWER_MAGNET:0, POWER_LASER:0, POWER_SLOWMO:0}
difficulty_mult = 1.0; combo_count = 0; combo_timer = 0; total_kills = 0; boss_spawned = False
wave_warning_timer = 0; danger_flash = 0; last_kill_time = 0
kill_streak = 0
# XP / Weapon tier
XP_THRESHOLDS = [10, 25, 50]   # kills to reach tier 2, tier 3 (cap)
xp = 0; weapon_tier = 1
# Bomb
bomb_count = 3; bomb_timer = 0
# Comets
comets = []   # horizontal fast enemies
# Meteor shower event
shower_timer = random.randint(600, 1200); shower_active = 0

# ================= SHOOT =================
def shoot():
    cy = player_pos[1] - 28
    if active_powers[POWER_LASER] > 0:
        bullets.append({"x": player_pos[0], "y": cy, "vx": 0, "vy": -22, "type": "laser"})
        laser_sfx.play()
    elif active_powers[POWER_SPREAD] > 0:
        for ao in [-14, -7, 0, 7, 14]:
            rad = math.radians(ao)
            bullets.append({"x": player_pos[0], "y": cy,
                             "vx": math.sin(rad)*5, "vy": -12, "type": "normal"})
        shoot_sfx.play()
    else:
        # weapon_tier: 1=single, 2=double, 3=triple
        offsets = [0] if weapon_tier == 1 else [-10, 10] if weapon_tier == 2 else [-20, 0, 20]
        for ox in offsets:
            bullets.append({"x": player_pos[0]+ox, "y": cy, "vx": ox*0.1, "vy": -12, "type": "normal"})
        shoot_sfx.play()

# ================= SPAWN METEOR =================
METEOR_TYPES = ["normal", "normal", "normal", "fast", "fast", "tanky", "zigzag", "splitter"]

def spawn_meteor(is_boss=False, mtype=None):
    if is_boss:
        sz = random.randint(50, 65)
        spd = random.uniform(0.8, 1.4) * difficulty_mult
        hp = 8 + level
        meteors.append({"x": random.randint(70, WIDTH-70), "y": -80,
                         "size": sz, "speed": spd, "base_speed": spd,
                         "timer": random.randint(30,80), "hp": hp, "max_hp": hp,
                         "is_boss": True, "type": "boss", "spark_timer": 0,
                         "vx": 0, "zigzag_phase": 0})
        boss_sfx.play()
        push_achievement("BOSS INCOMING!", MAGENTA)
    else:
        # Difficulty biases certain types at higher levels
        pool = ["normal"]*4 + ["fast"]*max(0, level-1) + ["tanky"]*max(0,(level-2)//2) \
               + ["zigzag"]*max(0,(level-3)//2) + ["splitter"]*max(0,(level-4)//2)
        t = mtype or random.choice(pool)

        if t == "fast":
            sz = random.randint(10, 20)
            spd = random.uniform(3.5, 6.0) * difficulty_mult
            hp = 1
        elif t == "tanky":
            sz = random.randint(34, 46)
            spd = random.uniform(0.8, 1.8) * difficulty_mult
            hp = 4 + level // 2
        elif t == "zigzag":
            sz = random.randint(16, 28)
            spd = random.uniform(2.0, 3.5) * difficulty_mult
            hp = 1
        elif t == "splitter":
            sz = random.randint(22, 34)
            spd = random.uniform(1.5, 3.0) * difficulty_mult
            hp = 2
        else:  # normal
            sz = random.randint(18, 35)
            spd = random.uniform(1.5, 3.5) * difficulty_mult
            hp = 1 if sz < 28 else 2

        meteors.append({"x": random.randint(sz, WIDTH-sz), "y": -sz*2,
                         "size": sz, "speed": spd, "base_speed": spd,
                         "timer": random.randint(30,120), "hp": hp, "max_hp": hp,
                         "is_boss": False, "type": t, "spark_timer": 0,
                         "vx": 0, "zigzag_phase": random.uniform(0, math.pi*2)})

def split_meteor(m):
    """Splitter meteor pecah jadi 2 yang lebih kecil."""
    for _ in range(2):
        new_sz = max(8, m["size"]//2)
        side = random.choice([-1, 1])
        meteors.append({"x": m["x"]+side*new_sz, "y": m["y"],
                         "size": new_sz, "speed": m["base_speed"]*1.3,
                         "base_speed": m["base_speed"]*1.3,
                         "timer": 60, "hp": 1, "max_hp": 1,
                         "is_boss": False, "type": "normal", "spark_timer": 0,
                         "vx": side*1.5, "zigzag_phase": 0})

# ================= COMET (horizontal enemy) =================
COMET_COLOR = (255, 220, 80)

def spawn_comet():
    side = random.choice([-1, 1])
    x = -40 if side == 1 else WIDTH + 40
    y = random.randint(80, HEIGHT // 2)
    spd = random.uniform(4, 8) * side * difficulty_mult
    comets.append({"x": float(x), "y": float(y), "vx": spd, "vy": random.uniform(-1,1),
                   "size": random.randint(12, 22), "pulse": 0.0})

def update_draw_comets():
    global score, total_kills, xp, weapon_tier, kill_streak
    for c in comets[:]:
        c["x"] += c["vx"]; c["y"] += c["vy"]; c["pulse"] += 0.15
        sz = c["size"]
        # Trail
        for _ in range(3):
            particles.append({"x": c["x"]-c["vx"]*random.uniform(0,1),
                               "y": c["y"]+random.uniform(-4,4),
                               "vx":random.uniform(-0.3,0.3), "vy":random.uniform(-0.5,0.5),
                               "size":random.uniform(2,4), "lifetime":12,"max_life":12,
                               "color":COMET_COLOR, "type":"trail"})
        # Draw
        glow = pygame.Surface((sz*3,sz*3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*COMET_COLOR, 40), (sz*3//2,sz*3//2), sz*3//2)
        screen.blit(glow, (int(c["x"])-sz*3//2, int(c["y"])-sz*3//2))
        pygame.draw.circle(screen, COMET_COLOR, (int(c["x"]),int(c["y"])), sz)
        pygame.draw.circle(screen, WHITE, (int(c["x"]),int(c["y"])), sz//2)

        # Off screen
        if c["x"] < -100 or c["x"] > WIDTH+100:
            comets.remove(c); continue

        # Bullet hit
        for b in bullets[:]:
            if math.hypot(c["x"]-b["x"], c["y"]-b["y"]) < sz+4:
                if b in bullets: bullets.remove(b)
                spawn_explosion(c["x"], c["y"], COMET_COLOR, 18)
                spawn_score_popup(c["x"], c["y"], f"+{30*level}", COMET_COLOR)
                score += 30 * level
                xp += 2; total_kills += 1; kill_streak += 1
                _check_weapon_tier()
                if c in comets: comets.remove(c)
                explode_sfx.play()
                break

        # Player collision
        if c in comets and invincible_timer <= 0:
            if math.hypot(c["x"]-player_pos[0], c["y"]-player_pos[1]) < sz+18:
                comets.remove(c)
                _on_player_hit()

def _on_player_hit():
    """Shared player damage logic."""
    global lives, invincible_timer, kill_streak, game_state, high_score
    kill_streak = 0
    if active_powers[POWER_SHIELD] > 0:
        active_powers[POWER_SHIELD] = 0
        trigger_flash(CYAN, 8); hit_sfx.play()
    else:
        lives -= 1; invincible_timer = 120
        trigger_shake(8, 15); trigger_flash(RED, 10)
        spawn_explosion(player_pos[0], player_pos[1], RED, 25)
        hit_sfx.play()
        if lives <= 0:
            gameover_sfx.play()
            if score > high_score:
                high_score = score; save_high_score(high_score)
            game_state = STATE_GAME_OVER

# ================= BOMB =================
def bomb_detonate():
    global bomb_count, score, total_kills, xp
    if bomb_count <= 0: return
    bomb_count -= 1
    radius = 160
    # Kill all meteors in radius
    killed = 0
    for m in meteors[:]:
        if math.hypot(m["x"]-player_pos[0], m["y"]-player_pos[1]) < radius + m["size"]:
            spawn_explosion(m["x"], m["y"], METEOR_COLORS.get(m["type"]) or (255,140,40), 15)
            score += 8 * level; killed += 1; xp += 1; total_kills += 1
            meteors.remove(m)
    for c in comets[:]:
        if math.hypot(c["x"]-player_pos[0], c["y"]-player_pos[1]) < radius:
            spawn_explosion(c["x"], c["y"], COMET_COLOR, 12)
            score += 25 * level; comets.remove(c)
    # Big explosion ring
    spawn_explosion(player_pos[0], player_pos[1], (255,200,80), 40)
    spawn_explosion(player_pos[0], player_pos[1], WHITE, 15)
    trigger_shake(14, 25); trigger_flash((255,200,50), 15)
    bomb_sfx.play()
    if killed > 0:
        push_achievement(f"BOMB! {killed} KILLED", (255,200,50))
        _check_weapon_tier()

def _check_weapon_tier():
    global xp, weapon_tier
    if weapon_tier < 2 and xp >= XP_THRESHOLDS[0]:
        weapon_tier = 2
        push_achievement("WEAPON UPGRADE! DBL SHOT", YELLOW)
        weapon_up_sfx.play()
    elif weapon_tier < 3 and xp >= XP_THRESHOLDS[1]:
        weapon_tier = 3
        push_achievement("WEAPON MAX! TRIPLE SHOT", ORANGE)
        weapon_up_sfx.play()

def draw_xp_bar():
    """XP bar at bottom-right + weapon tier indicator."""
    max_xp = XP_THRESHOLDS[min(weapon_tier-1, len(XP_THRESHOLDS)-1)]
    cur_xp  = min(xp, max_xp)
    bw = 80; bh = 8
    bx = WIDTH - bw - 8; by = HEIGHT - 22
    pygame.draw.rect(screen, (30,30,50), (bx-1, by-1, bw+2, bh+2), border_radius=3)
    fill = int(bw * cur_xp / max_xp) if max_xp > 0 else bw
    bar_col = YELLOW if weapon_tier == 1 else ORANGE if weapon_tier == 2 else MAGENTA
    pygame.draw.rect(screen, bar_col, (bx, by, fill, bh), border_radius=3)
    tier_names = {1:"I", 2:"II", 3:"III"}
    draw_text_shadow(screen, f"WPN {tier_names[weapon_tier]}", font_tiny, bar_col, bx, by-14)
    # Bomb count
    bmb_col = (255,200,50)
    draw_text_shadow(screen, f"BOMB: {'■'*bomb_count}{'□'*(3-bomb_count)}", font_tiny, bmb_col, bx - 60, by-14)

# ================= SPAWN POWERUP =================
def spawn_powerup(x, y, force=False):
    if not force and random.random() > 0.12:
        return
    pt = random.choices(
        [POWER_RAPID, POWER_SHIELD, POWER_LIFE, POWER_SPREAD,
         POWER_MAGNET, POWER_LASER, POWER_NUKE, POWER_SLOWMO],
        weights=[25, 22, 5, 18, 7, 10, 6, 7]
    )[0]
    powerups.append({"x": float(x), "y": float(y), "type": pt,
                      "speed": 1.5, "pulse": random.uniform(0, math.pi*2)})

# ================= BOSS ATTACK =================
boss_shoot_timer = 0

def boss_attack(m):
    """Boss tembakkan 3 peluru ke arah pemain."""
    global boss_shoot_timer
    dx = player_pos[0] - m["x"]
    dy = player_pos[1] - m["y"]
    dist = math.hypot(dx, dy)
    if dist == 0: return
    speed = 4.0
    for spread in [-0.25, 0, 0.25]:
        angle = math.atan2(dy, dx) + spread
        enemy_bullets.append({
            "x": float(m["x"]), "y": float(m["y"]),
            "vx": math.cos(angle)*speed, "vy": math.sin(angle)*speed,
            "lifetime": 180
        })
    boss_shoot_sfx.play()

def draw_enemy_bullet(b):
    bx, by = int(b["x"]), int(b["y"])
    pygame.draw.circle(screen, (255,50,50), (bx,by), 5)
    pygame.draw.circle(screen, (255,150,150), (bx,by), 3)
    glow = pygame.Surface((16,16), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255,0,0,60), (8,8), 8)
    screen.blit(glow, (bx-8, by-8))


# ================= DRAW POWERUP =================
def draw_powerup(p):
    p["pulse"] += 0.1
    glow = int(abs(math.sin(p["pulse"]))*60)
    pd = power_up_defs[p["type"]]
    r,g,b = pd["color"]
    col = (min(255,r+glow), min(255,g+glow), min(255,b+glow))
    gs = pygame.Surface((36,36), pygame.SRCALPHA)
    pygame.draw.circle(gs, (*col,50), (18,18), 18)
    screen.blit(gs, (int(p["x"])-18, int(p["y"])-18))
    pygame.draw.circle(screen, col, (int(p["x"]),int(p["y"])), 11)
    pygame.draw.circle(screen, WHITE, (int(p["x"]),int(p["y"])), 11, 2)
    draw_text_shadow(screen, pd["symbol"], font_small, WHITE, int(p["x"])-font_small.size(pd["symbol"])[0]//2, int(p["y"])-font_small.size(pd["symbol"])[1]//2)

# ================= DRAW PLAYER =================
def draw_player(moving):
    global invincible_timer
    if invincible_timer > 0:
        invincible_timer -= 1
        if (invincible_timer//4) % 2 == 0:
            return

    # Shield
    if active_powers[POWER_SHIELD] > 0:
        ss = pygame.Surface((80,80), pygame.SRCALPHA)
        pulse = abs(math.sin(frame_count/10))
        alpha = int(80+pulse*80)
        pygame.draw.circle(ss, (0,200,255,alpha), (40,40), 38, 3)
        pygame.draw.circle(ss, (0,200,255,alpha//3), (40,40), 38)
        screen.blit(ss, (player_pos[0]-40, player_pos[1]-40))

    # Laser aura
    if active_powers[POWER_LASER] > 0:
        la = pygame.Surface((60,60), pygame.SRCALPHA)
        pulse = abs(math.sin(frame_count/6))
        pygame.draw.circle(la, (255,50,200,int(50+pulse*60)), (30,30), 30, 2)
        screen.blit(la, (player_pos[0]-30, player_pos[1]-30))

    # Magnet aura
    if active_powers[POWER_MAGNET] > 0:
        ma = pygame.Surface((120,120), pygame.SRCALPHA)
        pygame.draw.circle(ma, (80,255,120,20), (60,60), 58, 2)
        screen.blit(ma, (player_pos[0]-60, player_pos[1]-60))

    screen.blit(rocket_img, (player_pos[0]-24, player_pos[1]-28))
    spawn_thruster(player_pos[0], player_pos[1]+24)
    add_player_trail(player_pos[0], player_pos[1], moving)

# ================= DRAW METEOR =================
def draw_meteor(m):
    mtype = m["type"]
    sz = m["size"]
    col = METEOR_COLORS.get(mtype)

    if col:
        img = get_tinted_meteor(sz, col)
    else:
        img = get_meteor_img(sz)

    rect = img.get_rect(center=(int(m["x"]), int(m["y"])))
    screen.blit(img, rect)

    # Sparks every 3 frames
    m["spark_timer"] += 1
    if m["spark_timer"] >= 3:
        m["spark_timer"] = 0
        spawn_sparks(m["x"], m["y"], sz, mtype if not m["is_boss"] else "normal")
    spawn_trail_particle(m["x"], m["y"], sz, mtype if not m["is_boss"] else "normal")

    # Glow
    gs = sz*2+10
    glow_surf = pygame.Surface((gs, gs), pygame.SRCALPHA)
    gc = col if col else (140,50,220)
    pulse = abs(math.sin(frame_count/12 + m["x"]*0.1))
    pygame.draw.circle(glow_surf, (*gc, int(20+pulse*15)), (gs//2,gs//2), gs//2)
    screen.blit(glow_surf, (int(m["x"])-gs//2, int(m["y"])-gs//2))

    # HP bars
    if m["is_boss"]:
        bw = sz*2; bh = 7
        bx = int(m["x"])-bw//2; by = int(m["y"])-sz-16
        pygame.draw.rect(screen, (60,60,60), (bx-1,by-1,bw+2,bh+2), border_radius=3)
        pygame.draw.rect(screen, (80,0,0), (bx,by,bw,bh), border_radius=3)
        fill = int(bw*m["hp"]/m["max_hp"])
        pygame.draw.rect(screen, RED, (bx,by,fill,bh), border_radius=3)
        bl = font_tiny.render("★ BOSS ★", True, MAGENTA)
        screen.blit(bl, (int(m["x"])-bl.get_width()//2, by-15))
    elif m["hp"] > 1:
        bw = sz; by = int(m["y"])-sz-8
        pygame.draw.rect(screen, (60,0,0), (int(m["x"])-bw//2, by, bw, 4))
        fill = int(bw*m["hp"]/m["max_hp"])
        pygame.draw.rect(screen, GREEN, (int(m["x"])-bw//2, by, fill, 4))

    # Type label for special meteors
    if mtype in ("fast","tanky","zigzag","splitter"):
        labels = {"fast":"FAST","tanky":"ARMOR","zigzag":"ZIG","splitter":"SPLIT"}
        lt = font_tiny.render(labels[mtype], True, WHITE)
        screen.blit(lt, (int(m["x"])-lt.get_width()//2, int(m["y"])+sz+2))

# ================= DRAW BULLETS =================
def draw_bullet(b):
    bx, by = int(b["x"]), int(b["y"])
    if b["type"] == "laser":
        # Laser beam
        pygame.draw.rect(screen, MAGENTA,  (bx-3, by, 6, 28), border_radius=3)
        pygame.draw.rect(screen, WHITE,    (bx-1, by, 2, 28), border_radius=1)
        # Glow
        gs = pygame.Surface((18, 50), pygame.SRCALPHA)
        pygame.draw.ellipse(gs, (255,50,200,80), (0,0,18,50))
        screen.blit(gs, (bx-9, by-10))
    else:
        # Normal bullet
        pygame.draw.rect(screen, (255,100,100), (bx-2, by, 4, 14), border_radius=2)
        pygame.draw.rect(screen, (255,200,150), (bx-1, by+2, 2, 8), border_radius=1)
        # Glow
        gs = pygame.Surface((16, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(gs, (255,180,50,60), (0,0,16,24))
        screen.blit(gs, (bx-8, by-4))

# ================= HUD =================
def draw_hud():
    HEARTS_PER_ROW = 4
    heart_rows = math.ceil(lives / HEARTS_PER_ROW) if lives > 0 else 1
    hud_h = 38 + (heart_rows-1)*30

    hs = pygame.Surface((WIDTH, hud_h+8), pygame.SRCALPHA)
    hs.fill((0,0,0,130))
    screen.blit(hs, (0,0))

    # Lives
    for i in range(lives):
        row = i // HEARTS_PER_ROW
        col = i % HEARTS_PER_ROW
        screen.blit(heart_img, (8+col*30, 4+row*30))

    # ---------------- HUD Overlays (Pills) ----------------
    def draw_hud_pill(surf, text, font, color, x, y, pad_x=10, pad_y=4):
        tw, th = font.size(text)
        bg = pygame.Surface((tw + pad_x*2, th + pad_y*2), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0,0,0,140), (0,0, bg.get_width(), bg.get_height()), border_radius=8)
        surf.blit(bg, (x - pad_x, y - pad_y))
        draw_text_shadow(surf, text, font, color, x, y, offset=1)
        return tw, th

    # Score (Top Center)
    score_txt = f"{score}"
    draw_hud_pill(screen, score_txt, font_med, WHITE, WIDTH//2-font_med.size(score_txt)[0]//2, 8)

    # Kills (Below Score)
    kills_txt = f"KILLS: {total_kills}"
    draw_hud_pill(screen, kills_txt, font_tiny, (180,180,180), WIDTH//2-font_tiny.size(kills_txt)[0]//2, 34)

    # Level (Top Right)
    lvl_txt = f"LV {level}"
    draw_hud_pill(screen, lvl_txt, font_small, CYAN, WIDTH - font_small.size(lvl_txt)[0] - 14, 8)

    # High score (Below Level)
    hi_txt = f"HI: {high_score}"
    draw_hud_pill(screen, hi_txt, font_tiny, YELLOW, WIDTH - font_tiny.size(hi_txt)[0] - 14, 30)

    # Combo
    if combo_count >= 2:
        pulse = abs(math.sin(frame_count/8))
        cc = (int(255*pulse), int(200+55*pulse), int(50+200*pulse))
        ct = font_combo.render(f"x{combo_count} COMBO!", True, cc)
        screen.blit(ct, (WIDTH//2-ct.get_width()//2, hud_h+10))

    # Kill streak badge
    if kill_streak >= 5:
        streak_colors = {5: GREEN, 10: YELLOW, 15: ORANGE, 20: MAGENTA}
        col = WHITE
        for threshold in sorted(streak_colors.keys(), reverse=True):
            if kill_streak >= threshold:
                col = streak_colors[threshold]; break
        skt = font_tiny.render(f"STREAK: {kill_streak}!", True, col)
        screen.blit(skt, (WIDTH-skt.get_width()-8, hud_h+10))

    # Power-up bars (bottom)
    y_off = HEIGHT - 90
    for pk in active_powers:
        if active_powers[pk] > 0:
            secs = active_powers[pk]//60+1
            pd = power_up_defs[pk]
            bw = 90
            bf = int(bw*active_powers[pk]/pd["duration"]) if pd["duration"]>0 else bw
            pygame.draw.rect(screen, (40,40,60), (8,y_off,bw+4,16), border_radius=3)
            pygame.draw.rect(screen, pd["color"], (10,y_off+2,bf,12), border_radius=2)
            label = font_tiny.render(f"{pd['name']} {secs}s", True, WHITE)
            screen.blit(label, (bw+18, y_off))
            y_off -= 22

# ================= DANGER LOW HP =================
def draw_danger():
    """Vignette merah berdenyut saat nyawa tinggal 1."""
    if lives == 1:
        pulse = abs(math.sin(frame_count/20))
        vs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alpha = int(80*pulse)
        pygame.draw.rect(vs, (200,0,0,alpha), (0,0,WIDTH,HEIGHT), 18)
        screen.blit(vs, (0,0))

# ================= BUTTONS (MOBILE) =================
# Format: (x, y, w, h, text, color, key_id)
is_muted = False
buttons = []

def get_buttons():
    BTN_Y = HEIGHT - 70
    return [
        {"x": WIDTH//2 - 60, "y": BTN_Y, "w": 120, "h": 50, "text": "BOMB", "key": "bomb", "col": (200,60,30)},
        {"x": WIDTH - 75,"y": 55,"w": 65, "h": 32, "text": "HOME","key": "home","col":(150,50,50)},
        {"x": 10,"y": 55,"w": 55, "h": 32, "text": "VOL","key": "mute","col":(50,120,160)}
    ]

def draw_buttons():
    global buttons
    buttons = get_buttons()
    for b in buttons:
        # Don't draw bomb if empty
        if b["key"] == "bomb" and bomb_count <= 0: continue
        color = b["col"]
        if b["key"] == "mute" and is_muted: color = (80,80,80)
        
        rect = (b["x"], b["y"], b["w"], b["h"])
        # Translucent background for buttons
        bg = pygame.Surface((b["w"], b["h"]), pygame.SRCALPHA)
        pygame.draw.rect(bg, (*color, 200), (0,0,b["w"],b["h"]), border_radius=8)
        screen.blit(bg, (b["x"], b["y"]))
        pygame.draw.rect(screen, (255,255,255,100), rect, 2, border_radius=8)
        
        t = "MUTE" if (b["key"]=="mute" and is_muted) else b["text"]
        f = font_small if b["key"] in ("home", "mute") else font_med
        draw_text_shadow(screen, t, f, WHITE, b["x"] + b["w"]//2 - f.size(t)[0]//2, b["y"] + b["h"]//2 - f.size(t)[1]//2, offset=1)


def check_button_click(pos):
    for b in buttons:
        if b["key"] == "bomb" and bomb_count <= 0: continue
        if b["x"] <= pos[0] <= b["x"]+b["w"] and b["y"] <= pos[1] <= b["y"]+b["h"]:
            return b["key"]
    return None

# ================= WAVE WARNING =================
wave_warning_timer = 0
level_up_timer = 0

def draw_wave_warning():
    global wave_warning_timer
    if wave_warning_timer > 0:
        wave_warning_timer -= 1
        pulse = abs(math.sin(frame_count/6))
        col = (255, int(pulse*100), 0)
        t = "⚠ WAVE INCOMING! ⚠"
        draw_text_shadow(screen, t, font_large, col, WIDTH//2-font_large.size(t)[0]//2, HEIGHT//2-20)

def draw_level_banner():
    global level_up_timer
    if level_up_timer > 0:
        level_up_timer -= 1
        a = min(1.0, level_up_timer/30)
        col = (int(0+255*(1-a)), int(200*a), int(255*a))
        t = f"LEVEL {level}!"
        draw_text_shadow(screen, t, font_large, col, WIDTH//2-font_large.size(t)[0]//2, HEIGHT//2-60)

# ================= MENU =================
def draw_menu():
    draw_background()
    t = pygame.time.get_ticks()/1000

    # Animated title
    title1 = font_title.render("SPACE METEOR", True, CYAN)
    title2 = font_title.render("HUNTER", True, YELLOW)
    s1 = font_title.render("SPACE METEOR", True, (0,60,80))
    s2 = font_title.render("HUNTER", True, (80,60,0))
    screen.blit(s1, (WIDTH//2-s1.get_width()//2+2, 102))
    screen.blit(s2, (WIDTH//2-s2.get_width()//2+2, 152))
    screen.blit(title1, (WIDTH//2-title1.get_width()//2, 100))
    screen.blit(title2, (WIDTH//2-title2.get_width()//2, 150))

    # Rocket bobbing
    bob = int(math.sin(t*2)*6)
    br = pygame.transform.scale(rocket_img, (80,96))
    screen.blit(br, (WIDTH//2-40, 220+bob))
    for _ in range(3):
        px = WIDTH//2 + random.uniform(-8,8)
        py = 220+bob+96+random.uniform(0,10)
        pygame.draw.circle(screen, random.choice([(255,200,50),(255,120,20)]),
                           (int(px),int(py)), random.randint(2,5))

    pulse = abs(math.sin(t*2))*255
    col = (int(pulse), 255, int(pulse))
    pt = font_med.render("ENTER / SPACE TO START", True, col)
    screen.blit(pt, (WIDTH//2-pt.get_width()//2, 360))

    # Meteor type legend
    legend = [
        ("NORMAL",  "Grey",   (160,160,160)),
        ("FAST",    "Orange", ORANGE),
        ("ARMOR",   "Blue",   BLUE),
        ("ZIG-ZAG", "Cyan",   CYAN),
        ("SPLIT",   "Red",    RED),
        ("BOSS",    "Magenta",MAGENTA),
    ]
    lx = 20
    lt_label = font_tiny.render("METEOR TYPES:", True, (180,180,200))
    screen.blit(lt_label, (lx, 420))
    for i, (name, _, col) in enumerate(legend):
        row, col_i = i//3, i%3
        lxt = lx + col_i * 135
        lyt = 437 + row * 16
        pygame.draw.circle(screen, col, (lxt+5, lyt+5), 5)
        label = font_tiny.render(name, True, col)
        screen.blit(label, (lxt+14, lyt-1))

    controls = [
        "WASD / Arrows = Move",
        "Click / SPACE  = Shoot",
        "P = Pause   ESC = Menu",
    ]
    for i, line in enumerate(controls):
        ct = font_small.render(line, True, (150,150,170))
        screen.blit(ct, (WIDTH//2-ct.get_width()//2, 490+i*22))

    if high_score > 0:
        ht = font_med.render(f"HIGH SCORE: {high_score}", True, YELLOW)
        screen.blit(ht, (WIDTH//2-ht.get_width()//2, 570))

# ================= GAME OVER =================
def draw_game_over():
    draw_background()
    overlay = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,110))
    screen.blit(overlay, (0,0))

    gt = font_title.render("GAME OVER", True, RED)
    sg = font_title.render("GAME OVER", True, (80,0,0))
    screen.blit(sg, (WIDTH//2-sg.get_width()//2+2, 162))
    screen.blit(gt, (WIDTH//2-gt.get_width()//2, 160))

    st = font_large.render(f"SCORE: {score}", True, WHITE)
    screen.blit(st, (WIDTH//2-st.get_width()//2, 220))

    stats = [f"LEVEL: {level}",
             f"METEORS DESTROYED: {total_kills}",
             f"BEST COMBO: x{combo_count}"]
    for i, s in enumerate(stats):
        tt = font_small.render(s, True, (180,180,200))
        screen.blit(tt, (WIDTH//2-tt.get_width()//2, 260+i*22))

    # Star Rating
    stars_earned = 1
    if score >= 10000: stars_earned = 3
    elif score >= 5000: stars_earned = 2
    
    star_txt = "★ " * stars_earned + "☆ " * (3 - stars_earned)
    st_surf = font_title.render(star_txt.strip(), True, YELLOW)
    screen.blit(st_surf, (WIDTH//2-st_surf.get_width()//2, 340))

    pulse = abs(math.sin(pygame.time.get_ticks()/500))*255
    col = (int(pulse), 255, int(pulse))

    if score >= high_score and score > 0:
        t = pygame.time.get_ticks()/300
        rbow = (int(abs(math.sin(t))*255),int(abs(math.sin(t+2))*255),int(abs(math.sin(t+4))*255))
        nh = font_med.render("NEW HIGH SCORE!", True, rbow)
        screen.blit(nh, (WIDTH//2-nh.get_width()//2, 390))

    rt = font_med.render("TAP / ENTER TO RESTART", True, col)
    screen.blit(rt, (WIDTH//2-rt.get_width()//2, 450))

    et = font_small.render("ESC = MENU", True, (150,150,170))
    screen.blit(et, (WIDTH//2-et.get_width()//2, 480))

# ================= PAUSED =================
def draw_paused():
    ov = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
    ov.fill((0,0,20,150))
    screen.blit(ov, (0,0))
    draw_text_shadow(screen, "HOME / PAUSED", font_title, CYAN, WIDTH//2-font_title.size("HOME / PAUSED")[0]//2, HEIGHT//2-40)
    
    # Resume Button
    rect = (WIDTH//2-70, HEIGHT//2+20, 140, 50)
    pygame.draw.rect(screen, GREEN, rect, border_radius=8)
    draw_text_shadow(screen, "RESUME", font_large, WHITE, WIDTH//2-font_large.size("RESUME")[0]//2, HEIGHT//2+25)
    
    # Quit Button
    rect2 = (WIDTH//2-70, HEIGHT//2+90, 140, 50)
    pygame.draw.rect(screen, RED, rect2, border_radius=8)
    draw_text_shadow(screen, "QUIT TO MENU", font_med, WHITE, WIDTH//2-font_med.size("QUIT TO MENU")[0]//2, HEIGHT//2+102)

# ================= MAIN LOOP (ASYNC FOR PYGBAG) =================
target_pos = None

async def main():
    global frame_count, game_state, running, level_up_timer, kill_streak, target_pos
    global player_pos, shoot_cooldown, active_powers, combo_count, combo_timer
    global level_timer, level, difficulty_mult, wave_warning_timer, boss_spawned
    global meteor_timer, shower_timer, shower_active, shower_sfx, screen

    running = True
    level_up_timer = 0
    kill_streak = 0
    
    def map_pos(phy_pos):
        px, py = phy_pos
        scale = min(SCREEN_W / WIDTH, SCREEN_H / HEIGHT)
        sw, sh = int(WIDTH * scale), int(HEIGHT * scale)
        x_off, y_off = (SCREEN_W - sw) // 2, (SCREEN_H - sh) // 2
        vx = (px - x_off) / scale
        vy = (py - y_off) / scale
        return vx, vy

    while running:
        global SCREEN_W, SCREEN_H
        frame_count += 1
        clock.tick(60)

        sx, sy = get_shake()
        mouse_pos = map_pos(pygame.mouse.get_pos())
        clicked_btn = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.VIDEORESIZE:
                SCREEN_W, SCREEN_H = event.w, event.h
                real_screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)

            if event.type == pygame.KEYDOWN and not is_transitioning:
                if game_state == STATE_MENU:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        start_transition(STATE_PLAYING)
                elif game_state == STATE_GAME_OVER:
                    if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                        start_transition(STATE_PLAYING)
                    elif event.key == pygame.K_ESCAPE:
                        start_transition(STATE_MENU)
                elif game_state == STATE_PLAYING:
                    if event.key == pygame.K_p:
                        game_state = STATE_PAUSED
                    if event.key == pygame.K_SPACE:
                        shoot()
                    if event.key == pygame.K_b:
                        bomb_detonate()
                elif game_state == STATE_PAUSED:
                    if event.key == pygame.K_p:
                        game_state = STATE_PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        game_state = STATE_MENU

            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1 and not is_transitioning:
                if game_state == STATE_MENU:
                    start_transition(STATE_PLAYING)
                elif game_state == STATE_GAME_OVER:
                    start_transition(STATE_PLAYING)
                elif game_state == STATE_PLAYING:
                    mapped_e_pos = map_pos(event.pos)
                    btn = check_button_click(mapped_e_pos)
                    if btn:
                        clicked_btn = btn
                        if btn == "home": game_state = STATE_PAUSED
                        elif btn == "bomb": bomb_detonate()
                        elif btn == "mute":
                            global is_muted
                            is_muted = not is_muted
                            if is_muted:
                                pygame.mixer.pause()
                            else:
                                pygame.mixer.unpause()
                    else:
                        target_pos = list(mapped_e_pos)
                        shoot()
                elif game_state == STATE_PAUSED:
                    # Check Resume or Quit
                    px, py = map_pos(event.pos)
                    if WIDTH//2-70 <= px <= WIDTH//2+70:
                        if HEIGHT//2+20 <= py <= HEIGHT//2+70:
                            game_state = STATE_PLAYING  # RESUME
                        elif HEIGHT//2+90 <= py <= HEIGHT//2+140:
                            start_transition(STATE_MENU)  # QUIT TO MENU

            if event.type == pygame.MOUSEMOTION and getattr(event, 'buttons', (0,0,0))[0] and not is_transitioning:
                mapped_e_pos = map_pos(event.pos)
                if game_state == STATE_PLAYING and not check_button_click(mapped_e_pos):
                    target_pos = list(mapped_e_pos)

            if event.type == pygame.MOUSEBUTTONUP and getattr(event, 'button', 1) == 1:
                target_pos = None

        # ========== State Handlers ==========
        if game_state == STATE_MENU:
            draw_menu()
            update_draw_transition()
            pygame.display.flip()
            await asyncio.sleep(0); continue

        if game_state == STATE_GAME_OVER:
            draw_game_over()
            update_particles(); update_score_popups()
            update_draw_transition()
            pygame.display.flip()
            await asyncio.sleep(0); continue

        if game_state == STATE_PAUSED:
            draw_background()
            update_trail(); update_particles()
            draw_player(False)
            for m in meteors: draw_meteor(m)
            draw_hud(); draw_buttons(); draw_paused()
            update_draw_transition()
            pygame.display.flip()
            await asyncio.sleep(0); continue

        # Hit Stop Freeze Juice
        global hit_stop_frames
        if hit_stop_frames > 0:
            hit_stop_frames -= 1
            draw_background()
            update_trail()
            draw_player(False)
            for m in meteors: draw_meteor(m)
            draw_hud(); draw_buttons()
            pygame.display.flip()
            await asyncio.sleep(0)
            continue

        # ========== PLAYING ==========
        mouse_pressed = getattr(pygame.mouse, 'get_pressed', lambda: (0,0,0))()[0]
        keys = pygame.key.get_pressed()
        space_pressed = keys[pygame.K_SPACE]

        # Auto fire & touch shoot
        is_firing = space_pressed or (mouse_pressed and not check_button_click(mouse_pos))
        cooldown_rate = 3 if active_powers[POWER_RAPID] > 0 else \
                        2 if active_powers[POWER_LASER] > 0 else 8
        if is_firing and shoot_cooldown <= 0:
            shoot(); shoot_cooldown = cooldown_rate
        if shoot_cooldown > 0: shoot_cooldown -= 1

        # Power-up timers
        for pk in list(active_powers.keys()):
            if active_powers[pk] > 0: active_powers[pk] -= 1

        slowmo = 0.35 if active_powers[POWER_SLOWMO] > 0 else 1.0

        if combo_timer > 0: combo_timer -= 1
        else: combo_count = 0

        # Player movement
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= player_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += player_speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= player_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += player_speed
        
        # Touch follow movement
        if target_pos:
            tx, ty = target_pos
            tx = max(24, min(WIDTH-24, tx))
            ty = max(28, min(HEIGHT-100, ty)) # keep finger above buttons
            t_dx = tx - player_pos[0]
            t_dy = ty - player_pos[1]
            dist = math.hypot(t_dx, t_dy)
            if dist > player_speed:
                dx += (t_dx/dist) * player_speed*1.5
                dy += (t_dy/dist) * player_speed*1.5
            else:
                player_pos[0] = tx; player_pos[1] = ty

        if dx and dy: dx *= 0.707; dy *= 0.707
        moving = (dx != 0 or dy != 0)

        player_pos[0] = max(24, min(WIDTH-24,  player_pos[0]+dx))
        player_pos[1] = max(28, min(HEIGHT-100, player_pos[1]+dy))

        # Events: Leveling, Shower, Comets
        level_timer += 1
        if level_timer >= 600:
            level_timer = 0; level += 1
            difficulty_mult = 1.0 + (level-1)*0.15
            level_up_timer = 90
            levelup_sfx.play()
            wave_warning_timer = 60; warning_sfx.play()

        # Meteor Shower
        shower_timer -= 1
        if shower_timer <= 0:
            shower_active = 200
            shower_timer = random.randint(1200, 2400)
            shower_sfx.play(); push_achievement("METEOR SHOWER!", RED)
        
        # Spawn logic
        if shower_active > 0:
            shower_active -= 1
            if frame_count % 3 == 0:
                spawn_meteor(mtype="fast")
        else:
            meteor_timer += 1
            spawn_rate = max(8, 30 - level*2)
            if meteor_timer > spawn_rate:
                spawn_meteor(); meteor_timer = 0
                if random.random() < 0.05 + 0.02*level:
                    spawn_comet()

        if level % 5 == 0 and not boss_spawned:
            spawn_meteor(is_boss=True); boss_spawned = True
        if level % 5 != 0: boss_spawned = False

        # ===== DRAW =====
        draw_background()
        update_trail()
        draw_player(moving)
        update_draw_comets()

        # Bullets
        for b in bullets[:]:
            b["x"] += b["vx"]; b["y"] += b["vy"]
            draw_bullet(b)
            if b["y"] < -30 or b["x"] < -10 or b["x"] > WIDTH+10:
                bullets.remove(b)

        # Meteors
        global score, total_kills, xp
        for meteor in meteors[:]:
            meteor["timer"] -= 1
            if meteor["timer"] <= 0:
                meteor["speed"] = meteor["base_speed"]*random.uniform(0.6,1.8)
                meteor["timer"] = random.randint(40,140)
                if meteor["is_boss"] and level >= 3: boss_attack(meteor)

            if meteor["type"] == "zigzag":
                meteor["zigzag_phase"] += 0.08
                meteor["vx"] = math.sin(meteor["zigzag_phase"]) * 2.5

            effective_speed = meteor["speed"] * slowmo
            meteor["x"] += meteor.get("vx", 0) * slowmo
            meteor["y"] += effective_speed
            meteor["x"] = max(meteor["size"], min(WIDTH-meteor["size"], meteor["x"]))

            draw_meteor(meteor)

            # Hit by bullet
            for b in bullets[:]:
                dist = math.hypot(meteor["x"]-b["x"], meteor["y"]-b["y"])
                hit_radius = meteor["size"] + (4 if b["type"] == "laser" else 0)
                if dist < hit_radius:
                    if b in bullets: bullets.remove(b)
                    dmg = 2 if b["type"] == "laser" else 1
                    meteor["hp"] -= dmg
                    if meteor["hp"] <= 0:
                        if meteor["type"] == "splitter":
                            split_meteor(meteor); push_achievement("SPLIT!", ORANGE)

                        combo_count += 1; combo_timer = 90
                        total_kills += 1; kill_streak += 1; xp += 1
                        last_kill_time = frame_count

                        if kill_streak in (5, 10, 15, 20, 30):
                            msgs = {5:"5 KILL STREAK!", 10:"10 KILL STREAK! 🔥", 15:"UNSTOPPABLE!", 20:"GODLIKE! 💀", 30:"LEGENDARY!"}
                            c_idx = list(msgs.keys()).index(kill_streak)
                            push_achievement(msgs[kill_streak], [GREEN,YELLOW,ORANGE,MAGENTA,RED][c_idx])

                        base_pts = 50 if meteor["is_boss"] else 20 if meteor["type"] in ("tanky","boss") else 15 if meteor["type"] == "splitter" else 10
                        mult = min(combo_count, 10)
                        pts = base_pts * level * mult; score += pts

                        if combo_count >= 2: combo_sfx.play()

                        ecol = METEOR_COLORS.get(meteor["type"]) or (255,140,40)
                        spawn_explosion(meteor["x"], meteor["y"], ecol, 20)
                        spawn_explosion(meteor["x"], meteor["y"], LIGHT_PURPLE, 8)
                        explode_sfx.play()

                        popup_col = YELLOW if mult<3 else ORANGE if mult<6 else MAGENTA
                        spawn_score_popup(meteor["x"], meteor["y"], f"+{pts}", popup_col)

                        if meteor["is_boss"]:
                            trigger_hit_stop(25)
                            spawn_powerup(meteor["x"], meteor["y"], force=True)
                            spawn_powerup(meteor["x"]+30, meteor["y"], force=True)
                            trigger_shake(10, 20); trigger_flash((255,100,0), 12)
                            push_achievement("BOSS DEFEATED!", MAGENTA)
                            xp += 10
                        else:
                            trigger_hit_stop(3) # Light hit stop for normal meteors too
                            spawn_powerup(meteor["x"], meteor["y"])

                        _check_weapon_tier()
                        if meteor in meteors: meteors.remove(meteor)
                    else:
                        hit_sfx.play()
                        spawn_explosion(meteor["x"], meteor["y"], (220,200,255), 5)
                    break

            if meteor in meteors and invincible_timer <= 0:
                pdist = math.hypot(meteor["x"]-player_pos[0], meteor["y"]-player_pos[1])
                if pdist < meteor["size"] + 18:
                    if meteor in meteors: meteors.remove(meteor)
                    _on_player_hit()

            if meteor in meteors and meteor["y"] > HEIGHT+80:
                meteors.remove(meteor)

        # Powerups
        global lives, high_score
        for p in powerups[:]:
            p["y"] += p["speed"]
            if active_powers[POWER_MAGNET] > 0:
                ddx = player_pos[0]-p["x"]; ddy = player_pos[1]-p["y"]
                md = math.hypot(ddx, ddy)
                if md > 5: p["x"] += ddx/md*4; p["y"] += ddy/md*4

            draw_powerup(p)
            dist = math.hypot(p["x"]-player_pos[0], p["y"]-player_pos[1])
            if dist < 26:
                pt = p["type"]
                if pt == POWER_LIFE:
                    lives = min(lives+1, max_lives); push_achievement("EXTRA LIFE!", RED)
                elif pt == POWER_NUKE:
                    killed = len(meteors)
                    for m in meteors:
                        spawn_explosion(m["x"], m["y"], METEOR_COLORS.get(m["type"]) or (255,140,40), 15)
                        score += 5 * level; xp += 1
                    meteors.clear()
                    nuke_sfx.play(); trigger_flash((255,120,40), 15); trigger_shake(12, 20)
                    push_achievement(f"NUKE! +{killed*5*level} PTS", (255,80,40))
                    _check_weapon_tier()
                elif pt == POWER_SLOWMO:
                    active_powers[POWER_SLOWMO] = power_up_defs[POWER_SLOWMO]["duration"]
                    slowmo_sfx.play(); push_achievement("SLOW-MO!", (80,180,255))
                else:
                    active_powers[pt] = power_up_defs[pt]["duration"]
                    push_achievement(power_up_defs[pt]["name"]+"!", power_up_defs[pt]["color"])
                
                if pt not in (POWER_NUKE, POWER_SLOWMO, POWER_LIFE): powerup_sfx.play()
                spawn_explosion(p["x"], p["y"], power_up_defs[pt]["color"], 12)
                spawn_score_popup(p["x"], p["y"], power_up_defs[pt]["name"], power_up_defs[pt]["color"])
                powerups.remove(p); continue
            
            if p["y"] > HEIGHT+20: powerups.remove(p)

        # Enemy bullets
        for eb in enemy_bullets[:]:
            eb["x"] += eb["vx"]; eb["y"] += eb["vy"]
            eb["lifetime"] -= 1
            draw_enemy_bullet(eb)
            if eb["lifetime"] <= 0 or eb["x"]<-10 or eb["x"]>WIDTH+10 or eb["y"]>HEIGHT+10 or eb["y"]<-10:
                if eb in enemy_bullets: enemy_bullets.remove(eb)
                continue
            if invincible_timer <= 0:
                if math.hypot(eb["x"]-player_pos[0], eb["y"]-player_pos[1]) < 20:
                    if eb in enemy_bullets: enemy_bullets.remove(eb)
                    _on_player_hit()

        # SlowMo tint
        if active_powers[POWER_SLOWMO] > 0:
            pulse = abs(math.sin(frame_count/15))
            so = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            so.fill((30, 80, 200, int(20+pulse*15)))
            screen.blit(so, (0,0))

        # Overlays
        update_particles()
        update_score_popups()
        draw_hud()
        draw_xp_bar()
        draw_achievements()
        draw_danger()
        draw_wave_warning()
        draw_level_banner()
        draw_buttons()
        draw_flash()
        update_draw_transition()

        # --- Virtual Resolution Scaling ---
        scale_x = SCREEN_W / WIDTH
        scale_y = SCREEN_H / HEIGHT
        scale = min(scale_x, scale_y)
        scaled_w = int(WIDTH * scale)
        scaled_h = int(HEIGHT * scale)
        x_off = (SCREEN_W - scaled_w) // 2
        y_off = (SCREEN_H - scaled_h) // 2
        
        scaled_bg = pygame.transform.scale(screen, (scaled_w, scaled_h))
        real_screen.fill((5, 5, 5)) # Elegantly dark margins
        real_screen.blit(scaled_bg, (x_off, y_off))

        pygame.display.flip()
        
        # REQUIRED for Pygbag / asyncio compilation
        await asyncio.sleep(0)

# Run asyncio main
if __name__ == "__main__":
    asyncio.run(main())
