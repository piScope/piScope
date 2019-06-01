from __future__ import print_function
import os
import time
print(" ")
print(" ##########################")
print(" Running GENRAY-Loki Script")
print(" ##########################")
print("")
print(" Running evniroment for script file")
# print "   proj    =", proj
print(("   treeobj =", obj.get_full_path(), obj))
print(" ")

print((" Script File : ",  obj.path2fullpath()))
print((" Last Modified : ", time.ctime(obj._script._script_mtime)))

solver = obj.get_parent()
print(('model folder:', solver.model.get_full_path()))
print(('solution folder :', solver.sol.get_full_path()))

root = obj.get_root_parent()
print(('setting:', root.psetting.get_full_path()))
print(('connection:', root.psetting.loki.get_full_path()))

proj = obj.get_root_parent()
wdir = proj.eval("wdir")
runname = os.path.basename(proj.eval("filename"))[:-4]

gin_file = os.path.join(wdir, 'genray.in')
cqlin_file = os.path.join(wdir, 'cqlinput')
cqlpbs = os.path.join(wdir, 'cql3d.pbs')
gfile = 'g111.1111'


gfile_full = os.path.join(wdir, gfile)

mto = solver.model.GENRAY

mto.genray_input.tokamak.setvar("eqdskin", ['"'+gfile+'"'])
mto.cql_input.eqsetup.setvar("eqdskin", ['"'+gfile+'"'])

mto.gfile.call_method('onWriteFile', file=gfile_full)
mto.genray_input.call_method('onWriteFile', file=gin_file)
mto.cql_input.call_method('onWriteFile', file=cqlin_file)
mto.cql3dpbs.call_method('onWriteFile', file=cqlpbs)

loki = root.psetting.loki
rdir = os.path.basename(wdir)
rdir = str(os.path.join('py_genray', runname))
loki.call_method('onSend', file=gfile_full, rdir=rdir)
loki.call_method('onSend', file=gin_file, rdir=rdir)
loki.call_method('onSend', file=cqlin_file, rdir=rdir)
loki.call_method('onSend', file=cqlpbs, rdir=rdir)

command = 'cd '+rdir + ';' + '/home/shiraiwa/bin/launch_xgenray -0'
print('Now calling genray')
loki.call_method('onExec',  command=command)
print('Now submitting CQL3D job')
command = 'cd '+rdir + ';' + 'qsub cql3d.pbs'
loki.call_method('onExec',  command=command)

# loki.onSend(rdir='/home/shiraiwa/xxx')
