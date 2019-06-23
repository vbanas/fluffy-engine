import decode
from constants import ATTACHER, TURN_BOT
from encoder import Encoder
from actions import *
import pathfinder
import svgwrite
import svg_colors
import tsp_solver.greedy as tsp

def solve(taskFile, solutionFile, solver):
    st = State.decode(decode.parse_task(taskFile))
    commands = solver(st)
    Encoder.encodeToFile(solutionFile, commands)


def moveCommand(posFrom, posTo):
    (xf, yf) = posFrom
    (xt, yt) = posTo
    if xt == xf:
        if yt < yf:
            return MoveDown()
        else:
            return MoveUp()
    if xt < xf:
        return MoveLeft()
    else:
        return MoveRight()


def selectCommand(state, command, bot_num):
    results = []
    bot = state.bots[bot_num]
    (x, y) = bot.pos
    current = len(bot.manipulators)
    if isinstance(command, MoveUp):
        current = numCleaned(state, (x, y + 1), bot_num)
    elif isinstance(command, MoveDown):
        current = numCleaned(state, (x, y - 1), bot_num)
    elif isinstance(command, MoveRight):
        current = numCleaned(state, (x + 1, y), bot_num)
    elif isinstance(command, MoveLeft):
        current = numCleaned(state, (x - 1, y), bot_num)
    results.append((current, command))
    bot.turnRight()
    right = numCleaned(state, bot.pos, bot_num)
    if TurnRight().validate(state, bot):
        results.append((right, TurnRight()))
    bot.turnLeft()
    bot.turnLeft()
    left = numCleaned(state, bot.pos, bot_num)
    if TurnLeft().validate(state, bot):
        results.append((left, TurnLeft()))
    bot.turnRight()
    return max(results, key=lambda t: t[0])[1]


def pathToCommands(path, state, bot_num=0):
    commands = []
    for (pos, nextPos) in zip(path, path[1:]):
        commands.append(moveCommand(pos, nextPos))
    for command in commands:
        if TURN_BOT:
            new = selectCommand(state, command, bot_num)
            if new != command:
                state.nextAction(new)
        state.nextAction(command)


def collectBoosters(st, bot):
    while True:
        path = pathfinder.bfsFind(st, bot.pos,
                                  lambda l, x, y: st.cell(x, y)[0] == Booster.MANIPULATOR)
        if path is None:
            break
        pathToCommands(path, st)

        cmd = AttachManipulator(ATTACHER.get_position(bot))
        st.nextAction(cmd)


def closestRotSolver(st):
    bot = st.bots[0]
    collectBoosters(st, bot)
    while True:
        path = pathfinder.bfsFind(st, bot.pos,
                                  lambda l, x, y: st.cell(x, y)[1] == Cell.ROT)
        if path is None:
            break
        pathToCommands(path, st)
    return st.actions()


def numCleaned(st, pos, botnum):
    bot = st.bots[botnum]
    num = 0

    def inc():
        nonlocal num
        num += 1

    bot.repaintWith(pos, st, lambda x, y: inc())
    return num


def closestRotInBlob(st, blob=None, blobRanks=None):
    if blob is None:
        path = pathfinder.bfsFindClosest(st, st.botPos(),
                                         lambda l, x, y:
                                         st.cell(x, y)[1] == Cell.ROT,
                                         rank=lambda x, y:
                                         -numCleaned(st, (x, y), 0))
    else:
        path = pathfinder.bfsFindClosest(
            st, st.botPos(),
            lambda l, x, y: st.cell(x, y)[1] == Cell.ROT,
            availP=lambda x, y: (x, y) in blob,
            rank=lambda x, y:
            (blobRanks.get((x, y)) or 99999,
             -numCleaned(st, (x, y), 0)))
    if path is None:
        return None
    pathToCommands(path, st)
    return path[len(path) - 1]


