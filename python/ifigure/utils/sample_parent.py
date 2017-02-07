from ifigure.utils.pickled_pipe import PickledPipe
import sys, time, os, subprocess, ifigure

def open_child():
    dirname=os.path.dirname(ifigure.__file__)
    script =os.path.join(dirname, 'utils', 'sample_child.py')

    p = subprocess.Popen(['python', script], 
                     stdin = subprocess.PIPE,
                     stdout = subprocess.PIPE)

    ch = PickledPipe(p.stdout, p.stdin)
    return  p, ch
    

   
