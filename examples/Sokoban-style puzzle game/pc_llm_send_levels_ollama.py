import time, random, re, argparse
import requests
import serial
from collections import deque

# ==========================
# Serial config
# ==========================
PORT = "COM11"
BAUD = 115200

# ==========================
# Level grid (wire format)
# ==========================
W = H = 20
DIRS = [(1,0), (-1,0), (0,1), (0,-1)]
RE_LINE = re.compile(r'^[#.PBT*+]{20}$')

# ==========================
# Expanded "subcell" grid (device physics + solver)
# Every 1 cell => 2x2 subcells
# ==========================
SCALE = 2
SW = W * SCALE
SH = H * SCALE
SDIRS = [(1,0), (-1,0), (0,1), (0,-1)]
def inbS(x,y): return 0 <= x < SW and 0 <= y < SH

# ==========================
# Ollama (optional seed)
# ==========================
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "llama3.1:8b"

# ==========================
# Difficulty design
# ==========================
DIFF_BOXES = [1, 2, 3]

DIFF_ROOM_CT      = [2, 3, 3]
DIFF_LOOP_BREAKS  = [14, 10, 7]
DIFF_EXTRA_BREAKS = [9,  7,  5]

DIFF_SCRAMBLE_PUSHES = [16, 26, 38]

MIN_BOX_PAIR_DIST   = [4, 5, 6]
MIN_TGT_PAIR_DIST   = [5, 6, 7]
MIN_BOX_TO_TGT_DIST = [7, 9, 11]

BORDER_MARGIN = 2

GEN_ATTEMPTS_PER_LEVEL = 360
MAX_PUSH_STATES = 120000
MAX_PUSH_DEPTH  = 260

# ==========================
# Serial helpers
# ==========================
def open_serial():
    ser = serial.Serial(PORT, BAUD, timeout=0.15, write_timeout=3)
    time.sleep(1.0)
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass
    return ser

def drain_serial(ser, ms=600):
    """清空设备端已有输出(含 >>> / > / READY / 旧日志)，避免干扰 ACK 判定。"""
    t0 = time.time()
    while (time.time() - t0) * 1000 < ms:
        try:
            s = ser.readline().decode("utf-8", errors="ignore").strip()
        except Exception:
            s = ""
        if not s:
            time.sleep(0.01)

def write_payload_chunked(ser, payload_bytes, chunk=256):
    i = 0
    n = len(payload_bytes)
    while i < n:
        ser.write(payload_bytes[i:i+chunk])
        i += chunk
        time.sleep(0.004)
    ser.flush()

def _is_repl_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    # 常见 REPL / Thonny 噪声
    if s in (">", ">>>", ">>", "....", "..."):
        return True
    if s.endswith(">>>") or s.endswith(">>") or s.endswith(">"):
        # 例如 "MPY: soft reboot" 后出现提示符
        if len(s) <= 5:
            return True
    if s.startswith("MicroPython") or s.startswith("MPY:"):
        return True
    return False

def wait_device_ack(ser, timeout_s=15.0):
    """只认 OK/ERR，忽略 '>' '>>>' 等 REPL 噪声。"""
    t0 = time.time()
    last_nonempty = ""
    while time.time() - t0 < timeout_s:
        raw = ser.readline()
        if not raw:
            continue
        s = raw.decode("utf-8", errors="ignore").strip()
        if not s:
            continue

        # 记录最后一条“非空”以便调试显示
        last_nonempty = s

        # 忽略噪声
        if _is_repl_noise(s):
            continue

        # 只接受 OK/ERR
        if s.startswith("OK") or s.startswith("ERR"):
            return s

        # 其它日志也忽略，但不退出
        # print("[DEV]", s)  # 需要的话可打开看设备日志

    return "(timeout, last=%r)" % (last_nonempty,)

# ==========================
# Frame format for device
# ==========================
def frame_level(name, diff, lines):
    out = [f"@LVL name={name} diff={diff} w=20 h=20"]
    out.extend(lines)
    out.append("@END")
    return "\n".join(out) + "\n"

# ==========================
# Ollama: seed only
# ==========================
def ollama_get_seed(diff):
    system = "You must output ONLY one integer number. No words."
    user = f"Give me one random integer seed for difficulty={diff}."
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": 0.8, "num_predict": 16},
    }
    try:
        r = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=3.0)
        r.raise_for_status()
        data = r.json()
        content = (data.get("message", {}) or {}).get("content", "") or ""
        m = re.search(r"-?\d+", content.strip())
        if not m:
            return None
        return int(m.group(0))
    except Exception:
        return None

