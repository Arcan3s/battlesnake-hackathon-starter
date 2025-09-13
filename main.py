import heapq
import typing

# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This file can be a nice home for your Battlesnake logic and helper functions.
#
# To get you started we've included code to prevent your Battlesnake from moving backwards.
# For more info see docs.battlesnake.com
import random


# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
        "apiversion": "1",
        "author": "",  # TODO: Your Battlesnake Username
        "color": "#888888",  # TODO: Choose color
        "head": "default",  # TODO: Choose head
        "tail": "default",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def dijkstra(board_width, board_height, start, dangers, food):
    distances = {start: 0}
    queue = [(0, start)]
    came_from = {}

    while queue:
        current_dist, current = heapq.heappop(queue)

        if current in food:
            path = []
            while current != start:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        for dx, dy, direction in [(0, 1, "up"), (0, -1, "down"),
                                  (-1, 0, "left"), (1, 0, "right")]:
            nx, ny = current[0] + dx, current[1] + dy
            neighbor = (nx, ny)

            if (0 <= nx < board_width and 0 <= ny < board_height
                    and neighbor not in dangers):
                new_dist = current_dist + 1
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    heapq.heappush(queue, (new_dist, neighbor))
                    came_from[neighbor] = current

    return []


def move(game_state: typing.Dict) -> typing.Dict:
    my_head = game_state["you"]["body"][0]
    head_pos = (int(my_head["x"]), int(my_head["y"]))

    dangers = set()
    for snake in game_state["board"]["snakes"]:
        for segment in snake["body"]:
            dangers.add((int(segment["x"]), int(segment["y"])))

    food = [(int(f["x"]), int(f["y"])) for f in game_state["board"]["food"]]
    board_width = game_state["board"]["width"]
    board_height = game_state["board"]["height"]

    path = dijkstra(board_width, board_height, head_pos, dangers, food)

    if path:
        next_pos = path[0]
        dx, dy = next_pos[0] - head_pos[0], next_pos[1] - head_pos[1]
        move_map = {
            (0, 1): "up",
            (0, -1): "down",
            (-1, 0): "left",
            (1, 0): "right"
        }
        return {"move": move_map[(dx, dy)]}

    safe_moves = []
    for move_dir, (dx, dy) in [("up", (0, 1)), ("down", (0, -1)),
                               ("left", (-1, 0)), ("right", (1, 0))]:
        nx, ny = head_pos[0] + dx, head_pos[1] + dy
        if (0 <= nx < board_width and 0 <= ny < board_height
                and (nx, ny) not in dangers):
            safe_moves.append(move_dir)

    return {"move": safe_moves[0] if safe_moves else "up"}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
