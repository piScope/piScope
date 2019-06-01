from ifigure.utils.pickled_pipe import PickledPipe
import sys
import time
import os
import subprocess
import ifigure


def open_child():
    dirname = os.path.dirname(ifigure.__file__)
    script = os.path.join(dirname, 'utils', 'sample_child.py')

    p = subprocess.Popen(['python', script],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE)

    ch = PickledPipe(p.stdout, p.stdin)
    return p, ch
