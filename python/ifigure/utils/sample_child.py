from ifigure.utils.pickled_pipe import PickledPipe
import sys, time

ch = PickledPipe(sys.stdin, sys.stdout)

while True:
    time.sleep(0.5)
    data = ch.recv(nowait=False)
    ch.send(data)
