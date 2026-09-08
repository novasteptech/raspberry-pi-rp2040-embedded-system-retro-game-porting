from machine import Pin, SPI, ADC, I2C
import time
import framebuf
import sys
import uselect
import gc

# -----------------------------
# Pins
# -----------------------------
PIN_LCD_RST   = 0
PIN_LCD_DC    = 1
PIN_LCD_SCK   = 2
PIN_LCD_MOSI  = 3

PIN_BTN_B     = 5
PIN_BTN_A     = 6
PIN_BTN_START = 7
PIN_BTN_SEL   = 8

# IMU (Task5)
PIN_I2C1_SDA  = 10
PIN_I2C1_SCL  = 11

# -----------------------------
# Display / Grid
# -----------------------------
WPIX, HPIX = 240, 240

GW, GH = 20, 20           # wire format
SCALE = 2                 # physics subgrid scale
SW, SH = GW*SCALE, GH*SCALE  # 40x40
TILE = 6                  # 240/40

MOVE_PERIOD_BY_DIFF = [180, 130, 90]  # Easy/Normal/Hard

# -----------------------------
# Colors
# -----------------------------
def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

C_BG    = rgb565(10, 10, 14)

# ✅ 改：迷宫墙颜色（换成紫色/洋红系，和黄/蓝/白区分很明显）
C_WALL  = rgb565(160, 60, 200)

C_FLOOR = rgb565(16, 16, 22)

# ✅ 改：终点亮白色（非常显眼）
C_TGT   = rgb565(255, 255, 255)

# ✅ 改：箱子蓝色（明显区别于玩家黄）
C_BOX   = rgb565(40, 120, 255)

# ✅ 改：玩家（摇杆滑块）亮黄色
C_PLY   = rgb565(255, 240, 40)

C_TXT   = rgb565(230, 230, 230)
C_DIM   = rgb565(140, 140, 140)
C_OK    = rgb565(80, 220, 120)

# subgrid object size (half corridor idea)
# Each subcell is TILE(6) pixels.
# We render player/box as 4x4 inside a 6x6 cell => "half width" visually,
# BUT IMPORTANT: physics grid is truly 40x40, so corridors are truly wider.
OBJ_SZ = 4
OBJ_OFS = (TILE - OBJ_SZ) // 2

# -----------------------------
# Minimal ST7789 driver (SPI)
# -----------------------------
class ST7789:
    def __init__(self, spi, dc, rst, width=240, height=240):
        self.spi = spi
        self.dc = dc
        self.rst = rst
        self.width = width
        self.height = height
        # full framebuffer (big, unavoidable if you want fast full-screen draw)
        self.buf = bytearray(width * height * 2)
        self.fb = framebuf.FrameBuffer(self.buf, width, height, framebuf.RGB565)
        self.reset()
        self.init_display()

    def reset(self):
        self.rst.value(1); time.sleep_ms(50)
        self.rst.value(0); time.sleep_ms(50)
        self.rst.value(1); time.sleep_ms(120)

    def write_cmd(self, cmd):
        self.dc.value(0)
        self.spi.write(bytearray([cmd]))

    def write_data(self, data):
        self.dc.value(1)
        self.spi.write(data)

    def init_display(self):
        self.write_cmd(0x36); self.write_data(bytearray([0x00]))
        self.write_cmd(0x3A); self.write_data(bytearray([0x55]))
        self.write_cmd(0xB2); self.write_data(bytearray([0x0C,0x0C,0x00,0x33,0x33]))
        self.write_cmd(0xB7); self.write_data(bytearray([0x35]))
        self.write_cmd(0xBB); self.write_data(bytearray([0x19]))
        self.write_cmd(0xC0); self.write_data(bytearray([0x2C]))
        self.write_cmd(0xC2); self.write_data(bytearray([0x01]))
        self.write_cmd(0xC3); self.write_data(bytearray([0x12]))
        self.write_cmd(0xC4); self.write_data(bytearray([0x20]))
        self.write_cmd(0xC6); self.write_data(bytearray([0x0F]))
        self.write_cmd(0xD0); self.write_data(bytearray([0xA4,0xA1]))
        self.write_cmd(0x21)
        self.write_cmd(0x11); time.sleep_ms(120)
        self.write_cmd(0x29); time.sleep_ms(20)
        self.set_window(0,0,self.width-1,self.height-1)

    def set_window(self, x0, y0, x1, y1):
        self.write_cmd(0x2A)
        self.write_data(bytearray([x0>>8,x0&0xFF,x1>>8,x1&0xFF]))
        self.write_cmd(0x2B)
        self.write_data(bytearray([y0>>8,y0&0xFF,y1>>8,y1&0xFF]))
        self.write_cmd(0x2C)

    def show(self):
        self.set_window(0,0,self.width-1,self.height-1)
        self.dc.value(1)
        self.spi.write(self.buf)

