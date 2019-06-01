proj = obj.get_root_parent()
wdir = proj.eval("wdir")

loki = proj.psetting.loki
rdir = os.path.basename(wdir)
runname = os.path.basename(proj.eval("filename"))[:-4]
rdir = str(os.path.join('py_genray', runname))

files = ['genray.nc', 'lh_raytracing.nc', 'lh_raytracing_krf001.nc']
for file in files:
    file_f = os.path.join(wdir, file)
    loki.call_method('onRec', file=file_f, rfile=file, rdir=rdir)

solver = obj.get_parent()
sol = solver.sol
