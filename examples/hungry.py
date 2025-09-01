# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# Super Food Greedy Snake
# - Primary objective: minimize distance to the nearest food.
# - Minimal safety: avoid walls/bodies and don't reverse into neck.
# - Tie-breaker: choose the move with the most reachable free space.
#
# Docs: https://docs.battlesnake.com

import typing
from collections import deque
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

def in_bounds(p: Coord, w: int, h: int) -> bool:
    return 0 <= p["x"] < w and 0 <= p["y"] < h

def add(a: Coord, d: typing.Tuple[int, int]) -> Coord:
    return {"x": a["x"] + d[0], "y": a["y"] + d[1]}

def manhattan(a: Coord, b: Coord) -> int:
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])

def nearest_food(head: Coord, foods: typing.List[Coord]) -> typing.Optional[Coord]:
    if not foods:
        return None
    return min(foods, key=lambda f: manhattan(head, f))

def all_body_cells(game_state: GameState) -> typing.Set[typing.Tuple[int, int]]:
    occ = set()
    for s in game_state["board"]["snakes"]:
        for seg in s["body"]:
            occ.add((seg["x"], seg["y"]))
    return occ

def flood_fill_size(start: Coord, blocked: typing.Set[typing.Tuple[int, int]], w: int, h: int, limit: int = 200) -> int:
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

# -------------------------
# Battlesnake Handlers
# -------------------------

def info() -> typing.Dict:
    print("INFO (Food Greedy)")
    return {
        "apiversion": "1",
        "author": "mm-b-food-greedy",
        "color": "#ff9f1a",  # orange
        "head": "sand-worm",
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

    # 1) Do not reverse into neck
    illegal = set()
    if len(my_body) >= 2:
        neck = my_body[1]
        if neck["x"] < my_head["x"]: illegal.add("left")
        if neck["x"] > my_head["x"]: illegal.add("right")
        if neck["y"] < my_head["y"]: illegal.add("down")
        if neck["y"] > my_head["y"]: illegal.add("up")

    # 2) Occupancy (allow stepping onto current tail — likely vacates unless we eat)
    blocked = all_body_cells(game_state)
    blocked.discard((my_tail["x"], my_tail["y"]))

    # 3) Nearest food target
    foods: typing.List[Coord] = board["food"]
    target = nearest_food(my_head, foods)

    # 4) Build candidate moves
    candidates: typing.List[typing.Tuple[str, Coord]] = []
    for mv, delta in DIRECTIONS.items():
        if mv in illegal:
            continue
        nxt = add(my_head, delta)
        if not in_bounds(nxt, width, height):
            continue
        if (nxt["x"], nxt["y"]) in blocked:
            continue
        candidates.append((mv, nxt))

    # If somehow no legal candidates, just pick any in-bounds non-reverse
    if not candidates:
        any_legal = [mv for mv, d in DIRECTIONS.items() if mv not in illegal and in_bounds(add(my_head, d), width, height)]
        mv = any_legal[0] if any_legal else "up"
        print(f"MOVE {game_state['turn']}: emergency '{mv}'")
        return {"move": mv}

    # 5) Score: get closer to food (huge weight), then prefer big open space
    scored: typing.List[typing.Tuple[float, str]] = []
    for mv, nxt in candidates:
        # Big greedy weight: reduce distance to food
        if target:
            d_now = manhattan(my_head, target)
            d_next = manhattan(nxt, target)
            toward_food = (d_now - d_next) * 1000.0  # BIG weight: always go for food
        else:
            toward_food = 0.0

        # Tie-breaker: prefer more reachable space after moving
        sim_blocked = set(blocked)
        sim_blocked.add((nxt["x"], nxt["y"]))
        space = flood_fill_size(nxt, sim_blocked, width, height, limit=200)

        score = toward_food + space * 0.5 + random.random() * 0.01
        scored.append((score, mv))

    scored.sort(reverse=True)
    best_move = scored[0][1]
    print(f"MOVE {game_state['turn']}: {best_move}")
    return {"move": best_move}

# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
