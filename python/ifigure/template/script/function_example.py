import numpy as np
from ifigure.interactive import figure

'''
   This exapmle shows how to write a function in Script object.
   Script object can be called as if it is a function
  
       proj.xxx.yyy.zzz.obj(x, y, keyword = 'xxxx')

   Note following keywords are reserved by piScope
 
   model
   ans
   obj
   top
   app
   wdir
   param
   ans
   args
   kwargs
'''


def func(x, y, keyword=True):
    pass


ans(func(*args, **kwargs))