# -----------------------------
# IMU MMA7660FC (Task5)
# -----------------------------
class MMA7660:
    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = None
        try:
            addrs = i2c.scan()
        except Exception:
            addrs = []
        for a in addrs:
            if a in (0x4C, 0x4D):
                self.addr = a
                break
        self.ok = self.addr is not None
        if self.ok:
            try:
                self.i2c.writeto_mem(self.addr, 0x07, b"\x01")  # active
            except Exception:
                self.ok = False

    def _read_axis(self, reg):
        v = self.i2c.readfrom_mem(self.addr, reg, 1)[0] & 0x3F
        if v & 0x20:
            v -= 0x40
        return v

    def read_xyz(self):
        if not self.ok:
            return 0, 0, 0
        try:
            return (self._read_axis(0x00), self._read_axis(0x01), self._read_axis(0x02))
        except Exception:
            return 0, 0, 0

# -----------------------------
# Memory-safe Level (NO clone, NO list-of-list)
# baseS: bytearray(SW*SH)  1=wall,0=floor
# objects: set(int idx)
# -----------------------------
def idx_of(x, y):
    return y*SW + x

def xy_of(idx):
    return idx % SW, idx // SW

class LevelRuntime:
    def __init__(self):
        self.name = "(none)"
        self.diff = 0
        self.baseS = bytearray(SW*SH)     # 0/1
        self.targets = set()              # idx
        self.boxes = set()                # idx
        self.px = 0
        self.py = 0

    def is_wall(self, x, y):
        return self.baseS[idx_of(x,y)] == 1

    def win(self):
        if not self.targets:
            return False
        # all targets occupied
        for t in self.targets:
            if t not in self.boxes:
                return False
        return True

    def load_from_20x20_lines(self, name, diff, lines20):
        # strict checks
        if len(lines20) != 20:
            raise ValueError("bad height")
        for i in range(20):
            if len(lines20[i]) != 20:
                raise ValueError("bad width")

        self.name = name
        self.diff = diff

        # clear
        bs = self.baseS
        for i in range(len(bs)):
            bs[i] = 0
        self.targets.clear()
        self.boxes.clear()
        self.px = 0
        self.py = 0

        found_p = 0

        # expand base
        for y in range(GH):
            row = lines20[y]
            for x in range(GW):
                ch = row[x]
                is_wall = (ch == '#')
                # fill 2x2 subcells
                sx = x*SCALE
                sy = y*SCALE
                base_idx = idx_of(sx, sy)
                if is_wall:
                    # (sx,sy), (sx+1,sy), (sx,sy+1), (sx+1,sy+1)
                    bs[base_idx] = 1
                    bs[base_idx+1] = 1
                    bs[base_idx+SW] = 1
                    bs[base_idx+SW+1] = 1
                else:
                    # already 0
                    pass

        # force expanded border walls
        for x in range(SW):
            bs[idx_of(x,0)] = 1
            bs[idx_of(x,SH-1)] = 1
        for y in range(SH):
            bs[idx_of(0,y)] = 1
            bs[idx_of(SW-1,y)] = 1

        # objects at (2x,2y)
        for y in range(GH):
            row = lines20[y]
            for x in range(GW):
                ch = row[x]
                sx = x*SCALE
                sy = y*SCALE
                ii = idx_of(sx, sy)
                if ch == 'T':
                    self.targets.add(ii)
                elif ch == 'B':
                    self.boxes.add(ii)
                elif ch == '*':
                    self.targets.add(ii)
                    self.boxes.add(ii)
                elif ch == 'P':
                    self.px, self.py = sx, sy
                    found_p += 1
                elif ch == '+':
                    self.targets.add(ii)
                    self.px, self.py = sx, sy
                    found_p += 1
                else:
                    # '.' or '#': ignore
                    pass

        if found_p != 1:
            raise ValueError("need exactly one player")
        gc.collect()

