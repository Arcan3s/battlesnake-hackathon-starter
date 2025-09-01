# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# Aggressive-Survivor Battlesnake
# - Survive first: walls, bodies, losing head-to-heads avoided
# - Hunt fast: seek winning head-to-heads, cut off routes (trap/pressure)
# - Eat only when needed or when it helps win races
#
# Docs: https://docs.battlesnake.com

import random
import typing
from collections import deque

Coord = typing.Dict[str, int]
GameState = typing.Dict[str, typing.Any]

# -------------------------
# Tunables
# -------------------------
HUNGER_THRESHOLD = 35         # Eat when at/below this health
AGGRESSION = 1.25             # >1 => more weight on attack; <1 => more cautious
TRAP_RADIUS = 4               # Consider opponents within this Manhattan distance for trap scoring
TRAP_SPACE_THRESH = 10        # If our move leaves an opponent with < this many cells, we boost that move
SPACE_LIMIT = 96              # Max nodes explored in flood fill for speed
HEAD_BUFFER_IF_SMALLER = True # If we are smaller, avoid all potential opponent head cells

# -------------------------
# Helpers
# -------------------------

DIRECTIONS = {
    "up":    (0, 1),
    "down":  (0, -1),
    "left":  (-1, 0),
    "right": (1, 0),
}

def add(a: Coord, b: typing.Tuple[int, int]) -> Coord:
    return {"x": a["x"] + b[0], "y": a["y"] + b[1]}

def in_bounds(pt: Coord, width: int, height: int) -> bool:
    return 0 <= pt["x"] < width and 0 <= pt["y"] < height

def manhattan(a: Coord, b: Coord) -> int:
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])

def all_body_cells(game_state: GameState) -> typing.Set[typing.Tuple[int,int]]:
    occ = set()
    for s in game_state["board"]["snakes"]:
        for seg in s["body"]:
            occ.add((seg["x"], seg["y"]))
    return occ

def next_heads_set(game_state: GameState) -> typing.Set[typing.Tuple[int,int]]:
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    poss = set()
    for s in game_state["board"]["snakes"]:
        h = s["head"]
        for dx, dy in DIRECTIONS.values():
            nx, ny = h["x"] + dx, h["y"] + dy
            if 0 <= nx < width and 0 <= ny < height:
                poss.add((nx, ny))
    return poss

def flood_fill_size(start: Coord, blocked: typing.Set[typing.Tuple[int,int]], width: int, height: int, limit: int = SPACE_LIMIT) -> int:
    key = (start["x"], start["y"])
    if key in blocked or not in_bounds(start, width, height):
        return 0
    seen = {key}
    q = deque([start])
    count = 0
    while q and count < limit:
        cur = q.popleft()
        count += 1
        for dx, dy in DIRECTIONS.values():
            nx, ny = cur["x"] + dx, cur["y"] + dy
            k = (nx, ny)
            if 0 <= nx < width and 0 <= ny < height and k not in blocked and k not in seen:
                seen.add(k)
                q.append({"x": nx, "y": ny})
    return count

def nearest(centre: Coord, points: typing.List[Coord]) -> typing.Optional[Coord]:
    return min(points, key=lambda p: manhattan(centre, p)) if points else None

def move_preferences_towards(src: Coord, dst: typing.Optional[Coord]) -> typing.List[str]:
    if not dst:
        return []
    dx = dst["x"] - src["x"]
    dy = dst["y"] - src["y"]
    prefs = []
    if abs(dx) >= abs(dy):
        if dx > 0: prefs.append("right")
        if dx < 0: prefs.append("left")
        if dy > 0: prefs.append("up")
        if dy < 0: prefs.append("down")
    else:
        if dy > 0: prefs.append("up")
        if dy < 0: prefs.append("down")
        if dx > 0: prefs.append("right")
        if dx < 0: prefs.append("left")
    return prefs

# -------------------------
# Battlesnake Handlers
# -------------------------

def info() -> typing.Dict:
    print("INFO (Aggressive-Survivor)")
    return {
        "apiversion": "1",
        "author": "mm-b-aggressive",
        "color": "#e63946",             # spicy red
        "head": "fang",
        "tail": "bolt",
    }

def start(game_state: GameState):
    print("GAME START")

def end(game_state: GameState):
    print("GAME OVER\n")

