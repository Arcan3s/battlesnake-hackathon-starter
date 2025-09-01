# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# Super Food Greedy Battlesnake
# - Extremely food-seeking: races to food even when healthy
# - Chooses "winnable" food (closer than opponents when possible)
# - Uses BFS distances to prefer shortest path toward target food
# - Survival checks: walls, bodies, losing head-to-heads avoided
# - Penalizes moves that collapse our future space
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
SPACE_LIMIT = 120          # BFS/flood cap for speed
FOOD_WEIGHT = 8.0          # How strongly to chase food per step of improvement
WINNABLE_FOOD_BONUS = 10.0 # Big bonus if we are strictly closer than all opponents
SPACE_WEIGHT = 0.8         # Mild penalty for low future space (survival bias)
HEAD_TIE_AVOID = True      # Avoid equal/larger head-to-head cells

DIRECTIONS = {
    "up":    (0, 1),
    "down":  (0, -1),
    "left":  (-1, 0),
    "right": (1, 0),
}

def in_bounds(pt: Coord, w: int, h: int) -> bool:
    return 0 <= pt["x"] < w and 0 <= pt["y"] < h

def manhattan(a: Coord, b: Coord) -> int:
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])

def all_body_cells(gs: GameState) -> typing.Set[typing.Tuple[int,int]]:
    occ = set()
    for s in gs["board"]["snakes"]:
        for seg in s["body"]:
            occ.add((seg["x"], seg["y"]))
    return occ

def next_heads_set(gs: GameState) -> typing.Set[typing.Tuple[int,int]]:
    w = gs["board"]["width"]; h = gs["board"]["height"]
    poss = set()
    for s in gs["board"]["snakes"]:
        hx, hy = s["head"]["x"], s["head"]["y"]
        for dx, dy in DIRECTIONS.values():
            nx, ny = hx + dx, hy + dy
            if 0 <= nx < w and 0 <= ny < h:
                poss.add((nx, ny))
    return poss

def flood_fill_size(start: Coord, blocked: typing.Set[typing.Tuple[int,int]], w: int, h: int, limit: int = SPACE_LIMIT) -> int:
    k = (start["x"], start["y"])
    if k in blocked or not in_bounds(start, w, h):
        return 0
    seen = {k}
    q = deque([start])
    n = 0
    while q and n < limit:
        cur = q.popleft()
        n += 1
        for dx, dy in DIRECTIONS.values():
            nx, ny = cur["x"] + dx, cur["y"] + dy
            kk = (nx, ny)
            if 0 <= nx < w and 0 <= ny < h and kk not in blocked and kk not in seen:
                seen.add(kk)
                q.append({"x": nx, "y": ny})
    return n

def bfs_distance(start: Coord, target: Coord, blocked: typing.Set[typing.Tuple[int,int]], w: int, h: int, limit: int = SPACE_LIMIT) -> typing.Optional[int]:
    """Shortest steps from start to target (4-neighbor), avoiding blocked; None if unreachable."""
    if (start["x"], start["y"]) in blocked or (target["x"], target["y"]) in blocked:
        return None
    if start == target:
        return 0
    seen = {(start["x"], start["y"])}
    q = deque([(start, 0)])
    steps = 0
    while q and steps < limit:
        cur, dist = q.popleft()
        for dx, dy in DIRECTIONS.values():
            nx, ny = cur["x"] + dx, cur["y"] + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            k = (nx, ny)
            if k in blocked or k in seen:
                continue
            if nx == target["x"] and ny == target["y"]:
                return dist + 1
            seen.add(k)
            q.append(({"x": nx, "y": ny}, dist + 1))
        steps += 1
    return None

def nearest_food(head: Coord, foods: typing.List[Coord]) -> typing.Optional[Coord]:
    if not foods:
        return None
    return min(foods, key=lambda f: manhattan(head, f))

def info() -> typing.Dict:
    print("INFO (Super Food Greedy)")
    return {
        "apiversion": "1",
        "author": "mm-b-super-greedy",
        "color": "#ffb703",   # mango
        "head": "sand-worm",
        "tail": "fat-rattle",
    }

def start(game_state: GameState):
    print("GAME START")

def end(game_state: GameState):
    print("GAME OVER\n")

