from constants import Booster
from state import State, Cell
import decode
from encoder import Encoder
from actions import MoveUp, MoveDown, MoveLeft, MoveRight, AttachManipulator
import pathfinder


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


def pathToCommands(path):
    commands = []
    for (pos, nextPos) in zip(path, path[1:]):
        commands.append(moveCommand(pos, nextPos))
    return commands


# left-right direction
LR = 1


def collectBoosters(st):
    global LR
    while True:
        path = pathfinder.bfsFind(st, st.botPos(),
                                  lambda x, y: st.cell(x, y)[0] == Booster.MANIPULATOR)
        if path is None:
            break
        commands = pathToCommands(path)
        for command in commands:
            st.nextAction(command)

        turns = 0
        while st.bot.manipulators[0] != (1, 0):
            turns += 1
            st.bot.turnLeft()
        idx = 2
        while not st.bot.is_attachable(idx * LR, 1):
            idx += 1
        pos = (idx * LR, 1)
        LR *= -1
        while turns > 0:
            turns -= 1
            st.bot.turnRight()
            pos = (pos[1], -pos[0])
        st.nextAction(AttachManipulator(*pos))


def closestRotSolver(st):
    collectBoosters(st)
    while True:
        path = pathfinder.bfsFind(st, st.botPos(),
                                  lambda x, y: st.cell(x, y)[1] == Cell.ROT)
        if path is None:
            break
        commands = pathToCommands(path)
        for command in commands:
            st.nextAction(command)
    return st.actions