def move(game_state: GameState) -> typing.Dict:
    board = game_state["board"]
    width, height = board["width"], board["height"]
    you = game_state["you"]

    my_head: Coord = you["head"]
    my_body: typing.List[Coord] = you["body"]
    my_tail: Coord = my_body[-1]
    my_len: int = you["length"]
    my_health: int = you["health"]

    # 1) Base safety: no reversing into neck
    is_move_safe = {m: True for m in DIRECTIONS.keys()}
    if len(my_body) >= 2:
        neck = my_body[1]
        if neck["x"] < my_head["x"]: is_move_safe["left"] = False
        if neck["x"] > my_head["x"]: is_move_safe["right"] = False
        if neck["y"] < my_head["y"]: is_move_safe["down"] = False
        if neck["y"] > my_head["y"]: is_move_safe["up"] = False

    # 2) Build occupancy & opponent info
    blocked = all_body_cells(game_state)
    blocked.discard((my_tail["x"], my_tail["y"]))  # tail often vacates

    opponents = [s for s in board["snakes"] if s["id"] != you["id"]]
    largest_opp = max((s["length"] for s in opponents), default=0)
    opp_heads = [s["head"] for s in opponents]
    opp_next_cells = next_heads_set(game_state)

    avoid_head_cells = set()
    if HEAD_BUFFER_IF_SMALLER and my_len <= largest_opp:
        avoid_head_cells = opp_next_cells

    # 3) Safe candidate moves
    candidates: typing.List[typing.Tuple[str, Coord]] = []
    for mv, (dx, dy) in DIRECTIONS.items():
        if not is_move_safe[mv]:
            continue
        nxt = {"x": my_head["x"] + dx, "y": my_head["y"] + dy}
        if not in_bounds(nxt, width, height):
            continue
        if (nxt["x"], nxt["y"]) in blocked:
            continue
        if (nxt["x"], nxt["y"]) in avoid_head_cells:
            continue
        candidates.append((mv, nxt))

    if not candidates:
        print(f"MOVE {game_state['turn']}: No safe candidates; panic 'down'")
        return {"move": "down"}

    # 4) Strategy
    foods = board["food"]
    want_food = my_health <= HUNGER_THRESHOLD and len(foods) > 0
    food_target = nearest(my_head, foods) if want_food else None
    target_head = nearest(my_head, opp_heads) if opp_heads else None

    # 5) Score candidates
    scored: typing.List[typing.Tuple[float, str]] = []

    for mv, nxt in candidates:
        space_score = flood_fill_size(nxt, blocked, width, height, limit=SPACE_LIMIT)

        food_score = 0.0
        if food_target:
            d_now = manhattan(my_head, food_target)
            d_next = manhattan(nxt, food_target)
            food_score = (d_now - d_next) * 2.5

        attack_score = 0.0
        if target_head:
            d_head_now = manhattan(my_head, target_head)
            d_head_next = manhattan(nxt, target_head)
            attack_score += (d_head_now - d_head_next) * 1.5 * AGGRESSION

            if d_head_next == 1:
                for s in opponents:
                    if s["head"] == target_head and my_len > s["length"]:
                        attack_score += 8.0 * AGGRESSION

        if opponents:
            sim_blocked = set(blocked)
            sim_blocked.add((nxt["x"], nxt["y"]))
            for opp in opponents:
                oh = opp["head"]
                if manhattan(oh, nxt) <= TRAP_RADIUS:
                    min_space = None
                    for dx, dy in DIRECTIONS.values():
                        cand = {"x": oh["x"] + dx, "y": oh["y"] + dy}
                        k = (cand["x"], cand["y"])
                        if not in_bounds(cand, width, height): 
                            continue
                        if k in sim_blocked:
                            continue
                        ssz = flood_fill_size(cand, sim_blocked, width, height, limit=SPACE_LIMIT)
                        if min_space is None or ssz < min_space:
                            min_space = ssz
                    if min_space is not None and min_space < TRAP_SPACE_THRESH:
                        size_diff = my_len - opp["length"]
                        attack_score += (6.0 + max(0, size_diff) * 0.5) * AGGRESSION

        cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
        dist_center_now = abs(my_head["x"] - cx) + abs(my_head["y"] - cy)
        dist_center_next = abs(nxt["x"] - cx) + abs(nxt["y"] - cy)
        center_bias = (dist_center_now - dist_center_next) * 0.2

        score = (
            space_score * 1.0
            + food_score
            + attack_score
            + center_bias
            + random.random() * 0.01
        )
        scored.append((score, mv))

    scored.sort(reverse=True)
    best_move = scored[0][1]
    print(f"MOVE {game_state['turn']}: {best_move}")
    return {"move": best_move}

# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