def move(game_state: GameState) -> typing.Dict:
    board = game_state["board"]
    w, h = board["width"], board["height"]
    you = game_state["you"]

    head: Coord = you["head"]
    body: typing.List[Coord] = you["body"]
    tail: Coord = body[-1]
    my_len: int = you["length"]

    # Prevent reversing into neck
    is_safe = {m: True for m in DIRECTIONS.keys()}
    if len(body) >= 2:
        neck = body[1]
        if neck["x"] < head["x"]: is_safe["left"] = False
        if neck["x"] > head["x"]: is_safe["right"] = False
        if neck["y"] < head["y"]: is_safe["down"] = False
        if neck["y"] > head["y"]: is_safe["up"] = False

    blocked = all_body_cells(game_state)
    # allow our current tail (often vacates)
    blocked.discard((tail["x"], tail["y"]))

    opponents = [s for s in board["snakes"] if s["id"] != you["id"]]
    opp_heads = [s["head"] for s in opponents]
    largest_opp = max((s["length"] for s in opponents), default=0)
    opp_next = next_heads_set(game_state)

    # Avoid equal-or-larger head collision squares
    avoid_head = opp_next if (HEAD_TIE_AVOID and my_len <= largest_opp) else set()

    # Build candidate moves with base safety
    candidates: typing.List[typing.Tuple[str, Coord]] = []
    for mv, (dx, dy) in DIRECTIONS.items():
        if not is_safe[mv]:
            continue
        nxt = {"x": head["x"] + dx, "y": head["y"] + dy}
        if not in_bounds(nxt, w, h):
            continue
        if (nxt["x"], nxt["y"]) in blocked:
            continue
        if (nxt["x"], nxt["y"]) in avoid_head:
            continue
        candidates.append((mv, nxt))

    if not candidates:
        print(f"MOVE {game_state['turn']}: No safe candidates; panic 'down'")
        return {"move": "down"}

    foods: typing.List[Coord] = board["food"]

    # Choose a food target:
    # 1) Prefer foods where we are strictly closer than any opponent (winnable)
    # 2) Otherwise nearest overall
    target = None
    if foods:
        # compute Manhattan distances to speed filter (admissible for BFS)
        best_winnable = None
        best_winnable_dist = None

        for f in foods:
            d_me = manhattan(head, f)
            d_opp_min = min((manhattan(oh, f) for oh in opp_heads), default=1_000_000)
            if d_me < d_opp_min:  # strictly closer than all opponents
                if best_winnable is None or d_me < best_winnable_dist:
                    best_winnable = f
                    best_winnable_dist = d_me

        target = best_winnable if best_winnable is not None else nearest_food(head, foods)

    # Score moves: huge weight on decreasing BFS distance to target food,
    # plus a winnable-food bonus, minus penalty for tiny reachable space.
    scored: typing.List[typing.Tuple[float, str]] = []

    for mv, nxt in candidates:
        space = flood_fill_size(nxt, blocked, w, h, limit=SPACE_LIMIT)

        food_score = 0.0
        bonus = 0.0
        if target:
            # Use BFS distance (safer than Manhattan in mazes)
            d_now = bfs_distance(head, target, blocked, w, h, limit=SPACE_LIMIT)
            d_next = bfs_distance(nxt, target, blocked, w, h, limit=SPACE_LIMIT)

            # Reward moves that shorten the true path; if unreachable from either, give tiny random
            if d_now is not None and d_next is not None:
                food_score = (d_now - d_next) * FOOD_WEIGHT
            elif d_now is None and d_next is not None:
                # We couldn't reach before but can after ⇒ big gain
                food_score = 1.5 * FOOD_WEIGHT

            # If this target is "winnable" by Manhattan tie-break, add a big flat bonus
            d_me_manh = manhattan(nxt, target)
            d_opp_manh = min((manhattan(oh, target) for oh in opp_heads), default=1_000_000)
            if d_me_manh < d_opp_manh:
                bonus += WINNABLE_FOOD_BONUS

        # Penalize cramped futures (but not too hard—still greedy)
        space_penalty = 0.0
        if space < 10:
            space_penalty = (10 - space) * SPACE_WEIGHT

        score = food_score + bonus - space_penalty + random.random() * 0.01
        scored.append((score, mv))

    scored.sort(reverse=True)
    best_move = scored[0][1]
    print(f"MOVE {game_state['turn']}: {best_move}")
    return {"move": best_move}

# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
