"""
    doc string should come here !!!  
    this doc-string will be set to Py.Script.Run() method,
    so that a user can see it from help screen
"""
#     **  Template for a new script  **

#   Following variabs/functions can be used
#    obj : script object
#    top. proj : = obj.get_root_parent()
#    wdir : proj.getvar('wdir')
#    model: model object containing this script
#    param : model param
#    app : proj.app (ifigure application)
#    exit() : exit from script
#    stop() : exit from script due to error
#    write_log(text) : write text to log
#
#    args : parameter arguments passed to Run method (default = ())
#    kwagrs : keyward arguments passed to Run method (default = {})

import numpy as np
from ifigure.interactive import figure


def example():
    import numpy as np
    x = np.linspace(0, 6.28)
    y = np.sin(x)
    return x, y


x, y = example()
v = figure()
v.addpage()
v.plot(x, y)
write_log('making plot')