# -----------------------------
# Rendering
# -----------------------------
def draw_level(disp, lvl, banner="", banner_c=C_TXT):
    fb = disp.fb
    fb.fill(C_BG)

    bs = lvl.baseS
    targets = lvl.targets
    boxes = lvl.boxes
    px = lvl.px
    py = lvl.py

    # draw tiles
    # note: loop 40x40 = 1600 cells, OK
    for y in range(SH):
        cy = y*TILE
        row_base = y*SW
        for x in range(SW):
            cx = x*TILE
            ii = row_base + x
            fb.fill_rect(cx, cy, TILE, TILE, C_WALL if bs[ii] else C_FLOOR)

            if ii in targets:
                fb.fill_rect(cx+2, cy+2, 2, 2, C_TGT)
            if ii in boxes:
                fb.fill_rect(cx+OBJ_OFS, cy+OBJ_OFS, OBJ_SZ, OBJ_SZ, C_BOX)

    # player
    fb.fill_rect(px*TILE+OBJ_OFS, py*TILE+OBJ_OFS, OBJ_SZ, OBJ_SZ, C_PLY)

    if banner:
        fb.fill_rect(0, 0, WPIX, 14, C_BG)
        fb.text(banner[:30], 2, 2, banner_c)

    fb.fill_rect(0, HPIX-14, WPIX, 14, C_BG)
    fb.text("A:Menu  B:Next  Start:Restart", 2, HPIX-12, C_DIM)

    disp.show()

def draw_menu(disp, idx, tilt_on, diff):
    fb = disp.fb
    fb.fill(C_BG)
    fb.text("MENU", 100, 10, C_TXT)
    items = [
        "Continue",
        "Restart Level",
        "Next Level (match diff)",
        "Difficulty: %s" % (["Easy","Normal","Hard"][diff]),
        "Control: %s" % ("Tilt" if tilt_on else "Joystick"),
    ]
    y = 40
    for i, s in enumerate(items):
        c = C_OK if i == idx else C_TXT
        fb.text(("> " if i==idx else "  ") + s, 20, y, c)
        y += 18
    fb.text("Up/Down: select  A:OK  B/Select:Back", 20, 210, C_DIM)
    disp.show()

# -----------------------------
# Input
# -----------------------------
class Buttons:
    def __init__(self):
        self.a = Pin(PIN_BTN_A, Pin.IN, Pin.PULL_UP)
        self.b = Pin(PIN_BTN_B, Pin.IN, Pin.PULL_UP)
        self.start = Pin(PIN_BTN_START, Pin.IN, Pin.PULL_UP)
        self.sel = Pin(PIN_BTN_SEL, Pin.IN, Pin.PULL_UP)
        self.last = {"a":1,"b":1,"start":1,"sel":1}

    def edge_falling(self, key, pin):
        v = pin.value()
        old = self.last[key]
        self.last[key] = v
        return old == 1 and v == 0

class Joy:
    def __init__(self):
        self.x = ADC(Pin(28))
        self.y = ADC(Pin(29))
        self.cx = 32768
        self.cy = 32768
        self.calibrate()

    def calibrate(self, n=30):
        sx = 0; sy = 0
        for _ in range(n):
            sx += self.x.read_u16()
            sy += self.y.read_u16()
            time.sleep_ms(5)
        self.cx = sx // n
        self.cy = sy // n

    def dir(self, dead=5000):
        vx = self.x.read_u16() - self.cx
        vy = self.y.read_u16() - self.cy
        if abs(vx) < dead and abs(vy) < dead:
            return 0, 0
        if abs(vx) > abs(vy):
            dx, dy = ((1, 0) if vx > 0 else (-1, 0))
        else:
            dx, dy = ((0, 1) if vy > 0 else (0, -1))
        # keep your locked swap
        dx, dy = dy, dx
        return dx, dy

