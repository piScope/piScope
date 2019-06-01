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
#    model: target model to work on
#    param : model param
#    app : proj.app (ifigure application)
#    exit() : exit from script
#    stop() : exit from script due to error
#
#    args : parameter arguments passed to Run method (default = ())
#    kwagrs : keyward arguments passed to Run method (default = {})

import numpy as np
import ifigure.interactive as plt


def example():
    import numpy as np
    x = np.linspace(0, 6.28)
    y = np.sin(x)
    return x, y


x, y = example()
plt.addpage()
plt.plot(x, y)
