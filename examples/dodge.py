# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# Dodge Snake
# - Always prioritizes distance from other snakes (heads first, then bodies)
# - Ignores food and aggression; survival-by-avoidance
# - Avoids opponent "threat cells" (where their heads could move next turn)

import typing
from collections import deque
import math
import random

Coord = typing.Dict[str, int]
GameState = typing.Dict[str, typing.Any]

DIRECTIONS: typing.Dict[str, typing.Tuple[int, int]] = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}

# -------------------------
# Helpers
# -------------------------

def add(a: Coord, d: typing.Tuple[int, int]) -> Coord:
    return {"x": a["x"] + d[0], "y": a["y"] + d[1]}

def in_bounds(pt: Coord, w: int, h: int) -> bool:
    return 0 <= pt["x"] < w and 0 <= pt["y"] < h

def manhattan(a: Coord, b: Coord) -> int:
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])

def all_body_cells(game_state: GameState) -> typing.Set[typing.Tuple[int, int]]:
    occ = set()
    for s in game_state["board"]["snakes"]:
        for seg in s["body"]:
            occ.add((seg["x"], seg["y"]))
    return occ

def opponent_heads(game_state: GameState, you_id: str) -> typing.List[Coord]:
    return [s["head"] for s in game_state["board"]["snakes"] if s["id"] != you_id]

def next_head_cells(game_state: GameState) -> typing.Set[typing.Tuple[int, int]]:
    w, h = game_state["board"]["width"], game_state["board"]["height"]
    cells = set()
    for s in game_state["board"]["snakes"]:
        hx, hy = s["head"]["x"], s["head"]["y"]
        for dx, dy in DIRECTIONS.values():
            nx, ny = hx + dx, hy + dy
            if 0 <= nx < w and 0 <= ny < h:
                cells.add((nx, ny))
    return cells

def flood_fill_size(start: Coord, blocked: typing.Set[typing.Tuple[int, int]], w: int, h: int, limit: int = 160) -> int:
    key = (start["x"], start["y"])
    if key in blocked or not in_bounds(start, w, h):
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
            if 0 <= nx < w and 0 <= ny < h and k not in blocked and k not in seen:
                seen.add(k)
                q.append({"x": nx, "y": ny})
    return count

def min_dist_to_points(p: Coord, points: typing.Iterable[Coord]) -> int:
    best = math.inf
    for q in points:
        d = manhattan(p, q)
        if d < best:
            best = d
    return int(best) if best != math.inf else 9999

# -------------------------
# Battlesnake Handlers
# -------------------------

def info() -> typing.Dict:
    print("INFO (Dodge Snake)")
    return {
        "apiversion": "1",
        "author": "mm-b-dodge",
        "color": "#00b894",  # teal
        "head": "safe",
        "tail": "round-bum",
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

    # 1) Basic "no reverse" rule
    illegal = set()
    if len(my_body) >= 2:
        neck = my_body[1]
        if neck["x"] < my_head["x"]: illegal.add("left")
        if neck["x"] > my_head["x"]: illegal.add("right")
        if neck["y"] < my_head["y"]: illegal.add("down")
        if neck["y"] > my_head["y"]: illegal.add("up")

    # 2) Occupancy & threats
    blocked = all_body_cells(game_state)

    # Allow stepping into our current tail (it usually moves away unless we eat;
    # we aren't pursuing food, so this is a reasonable survival heuristic).
    blocked.discard((my_tail["x"], my_tail["y"]))

    opp_heads = opponent_heads(game_state, you_id=you["id"])
    opp_threat_cells = next_head_cells(game_state)  # where any head could move next

    # 3) Candidate moves that are in-bounds, not reversing, not into bodies, not into head-threat cells
    candidates: typing.List[typing.Tuple[str, Coord]] = []
    for mv, delta in DIRECTIONS.items():
        if mv in illegal:
            continue
        nxt = add(my_head, delta)
        if not in_bounds(nxt, width, height):
            continue
        if (nxt["x"], nxt["y"]) in blocked:
            continue
        if (nxt["x"], nxt["y"]) in opp_threat_cells:
            # ultra-conservative: avoid squares opponents could contest next tick
            continue
        candidates.append((mv, nxt))

    # If nothing passes ultra-conservative filter, relax the threat-cell check but keep bodies/walls
    if not candidates:
        for mv, delta in DIRECTIONS.items():
            if mv in illegal:
                continue
            nxt = add(my_head, delta)
            if not in_bounds(nxt, width, height):
                continue
            if (nxt["x"], nxt["y"]) in blocked:
                continue
            candidates.append((mv, nxt))

    # Still nothing? choose any legal in-bounds (even if into body—last resort)
    if not candidates:
        fallbacks = [mv for mv, d in DIRECTIONS.items() if mv not in illegal and in_bounds(add(my_head, d), width, height)]
        mv = fallbacks[0] if fallbacks else "up"
        print(f"MOVE {game_state['turn']}: emergency '{mv}'")
        return {"move": mv}

    # 4) Score moves:
    #    - Maximize distance to nearest opponent head (weight 1.0)
    #    - Maximize distance to nearest opponent body segment (weight 0.4)
    #    - Prefer larger reachable space via flood fill (weight 0.15)
    #    - Slight random jitter to break ties
    opp_body_coords = []
    for s in board["snakes"]:
        if s["id"] == you["id"]:
            continue
        opp_body_coords.extend(s["body"])

    scored: typing.List[typing.Tuple[float, str]] = []
    for mv, nxt in candidates:
        head_dist = min_dist_to_points(nxt, opp_heads) if opp_heads else 9999
        body_dist = min_dist_to_points(nxt, opp_body_coords) if opp_body_coords else 9999

        # Build a blocked set that assumes we take nxt
        sim_blocked = set(blocked)
        sim_blocked.add((nxt["x"], nxt["y"]))
        space = flood_fill_size(nxt, sim_blocked, width, height, limit=200)

        score = (
            head_dist * 1.0 +
            body_dist * 0.4 +
            space * 0.15 +
            random.random() * 0.01
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