# -----------------------------
# Serial level receiver (robust)
# returns dict: {"name":..,"diff":..,"lines":[20 strings]}
# -----------------------------
class LevelReceiver:
    def __init__(self):
        self.poll = uselect.poll()
        self.poll.register(sys.stdin, uselect.POLLIN)
        self.in_level = False
        self.meta = {}
        self.lines = []

    def _parse_meta(self, header):
        meta = {"name":"(unnamed)","diff":"0","w":"20","h":"20"}
        parts = header.strip().split()
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                meta[k.strip()] = v.strip()
        return meta

    def _reset(self):
        self.in_level = False
        self.meta = {}
        self.lines = []

    def tick(self):
        ev = self.poll.poll(0)
        if not ev:
            return None
        try:
            line = sys.stdin.readline()
        except Exception:
            return None
        if not line:
            return None

        line = line.strip("\r\n")
        if (not line) or line in (">", ">>>", "..."):
            return None

        if line.startswith("@LVL"):
            self.in_level = True
            self.meta = self._parse_meta(line)
            self.lines = []
            return None

        if not self.in_level:
            return None

        if line.startswith("@END"):
            try:
                w = int(self.meta.get("w","20"))
                h = int(self.meta.get("h","20"))
                if w != 20 or h != 20:
                    raise ValueError("only supports 20x20")
                if len(self.lines) != 20:
                    raise ValueError("need 20 lines, got %d" % len(self.lines))
                for i in range(20):
                    if len(self.lines[i]) != 20:
                        raise ValueError("bad width at line %d" % i)

                pkt = {
                    "name": self.meta.get("name","(unnamed)"),
                    "diff": int(self.meta.get("diff","0")),
                    "lines": tuple(self.lines),   # tuple saves RAM vs list
                }
                print("OK", pkt["name"])
                self._reset()
                gc.collect()
                return pkt
            except Exception as e:
                print("ERR", str(e))
                self._reset()
                gc.collect()
                return None

        if len(self.lines) < 20:
            self.lines.append(line)
        return None

# -----------------------------
# Movement on subgrid (40x40)
# -----------------------------
def try_move(lvl, dx, dy):
    nx = lvl.px + dx
    ny = lvl.py + dy
    if nx < 0 or nx >= SW or ny < 0 or ny >= SH:
        return False
    if lvl.is_wall(nx, ny):
        return False

    nidx = idx_of(nx, ny)

    if nidx in lvl.boxes:
        bx = nx + dx
        by = ny + dy
        if bx < 0 or bx >= SW or by < 0 or by >= SH:
            return False
        if lvl.is_wall(bx, by):
            return False
        bidx = idx_of(bx, by)
        if bidx in lvl.boxes:
            return False
        lvl.boxes.remove(nidx)
        lvl.boxes.add(bidx)

    lvl.px, lvl.py = nx, ny
    return True