def blobClosestRotSolver(st):
    blobs = pathfinder.blobSplit(st, 100000)

    def findBlob(pos):
        for blob in blobs:
            if pos in blob:
                return blob
        return None

    def optimizeBlob():
        for i in range(len(blobs)):
            if (len(blobs[i]) < 10):
                pos = next(iter(blobs[i]))
                otherPath = pathfinder.bfsFind(st, pos,
                                               lambda l, x, y:
                                               st.cell(x, y)[1] == Cell.ROT
                                               and (x, y) not
                                               in blobs[i])
                if otherPath is None:
                    return False
                otherPos = otherPath[len(otherPath) - 1]
                otherBlob = findBlob(otherPos)
                blobs[i] = otherBlob.union(blobs[i])
                blobs.remove(otherBlob)
                return True
        return False

    for it in range(1000):
        optimizeBlob()
    return solveWithBlobs(st, blobs)


# solve('/home/myth/projects/fluffy-engine/desc/prob-047.desc', '/home/myth/projects/fluffy-engine/sol/sol-047.sol', blobClosestRotSolver)


def solveWithBlobs(st, blobs):
    bot = st.bots[0]
    collectBoosters(st, bot)

    def findBlob(pos):
        for blob in blobs:
            if pos in blob:
                return blob
        return None

    curPos = st.botPos()
    while True:
        blob = findBlob(curPos)
        if blob is None:
            break
        blobRanks = {}

        def add(l, x, y):
            blobRanks[(x, y)] = l

        pathfinder.bfsFind(st, curPos,
                           lambda l, x, y: False,
                           register=add)
        while True:
            nextPos = closestRotInBlob(st, blob, {})
            if nextPos is None:
                break
        curPos = closestRotInBlob(st)
        if curPos is None:
            break
    return st.actions()


def split_into_regions(st):
    id_counter = 0
    ids_yx = [[0]*st.width for _ in range(st.height)]

    def next_id():
        nonlocal id_counter
        id_counter += 1
        return id_counter

    def is_obstacle(x, y):
        return st.cell(x, y)[1] is Cell.OBSTACLE

    for y in range(st.height):
        # first pass, inherit id from top
        for x in range(st.width):
            if is_obstacle(x, y):
                continue
            if y == 0:
                continue
            if ids_yx[y-1][x] != 0:
                ids_yx[y][x] = ids_yx[y-1][x]
                
        # second pass, propagate id to the right
        for x in range(st.width):
            if is_obstacle(x, y):
                continue
            if x == 0:
                continue

            if ids_yx[y][x-1] != 0 and ids_yx[y][x] == 0:
                ids_yx[y][x] = ids_yx[y][x-1]
                
        # second and a half pass, break propagation to the right after obstacle
        last_id_before_obstacle = 0
        replacement_id = None
        for x in range(st.width):
            if is_obstacle(x, y):
                if x != 0 and not is_obstacle(x-1, y):
                    last_id_before_obstacle = ids_yx[y][x-1]
                continue

            if ids_yx[y][x] == last_id_before_obstacle and last_id_before_obstacle != 0:
                if not replacement_id:
                    replacement_id = next_id()
                ids_yx[y][x] = replacement_id
            else:
                last_id_before_obstacle = 0
                replacement_id = None

        # third pass, propagate id to the left
        for x in reversed(range(st.width)):
            if is_obstacle(x, y):
                continue
            if x == st.width-1:
                continue
            if ids_yx[y][x+1] != 0 and ids_yx[y][x] == 0:
                ids_yx[y][x] = ids_yx[y][x+1]

        # third and a half pass, break propagation to the left after obstacle
        last_id_before_obstacle = 0
        replacement_id = None
        for x in reversed(range(st.width)):
            if is_obstacle(x, y):
                if x != st.width-1 and not is_obstacle(x+1, y):
                    last_id_before_obstacle = ids_yx[y][x+1]
                continue

            if ids_yx[y][x] == last_id_before_obstacle and last_id_before_obstacle != 0:
                if not replacement_id:
                    replacement_id = next_id()
                ids_yx[y][x] = replacement_id
            else:
                last_id_before_obstacle = 0
                replacement_id = None

        # last pass, allocate new ids
        for x in range(st.width):
            if is_obstacle(x, y):
                continue
            if ids_yx[y][x] == 0:
                if x == 0 or ids_yx[y][x-1] == 0:
                    ids_yx[y][x] = next_id()
                else:
                    ids_yx[y][x] = ids_yx[y][x-1]

    # TODO: post processing pass to merge small regions with neighbours?
    # TODO: do not propagate through narrow regions?
    # TODO: limit region sizes? (atleast height? proportional to map height?)

    return ids_yx

