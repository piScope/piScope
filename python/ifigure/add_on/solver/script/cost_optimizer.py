# evaluate cost here.
# in this skelton, cost is assumed to be evaulated
# by run script of the model and stored in param.
# Therefore it reads and retuns it.

model = args[0]
ans(model.param.getvar('cost'))