# -----------------------------
# Built-in levels (store only 20x20 lines, NOT expanded objects)
# -----------------------------
DEFAULT_LEVELS = [
    {
        "name": "BuiltIn-E",
        "diff": 0,
        "lines": (
            "####################",
            "#..#.....#.....#...#",
            "#..#..#..#..#..#...#",
            "#.....#.....#....T.#",
            "#.###.#####.###.####",
            "#...#.....#...#....#",
            "###.#.###.#.#.####.#",
            "#...#...#.#.#......#",
            "#.#####.#.#.######.#",
            "#.....#.#.#....#...#",
            "#.###.#.#.####.#.###",
            "#...#.#....B...#...#",
            "#.#.#.##########.#.#",
            "#.#.#..........#.#.#",
            "#.#.##########.#.#.#",
            "#.#......P.....#...#",
            "#.##############.###",
            "#..................#",
            "#..................#",
            "####################",
        )
    },
    {
        "name": "BuiltIn-N",
        "diff": 1,
        "lines": (
            "####################",
            "#..#.....#.....#...#",
            "#..#.###.#.###.#.T.#",
            "#.....#.....#......#",
            "#.###.#.###.#.####.#",
            "#...#.#...#.#....#.#",
            "###.#.###.#.###.#..#",
            "#...#.....#.....#..#",
            "#.#####.#####.###..#",
            "#.....#.....#......#",
            "#.###.#####.#.####.#",
            "#...#..B..#.#....#.#",
            "#.#.#######.###.#..#",
            "#.#.....T.....#.#..#",
            "#.####.#####.##.#..#",
            "#....#....P#....#..#",
            "#.##.#.#####.##.#..#",
            "#..#.....B.....#...#",
            "#.............T#...#",
            "####################",
        )
    },
    {
        "name": "BuiltIn-H",
        "diff": 2,
        "lines": (
            "####################",
            "#..#..#..###..#..T.#",
            "#..#..#..#.#..#.#..#",
            "#.....#..#.#....#..#",
            "#.###.###.#.#####.##",
            "#...#.....#.....#..#",
            "#.#.#####.#####.#..#",
            "#.#..T..#.....#....#",
            "#.#####.#.###.####.#",
            "#.....#.#...#....#.#",
            "#.###.#.###.#.##.#.#",
            "#...#.#..B..#..#...#",
            "#.#.#.#######.###.##",
            "#.#.#..T.....B....##",
            "#.#.####.#####.##..#",
            "#.#....#.....#..#..#",
            "#.####.#####.#.##..#",
            "#..P....B....#..T..#",
            "#..#.........#.....#",
            "####################",
        )
    },
]

def next_level_matching(levels, cur, diff):
    n = len(levels)
    if n <= 1:
        return cur
    start = cur
    for _ in range(n):
        cur = (cur + 1) % n
        if levels[cur]["diff"] == diff:
            return cur
    return (start + 1) % n

def short_name(name, maxlen=12):
    return name if len(name) <= maxlen else name[:maxlen]