def make_region_neighbours_map(ids_yx):
    id_to_neighbours_map = {}

    def ensure_set(a):
        if not a in id_to_neighbours_map:
            id_to_neighbours_map[a] = set()
    
    def link(a, b):
        id_to_neighbours_map[a].add(b)
        id_to_neighbours_map[b].add(a)
    
    h = len(ids_yx)
    w = len(ids_yx[0])
    for y in range(h):
        for x in range(w):
            ensure_set(ids_yx[y][x])
            if x > 0: link(ids_yx[y][x-1], ids_yx[y][x])
            if y > 0: link(ids_yx[y-1][x], ids_yx[y][x])

    return id_to_neighbours_map

            
def make_traversal_plan(region_ids_yx):
    id_to_neighbours_map = make_region_neighbours_map(region_ids_yx)
    max_id = 0
    for row in region_ids_yx:
        for _id in row:
            if _id > max_id:
                max_id = _id
    # TODO: try using this library instead:
    #       https://github.com/jvkersch/pyconcorde
    distance_half_matrix = []
    for a in range(1, max_id+1):
        row = []
        for b in range(1, a):
            if b in id_to_neighbours_map[a]:
                row.append(1)
            else:
                row.append(1000*1000*1000)
        distance_half_matrix.append(row)

    path = tsp.solve_tsp(distance_half_matrix, optim_steps=10)
    
    return list(map(lambda x: x+1, path))

            
def draw_regions(st, ids_yx, traversal_plan, svg_file):
    svg = svgwrite.Drawing(filename=svg_file)
    svg.viewbox(minx=0, miny=0, width=st.width*5, height=st.height*5)
    id_to_color = {}
    def id_color(i):
        if i in id_to_color:
            return id_to_color[i]
        color = svg_colors.random_color(["black", "white"])
        id_to_color[i] = color
        return color

    id_to_coord = {}
    
    for y in range(st.height):
        for x in range(st.width):
            color = "white"
            cell_kind = st.cell(x, y)[1]
            if cell_kind is Cell.OBSTACLE:
                color = "black"

            cell_id = ids_yx[y][x]
            if cell_id != 0 and color != "black":
                color = id_color(cell_id)
                if cell_id not in id_to_coord:
                    id_to_coord[cell_id] = (x*5+2,y*5+2)
                
            svg.add(svg.rect(
                insert=(x*5, y*5),
                size=(5,5),
                fill=color,
                stroke="black",
                stroke_width="0.5"))

            if cell_id != 0:
                svg.add(svg.text(str(cell_id), insert=(x*5+1, y*5+4), font_size=3))

    svg_traversal_line = svg.polyline(
        points=map(lambda x: id_to_coord[x], traversal_plan),
        stroke="red",
        stroke_width="1",
        fill_opacity="0"
    )
    svg.add(svg_traversal_line)
            
    svg.save()

def draw_regions_for_task(task_file, svg_file):
    st = State.decode(decode.parse_task(task_file))
    ids_yx = split_into_regions(st)
    traversal_plan = make_traversal_plan(ids_yx)
    draw_regions(st, ids_yx, traversal_plan, svg_file)


# draw_regions_for_task(
#     "/home/eddy/prog/fluffy-engine/desc/prob-120.desc",
#     "/home/eddy/tmp/1.svg")

