# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# Circle Snake
# - Always moves in a clockwise rectangle around the board.
# - If not currently on an edge, it moves to the nearest edge first.
#
# Docs: https://docs.battlesnake.com

import typing

Coord = typing.Dict[str, int]
GameState = typing.Dict[str, typing.Any]

DIRECTIONS = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}

def in_bounds(pt: Coord, width: int, height: int) -> bool:
    return 0 <= pt["x"] < width and 0 <= pt["y"] < height

def step(head: Coord, dir_name: str) -> Coord:
    dx, dy = DIRECTIONS[dir_name]
    return {"x": head["x"] + dx, "y": head["y"] + dy}

def info() -> typing.Dict:
    print("INFO (Circle Snake)")
    return {
        "apiversion": "1",
        "author": "mm-b-circle",
        "color": "#6c5ce7",  # violet
        "head": "smile",
        "tail": "curled",
    }

def start(game_state: GameState):
    print("GAME START")

def end(game_state: GameState):
    print("GAME OVER\n")

def move(game_state: GameState) -> typing.Dict:
    board = game_state["board"]
    width, height = board["width"], board["height"]
    you = game_state["you"]

    head: Coord = you["head"]
    body: typing.List[Coord] = you["body"]

    # Avoid reversing into our neck (Battlesnake basic safety)
    illegal: typing.Set[str] = set()
    if len(body) >= 2:
        neck = body[1]
        if neck["x"] < head["x"]: illegal.add("left")
        if neck["x"] > head["x"]: illegal.add("right")
        if neck["y"] < head["y"]: illegal.add("down")
        if neck["y"] > head["y"]: illegal.add("up")

    x, y = head["x"], head["y"]
    top, bottom, left, right = height - 1, 0, 0, width - 1

    # If we're on the perimeter, follow a clockwise rectangle:
    # Top row → right, Right col → down, Bottom row → left, Left col → up
    if y == top and x < right:
        preferred = ["right", "down", "up", "left"]
    elif x == right and y > bottom:
        preferred = ["down", "left", "right", "up"]
    elif y == bottom and x > left:
        preferred = ["left", "up", "down", "right"]
    elif x == left and y < top:
        preferred = ["up", "right", "left", "down"]
    else:
        # Not on the edge: head toward the *nearest* edge, then the loop will take over.
        # Choose a direction that reduces distance to any edge (tie-broken in order up/right/left/down).
        dist_to_edges = {
            "up":    top - y,
            "down":  y - bottom,
            "left":  x - left,
            "right": right - x,
        }
        # Move toward the closest edge (smallest distance)
        toward = min(dist_to_edges, key=dist_to_edges.get)
        # Provide some fallbacks to keep motion if 'toward' is illegal
        if toward == "up":
            preferred = ["up", "right", "left", "down"]
        elif toward == "down":
            preferred = ["down", "left", "right", "up"]
        elif toward == "left":
            preferred = ["left", "down", "up", "right"]
        else:  # "right"
            preferred = ["right", "up", "down", "left"]

    # Pick the first preferred direction that is not reversing into neck and stays in-bounds.
    for mv in preferred:
        if mv in illegal:
            continue
        nxt = step(head, mv)
        if in_bounds(nxt, width, height):
            print(f"MOVE {game_state['turn']}: {mv}")
            return {"move": mv}

    # Absolute fallback (should rarely happen)
    print(f"MOVE {game_state['turn']}: fallback 'up'")
    return {"move": "up"}

# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
