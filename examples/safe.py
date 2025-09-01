# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# A slightly smarter example snake:
# - Avoids walls/self/other bodies
# - Avoids risky head-to-heads with equal/larger snakes
# - Seeks nearest food when low on health
# - Otherwise prefers moves with the most open space (flood-fill)
#
# Docs: https://docs.battlesnake.com

import random
import typing
from collections import deque

Coord = typing.Dict[str, int]
GameState = typing.Dict[str, typing.Any]

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

def board_occupied_cells(game_state: GameState) -> typing.Set[typing.Tuple[int,int]]:
    """All body cells of all snakes (including our own)."""
    occ = set()
    for s in game_state["board"]["snakes"]:
        for seg in s["body"]:
            occ.add((seg["x"], seg["y"]))
    return occ

def next_heads_of_opponents(game_state: GameState) -> typing.Set[typing.Tuple[int,int]]:
    """
    Cells that opponent heads could move into next turn.
    Used to avoid risky head-to-heads vs equal/larger snakes.
    """
    danger = set()
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    for s in game_state["board"]["snakes"]:
        head = s["head"]
        for dx, dy in DIRECTIONS.values():
            nx, ny = head["x"] + dx, head["y"] + dy
            if 0 <= nx < width and 0 <= ny < height:
                danger.add((nx, ny))
    return danger

def flood_fill_size(start: Coord, blocked: typing.Set[typing.Tuple[int,int]], width: int, height: int, limit: int = 64) -> int:
    """
    Count how many cells are reachable from start without crossing blocked cells.
    Stops early at 'limit' to keep it fast.
    """
    start_key = (start["x"], start["y"])
    if start_key in blocked or not in_bounds(start, width, height):
        return 0
    seen = {start_key}
    q = deque([start])
    count = 0
    while q and count < limit:
        cur = q.popleft()
        count += 1
        for dx, dy in DIRECTIONS.values():
            nx, ny = cur["x"] + dx, cur["y"] + dy
            key = (nx, ny)
            if 0 <= nx < width and 0 <= ny < height and key not in blocked and key not in seen:
                seen.add(key)
                q.append({"x": nx, "y": ny})
    return count

def nearest_food(my_head: Coord, foods: typing.List[Coord]) -> typing.Optional[Coord]:
    if not foods:
        return None
    return min(foods, key=lambda f: manhattan(my_head, f))

def move_towards(src: Coord, dst: Coord) -> typing.List[str]:
    """
    Return move preferences that step closer (by Manhattan) to dst.
    We'll still safety-check these moves later.
    """
    prefs = []
    if dst is None:
        return prefs
    dx = dst["x"] - src["x"]
    dy = dst["y"] - src["y"]
    # Prefer axis with greater distance first
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
    print("INFO")
    return {
        "apiversion": "1",
        "author": "mm-b-example",   # <-- put your Battlesnake username
        "color": "#1d7bff",
        "head": "smart-caterpillar",
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
    my_length = you["length"]
    my_health = you["health"]

    # Disallow reversing into our neck
    is_move_safe = {m: True for m in DIRECTIONS.keys()}
    if len(my_body) >= 2:
        neck = my_body[1]
        if neck["x"] < my_head["x"]: is_move_safe["left"] = False
        if neck["x"] > my_head["x"]: is_move_safe["right"] = False
        if neck["y"] < my_head["y"]: is_move_safe["down"] = False
        if neck["y"] > my_head["y"]: is_move_safe["up"] = False

    # Build blocked cells: everyone’s body, except allow moving into our tail
    # if it will move away this turn (safe approximation: allow our current tail cell).
    blocked = board_occupied_cells(game_state)
    my_tail = my_body[-1]
    blocked.discard((my_tail["x"], my_tail["y"]))

    # Head-to-head danger map
    opp_next_heads = next_heads_of_opponents(game_state)

    # Pre-check each candidate move for hard safety:
    # - in bounds
    # - not into a body (blocked)
    # - avoid head-to-head ties/losses (if an equal or larger snake could also move there)
    #   We'll approximate by avoiding ANY potential opponent head cell unless we're strictly larger.
    largest_opp = 0
    for s in board["snakes"]:
        if s["id"] != you["id"]:
            largest_opp = max(largest_opp, s["length"])
    avoid_head_cells = opp_next_heads if my_length <= largest_opp else set()

    candidates = []
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
        # No safe moves—pick any legal (or fallback "down") to comply with API
        print(f"MOVE {game_state['turn']}: No safe moves! Panic move.")
        return {"move": "down"}

    # Strategy:
    # 1) If low health, bias toward nearest food (but still ensure safety).
    foods = board["food"]
    want_food = my_health <= 50 and len(foods) > 0
    food_target = nearest_food(my_head, foods) if want_food else None

    # 2) Score candidates:
    #    - If chasing food: prefer moves that reduce distance to target.
    #    - Always prefer moves with larger flood-fill space.
    #    - Add a tiny random jitter to break ties.
    scored = []
    for mv, nxt in candidates:
        # Flood fill assumes cell we move into is now "us"
        # Temporarily mark our current head as free (since we move) and block new body except tail
        # We'll approximate by using existing 'blocked' (already liberal about our tail)
        space = flood_fill_size(nxt, blocked, width, height, limit=96)

        toward = 0
        if food_target:
            d_now = manhattan(my_head, food_target)
            d_next = manhattan(nxt, food_target)
            toward = (d_now - d_next)  # positive if we get closer

        score = (space * 1.0) + (toward * 3.0) + random.random() * 0.01
        scored.append((score, mv))

    scored.sort(reverse=True)
    best_move = scored[0][1]

    print(f"MOVE {game_state['turn']}: {best_move}")
    return {"move": best_move}

# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