# -----------------------------
# Main
# -----------------------------
def main():
    gc.collect()

    spi = SPI(0, baudrate=40_000_000, polarity=1, phase=1,
              sck=Pin(PIN_LCD_SCK), mosi=Pin(PIN_LCD_MOSI), miso=None)
    disp = ST7789(spi, Pin(PIN_LCD_DC, Pin.OUT), Pin(PIN_LCD_RST, Pin.OUT))

    btn = Buttons()
    joy = Joy()
    rx = LevelReceiver()

    i2c = I2C(1, scl=Pin(PIN_I2C1_SCL), sda=Pin(PIN_I2C1_SDA), freq=400_000)
    imu = MMA7660(i2c)

    # store only packets (small)
    levels = list(DEFAULT_LEVELS)
    cur = 0

    # runtime level buffer (reused, no clone)
    base_pkt = levels[cur]
    lvl = LevelRuntime()
    lvl.load_from_20x20_lines(base_pkt["name"], base_pkt["diff"], base_pkt["lines"])

    diff = lvl.diff
    move_period = MOVE_PERIOD_BY_DIFF[diff]

    tilt_on = False
    last_move_ms = 0

    menu = False
    menu_idx = 0
    win_flash = 0

    print("READY")  # PC端会忽略它，不会当 ACK
    draw_level(disp, lvl, "READY 40x40 (real corridor width)", C_DIM)

    while True:
        try:
            pkt = rx.tick()
            if pkt:
                # store only the 20x20 packet (small)
                levels.append(pkt)
                cur = len(levels) - 1
                base_pkt = levels[cur]
                lvl.load_from_20x20_lines(base_pkt["name"], base_pkt["diff"], base_pkt["lines"])
                diff = lvl.diff
                move_period = MOVE_PERIOD_BY_DIFF[diff]
                draw_level(disp, lvl, "Loaded: %s" % short_name(lvl.name), C_OK)
                gc.collect()
                time.sleep_ms(220)

            press_a = btn.edge_falling("a", btn.a)
            press_b = btn.edge_falling("b", btn.b)
            press_s = btn.edge_falling("start", btn.start)
            press_sel = btn.edge_falling("sel", btn.sel)

            if not menu:
                if press_a:
                    menu = True
                    menu_idx = 0
                    draw_menu(disp, menu_idx, tilt_on, diff)
                    time.sleep_ms(120)
                    continue

                if press_s:
                    # restart from base_pkt (no clone)
                    lvl.load_from_20x20_lines(base_pkt["name"], base_pkt["diff"], base_pkt["lines"])
                    diff = lvl.diff
                    move_period = MOVE_PERIOD_BY_DIFF[diff]
                    draw_level(disp, lvl, "Restart", C_DIM)
                    gc.collect()
                    time.sleep_ms(130)

                if press_b:
                    cur = next_level_matching(levels, cur, diff)
                    base_pkt = levels[cur]
                    lvl.load_from_20x20_lines(base_pkt["name"], base_pkt["diff"], base_pkt["lines"])
                    diff = lvl.diff
                    move_period = MOVE_PERIOD_BY_DIFF[diff]
                    draw_level(disp, lvl, "Next(diff): %s" % short_name(lvl.name), C_DIM)
                    gc.collect()
                    time.sleep_ms(160)

                now = time.ticks_ms()
                if time.ticks_diff(now, last_move_ms) > move_period:
                    dx = dy = 0

                    # Task5: tilt control toggle in menu
                    if tilt_on and imu.ok:
                        x, y, z = imu.read_xyz()
                        if abs(x) > 6 or abs(y) > 6:
                            if abs(x) > abs(y):
                                dx = 1 if x > 0 else -1
                            else:
                                dy = 1 if y > 0 else -1
                    else:
                        dx, dy = joy.dir(dead=5000)

                    if dx or dy:
                        if try_move(lvl, dx, dy):
                            last_move_ms = now
                            if lvl.win():
                                win_flash = 10

                    idx = cur + 1
                    total = len(levels)
                    dch = ["E", "N", "H"][diff]
                    ctrl = "T" if (tilt_on and imu.ok) else "J"
                    banner = "%d/%d %s %s B%d S%d %s" % (
                        idx, total, short_name(lvl.name, 7), dch, len(lvl.boxes), move_period, ctrl
                    )

                    if win_flash > 0:
                        draw_level(disp, lvl, "WIN! B next / Start restart", C_OK)
                        win_flash -= 1
                    else:
                        draw_level(disp, lvl, banner, C_TXT)

            else:
                if press_b or press_sel:
                    menu = False
                    draw_level(disp, lvl, "Back", C_DIM)
                    time.sleep_ms(120)
                    continue

                dx, dy = joy.dir(dead=7000)
                if dy != 0:
                    menu_idx = (menu_idx + (1 if dy > 0 else -1)) % 5
                    draw_menu(disp, menu_idx, tilt_on, diff)
                    time.sleep_ms(150)

                if press_a:
                    if menu_idx == 0:
                        menu = False
                        draw_level(disp, lvl, "Continue", C_DIM)
                        time.sleep_ms(110)
                    elif menu_idx == 1:
                        lvl.load_from_20x20_lines(base_pkt["name"], base_pkt["diff"], base_pkt["lines"])
                        menu = False
                        draw_level(disp, lvl, "Restart", C_DIM)
                        gc.collect()
                        time.sleep_ms(130)
                    elif menu_idx == 2:
                        cur = next_level_matching(levels, cur, diff)
                        base_pkt = levels[cur]
                        lvl.load_from_20x20_lines(base_pkt["name"], base_pkt["diff"], base_pkt["lines"])
                        diff = lvl.diff
                        move_period = MOVE_PERIOD_BY_DIFF[diff]
                        menu = False
                        draw_level(disp, lvl, "Next(diff)", C_DIM)
                        gc.collect()
                        time.sleep_ms(140)
                    elif menu_idx == 3:
                        diff = (diff + 1) % 3
                        move_period = MOVE_PERIOD_BY_DIFF[diff]
                        draw_menu(disp, menu_idx, tilt_on, diff)
                        time.sleep_ms(120)
                    elif menu_idx == 4:
                        tilt_on = not tilt_on
                        draw_menu(disp, menu_idx, tilt_on, diff)
                        time.sleep_ms(120)

            time.sleep_ms(10)

        except Exception as e:
            # never crash back to REPL (prevents PC seeing '>')
            try:
                print("ERR runtime", str(e))
            except Exception:
                pass
            gc.collect()
            time.sleep_ms(50)

main()
