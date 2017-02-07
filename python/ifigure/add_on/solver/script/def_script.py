print(" ")
print(" ##########################")
print(" Running Debug Script")
print(" ##########################")
print("")
print(" Running evniroment for script file")
proj = obj.get_root_parent()
print("   proj    =", proj)
print("   treeobj =", obj)
print(" ")

import time, os



print(proj.book1.page6.axes1.spline1._artists[0].get_xdata())