# ==========================
# 20x20 helpers
# ==========================
def inb(x,y): return 0 <= x < W and 0 <= y < H

def border_ok(x,y,margin=BORDER_MARGIN):
    return (margin <= x <= W-1-margin-1) and (margin <= y <= H-1-margin-1)

def manhattan(a,b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def pairwise_min_dist(points):
    pts = list(points)
    if len(pts) <= 1:
        return 999
    md = 999
    for i in range(len(pts)):
        for j in range(i+1, len(pts)):
            md = min(md, manhattan(pts[i], pts[j]))
    return md

def bfs_walkable20(base, start, blocks=set()):
    sx,sy=start
    if base[sy][sx] == '#' or (sx,sy) in blocks:
        return set()
    q=deque([(sx,sy)])
    vis=set([(sx,sy)])
    while q:
        x,y=q.popleft()
        for dx,dy in DIRS:
            nx,ny=x+dx,y+dy
            if not inb(nx,ny): continue
            if (nx,ny) in vis: continue
            if base[ny][nx] == '#': continue
            if (nx,ny) in blocks: continue
            vis.add((nx,ny))
            q.append((nx,ny))
    return vis

def all_floor_connected20(base, player):
    floors=set()
    for y in range(H):
        for x in range(W):
            if base[y][x] != '#':
                floors.add((x,y))
    vis = bfs_walkable20(base, player, blocks=set())
    return floors == vis

def is_corner_dead20(base, x, y, targets):
    if (x,y) in targets:
        return False
    up    = (base[y-1][x] == '#')
    down  = (base[y+1][x] == '#')
    left  = (base[y][x-1] == '#')
    right = (base[y][x+1] == '#')
    return (up and left) or (up and right) or (down and left) or (down and right)

def cell_open4_20(base, x, y):
    for dx,dy in DIRS:
        nx,ny=x+dx,y+dy
        if not inb(nx,ny): return False
        if base[ny][nx] == '#':
            return False
    return True

def cell_open3_20(base, x, y):
    open_n = 0
    for dx,dy in DIRS:
        nx,ny=x+dx,y+dy
        if not inb(nx,ny): 
            continue
        if base[ny][nx] != '#':
            open_n += 1
    return open_n >= 3

# ==========================
# Expand 20x20 -> 40x40
# Objects at (2x,2y)
# ==========================
def expand_to_subgrid(base20, player20, boxes20, targets20):
    baseS = [['.' for _ in range(SW)] for _ in range(SH)]
    for y in range(H):
        for x in range(W):
            ch = base20[y][x]
            for yy in range(y*SCALE, y*SCALE+SCALE):
                for xx in range(x*SCALE, x*SCALE+SCALE):
                    baseS[yy][xx] = '#' if ch == '#' else '.'

    for x in range(SW):
        baseS[0][x]='#'; baseS[SH-1][x]='#'
    for y in range(SH):
        baseS[y][0]='#'; baseS[y][SW-1]='#'

    px,py = player20
    pS = (px*SCALE, py*SCALE)
    bS = set((bx*SCALE, by*SCALE) for (bx,by) in boxes20)
    tS = set((tx*SCALE, ty*SCALE) for (tx,ty) in targets20)
    return baseS, pS, bS, tS

# ==========================
# Subgrid solver
# ==========================
def bfs_walkableS(baseS, startS, blocks=set()):
    sx,sy = startS
    if baseS[sy][sx] == '#' or (sx,sy) in blocks:
        return set()
    q=deque([(sx,sy)])
    vis=set([(sx,sy)])
    while q:
        x,y=q.popleft()
        for dx,dy in SDIRS:
            nx,ny=x+dx,y+dy
            if not inbS(nx,ny): continue
            if (nx,ny) in vis: continue
            if baseS[ny][nx] == '#': continue
            if (nx,ny) in blocks: continue
            vis.add((nx,ny))
            q.append((nx,ny))
    return vis

def canonical_playerS(baseS, playerS, boxesS):
    reach = bfs_walkableS(baseS, playerS, blocks=set(boxesS))
    if not reach:
        return None, None
    return min(reach), reach

def is_corner_deadS(baseS, x, y, targetsS):
    if (x,y) in targetsS:
        return False
    up    = (baseS[y-1][x] == '#')
    down  = (baseS[y+1][x] == '#')
    left  = (baseS[y][x-1] == '#')
    right = (baseS[y][x+1] == '#')
    return (up and left) or (up and right) or (down and left) or (down and right)

def solvable_push_bfs_subgrid(baseS, playerS, boxesS, targetsS):
    boxes0 = frozenset(boxesS)
    tgt = frozenset(targetsS)

    for (bx,by) in boxes0:
        if is_corner_deadS(baseS, bx, by, tgt):
            return False

    cp, _ = canonical_playerS(baseS, playerS, boxes0)
    if cp is None:
        return False

    q=deque([(boxes0, playerS, 0)])
    seen=set([(boxes0, cp)])

    expansions=0
    while q:
        bxs, ppos, depth = q.popleft()
        if bxs == tgt:
            return True
        if depth >= MAX_PUSH_DEPTH:
            continue

        expansions += 1
        if expansions > MAX_PUSH_STATES:
            return False

        cp, reach = canonical_playerS(baseS, ppos, bxs)
        if cp is None:
            continue

        bset=set(bxs)
        for (bx,by) in bset:
            for dx,dy in SDIRS:
                stand=(bx-dx, by-dy)
                dest =(bx+dx, by+dy)
                if not inbS(*stand) or not inbS(*dest):
                    continue
                if stand not in reach:
                    continue
                if baseS[dest[1]][dest[0]] == '#':
                    continue
                if dest in bset:
                    continue
                if is_corner_deadS(baseS, dest[0], dest[1], tgt):
                    continue

                nb=set(bset)
                nb.remove((bx,by))
                nb.add(dest)
                nb=frozenset(nb)
                np=(bx,by)

                ncp, _ = canonical_playerS(baseS, np, nb)
                if ncp is None:
                    continue

                key=(nb, ncp)
                if key in seen:
                    continue
                seen.add(key)
                q.append((nb, np, depth+1))

    return False

# ==========================
# Maze generation (20x20)
# ==========================
def gen_maze_base(diff, seed):
    rnd = random.Random(seed)
    base = [['#' for _ in range(W)] for _ in range(H)]

    nodes = [(x,y) for y in range(1,18,2) for x in range(1,18,2)]
    for x,y in nodes:
        base[y][x] = '.'

    stack=[]
    start = rnd.choice(nodes)
    visited=set([start])
    stack.append(start)

    def neighbors(cx,cy):
        cand=[]
        for dx,dy in [(2,0),(-2,0),(0,2),(0,-2)]:
            nx,ny=cx+dx,cy+dy
            if 1 <= nx <= 17 and 1 <= ny <= 17 and (nx,ny) not in visited:
                cand.append((nx,ny,dx,dy))
        return cand

    while stack:
        cx,cy = stack[-1]
        nbs = neighbors(cx,cy)
        if not nbs:
            stack.pop()
            continue
        nx,ny,dx,dy = rnd.choice(nbs)
        wx,wy = cx+dx//2, cy+dy//2
        base[wy][wx]='.'
        base[ny][nx]='.'
        visited.add((nx,ny))
        stack.append((nx,ny))

    room_ct = DIFF_ROOM_CT[diff]
    for _ in range(room_ct*10):
        if room_ct <= 0:
            break
        rx = rnd.randrange(3, 16)
        ry = rnd.randrange(3, 16)
        if not border_ok(rx, ry, 2):
            continue
        for yy in range(ry-1, ry+2):
            for xx in range(rx-1, rx+2):
                base[yy][xx] = '.'
        room_ct -= 1

    breaks = DIFF_LOOP_BREAKS[diff]
    for _ in range(breaks*7):
        if breaks <= 0:
            break
        x = rnd.randrange(2,18)
        y = rnd.randrange(2,18)
        if base[y][x] != '#':
            continue
        if not border_ok(x,y,1):
            continue
        open_n = sum(1 for dx,dy in DIRS if base[y+dy][x+dx]=='.')
        if open_n >= 2:
            base[y][x]='.'
            breaks -= 1

    extra = DIFF_EXTRA_BREAKS[diff]
    for _ in range(extra*10):
        if extra <= 0:
            break
        x = rnd.randrange(2,18)
        y = rnd.randrange(2,18)
        if base[y][x] != '#':
            continue
        if not border_ok(x,y,2):
            continue
        open_n = sum(1 for dx,dy in DIRS if base[y+dy][x+dx]=='.')
        if open_n >= 3:
            base[y][x]='.'
            extra -= 1

    for i in range(W):
        base[0][i]='#'; base[H-1][i]='#'
    for i in range(H):
        base[i][0]='#'; base[i][W-1]='#'
    return base

def random_floor_cells(base):
    floors=[]
    for y in range(1,H-1):
        for x in range(1,W-1):
            if base[y][x]=='.':
                floors.append((x,y))
    return floors

def pick_player(base, rnd):
    floors = random_floor_cells(base)
    rnd.shuffle(floors)
    for x,y in floors:
        if border_ok(x,y,2):
            return (x,y)
    return None

def pick_targets(base, n, rnd, stage, diff):
    floors = random_floor_cells(base)
    rnd.shuffle(floors)
    targets=set()

    tgt_need = max(3, MIN_TGT_PAIR_DIST[diff] - stage)
    for x,y in floors:
        if len(targets) == n:
            if pairwise_min_dist(targets) < tgt_need:
                return None
            return targets
        if not border_ok(x,y,2):
            continue
        if stage == 0:
            if not cell_open4_20(base,x,y):
                continue
        else:
            if not cell_open3_20(base,x,y):
                continue
        ok = True
        for t in targets:
            if manhattan((x,y), t) < tgt_need:
                ok = False
                break
        if not ok:
            continue
        targets.add((x,y))
    return None

def scramble_from_solved(base, player, targets, diff, rnd, stage):
    boxes=set(targets)
    pushes_need = DIFF_SCRAMBLE_PUSHES[diff]
    ok_push=0

    for _ in range(pushes_need*220):
        if ok_push >= pushes_need:
            break
        reachable = bfs_walkable20(base, player, blocks=set(boxes))
        if not reachable:
            continue
        moves=[]
        for (bx,by) in boxes:
            for dx,dy in DIRS:
                stand=(bx-dx, by-dy)
                dest =(bx+dx, by+dy)
                if not inb(*stand) or not inb(*dest):
                    continue
                if stand not in reachable:
                    continue
                if base[dest[1]][dest[0]] == '#':
                    continue
                if dest in boxes:
                    continue
                if dest not in targets:
                    if stage == 0:
                        if not cell_open4_20(base, dest[0], dest[1]):
                            continue
                    else:
                        if not cell_open3_20(base, dest[0], dest[1]):
                            continue
                    if is_corner_dead20(base, dest[0], dest[1], targets):
                        continue
                if not border_ok(dest[0], dest[1], 2):
                    continue
                moves.append((bx,by,dest))
        if not moves:
            continue
        bx,by,dest = rnd.choice(moves)
        boxes.remove((bx,by))
        boxes.add(dest)
        player=(bx,by)
        ok_push += 1

    if ok_push < max(10, pushes_need//2):
        return None

    box_need = max(3, MIN_BOX_PAIR_DIST[diff] - stage)
    if pairwise_min_dist(boxes) < box_need:
        return None
    return player, boxes

def build_lines(base, player, boxes, targets):
    out=[row[:] for row in base]
    for (x,y) in targets:
        out[y][x]='T'
    for (x,y) in boxes:
        out[y][x]='*' if out[y][x]=='T' else 'B'
    px,py=player
    out[py][px]='+' if out[py][px]=='T' else 'P'
    lines=["".join(r) for r in out]
    if len(lines)!=20 or any(len(r)!=20 for r in lines):
        raise ValueError("bad line size")
    if any(not RE_LINE.match(r) for r in lines):
        raise ValueError("bad chars / width")
    return lines

def initial_ok(base, player, boxes, targets, diff, stage):
    if not border_ok(player[0],player[1],2):
        return False
    for (x,y) in targets:
        if not border_ok(x,y,2):
            return False
    for (x,y) in boxes:
        if not border_ok(x,y,2):
            return False

    if not all_floor_connected20(base, player):
        return False

    for (bx,by) in boxes:
        if is_corner_dead20(base,bx,by,targets):
            return False

    box_need = max(3, MIN_BOX_PAIR_DIST[diff] - stage)
    tgt_need = max(3, MIN_TGT_PAIR_DIST[diff] - stage)
    if pairwise_min_dist(boxes) < box_need:
        return False
    if pairwise_min_dist(targets) < tgt_need:
        return False

    dist_need = max(5, MIN_BOX_TO_TGT_DIST[diff] - stage)
    mind = 999
    for b in boxes:
        dmin = min(manhattan(b,t) for t in targets)
        mind = min(mind, dmin)
    if mind < dist_need:
        return False

    return True

def ultra_safe_level(diff):
    base = [['.' for _ in range(W)] for _ in range(H)]
    for x in range(W):
        base[0][x]='#'; base[H-1][x]='#'
    for y in range(H):
        base[y][0]='#'; base[y][W-1]='#'

    for y in range(4, 16, 4):
        for x in range(4, 16, 4):
            base[y][x]='#'
    for x in range(2,18):
        if x not in (5,10,15):
            base[8][x]='#'
    for (x,y) in [(5,8),(10,8),(15,8)]:
        base[y][x]='.'

    if diff == 0:
        player=(3,16); boxes={(10,11)}; targets={(16,3)}
    elif diff == 1:
        player=(10,16); boxes={(7,12),(13,12)}; targets={(5,3),(15,3)}
    else:
        player=(10,16); boxes={(6,13),(10,11),(14,13)}; targets={(3,3),(10,3),(17,3)}

    return build_lines(base, player, boxes, targets)

def gen_one_level(diff, seed):
    rnd = random.Random(seed)
    for stage in (0,1,2):
        for attempt in range(GEN_ATTEMPTS_PER_LEVEL):
            s = seed + stage*99991 + attempt*10007
            rnd.seed(s)

            base = gen_maze_base(diff, s)
            player = pick_player(base, rnd)
            if not player:
                continue

            nbox = DIFF_BOXES[diff]
            targets = pick_targets(base, nbox, rnd, stage, diff)
            if not targets:
                continue

            scr = scramble_from_solved(base, player, targets, diff, rnd, stage)
            if not scr:
                continue
            player2, boxes = scr

            if not initial_ok(base, player2, boxes, targets, diff, stage):
                continue

            baseS, pS, bS, tS = expand_to_subgrid(base, player2, boxes, targets)
            if not solvable_push_bfs_subgrid(baseS, pS, bS, tS):
                continue

            lines = build_lines(base, player2, boxes, targets)

            if any(ch != "#" for ch in lines[0]):  continue
            if any(ch != "#" for ch in lines[-1]): continue
            if any(lines[y][0] != "#" or lines[y][-1] != "#" for y in range(H)): continue

            return lines
    return ultra_safe_level(diff)

def send_one_level_with_retry(ser, name, diff, lines, seed):
    payload = frame_level(name, diff, lines).encode("utf-8")
    # 发送前清一下输出，防止把旧的 '>' 当 last
    drain_serial(ser, ms=350)

    write_payload_chunked(ser, payload)
    ack = wait_device_ack(ser, timeout_s=15.0)
    if ack.startswith("(timeout"):
        # 只重发一次（有时候设备端刚好在画面刷新/菜单，错过了读）
        drain_serial(ser, ms=350)
        write_payload_chunked(ser, payload)
        ack = wait_device_ack(ser, timeout_s=15.0)
    print(f"[{name}] diff={diff} boxes={DIFF_BOXES[diff]} seed={seed} -> {ack}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", type=int, default=-1, help="0/1/2, -1 mix")
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--no-ollama", action="store_true")
    args = ap.parse_args()

    ser = open_serial()
    try:
        # 启动时先清一次串口，把 REPL 提示符/旧输出清掉
        drain_serial(ser, ms=800)

        for i in range(args.count):
            diff = (i % 3) if args.diff < 0 else args.diff
            name = f"AI-D{diff}-{i+1}"

            if args.no_ollama:
                seed = (int(time.time()*1000) ^ (diff<<8) ^ (i<<16)) & 0x7FFFFFFF
            else:
                seed = ollama_get_seed(diff)
                if seed is None:
                    seed = (int(time.time()*1000) ^ (diff<<8) ^ (i<<16)) & 0x7FFFFFFF

            lines = gen_one_level(diff, seed)
            send_one_level_with_retry(ser, name, diff, lines, seed)
            time.sleep(0.15)

        print("Done. On device press B to switch levels.")
    finally:
        try: ser.close()
        except Exception: pass

if __name__ == "__main__":
    main()
