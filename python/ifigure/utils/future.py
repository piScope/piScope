'''
  a utility to use futurize

'''
import sys
import os
import shutil
import subprocess as sp
import ifigure
futurize = None

##
futurize1 = os.path.join(os.path.dirname(os.path.realpath(sys.executable)), 'futurize')
if os.path.exists(futurize1):
    futurize = futurize1

##    
futurize2 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.__file__))), 'bin', 'futurize')
if os.path.exists(futurize2):
    futurize = futurize2
    
## if piScope is installed using the same prefix as futurize, this one find it
futurize3 = os.path.join(os.path.dirname(
                         os.path.dirname(
                         os.path.dirname(
                         os.path.dirname(                             
                         os.path.dirname(ifigure.__file__))))), 'bin', 'futurize')
if os.path.exists(futurize3):
    futurize = futurize3

# probably the best is to keep only this one??    
if futurize is None:    
    futurize=shutil.which("futurize")
    
def call_futurize(file=None, dryrun=False, verbose=False, unicode=True,
                  stage1=True, stage2=False, help=False):
    
    def make_com0():
        command = [futurize,]
        if not dryrun:
            command.append('-w')
        if verbose:
            command.append('-v')
        return command

    def run_com(command):
        p = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
        out, err = p.communicate()
        return out, err
    
    command = make_com0()
    if help:
        command = [futurize, '--help']
        out, err = run_com(command)
        print(out.decode('utf-8'))
        print(err.decode('utf-8'))        
        return
    if stage1:
        command.append('--stage1')
        command.append(file)        
        print(command)
        out, err = run_com(command)
        print(out.decode('utf-8'))
        print(err.decode('utf-8'))        

    if stage2:
        command.append('--stage2')
        command.append(file)                
        print(command)
        out, err = run_com(command)
        print(out.decode('utf-8'))
        print(err.decode('utf-8'))        

class futurizer():
    def process_script(self, obj, dryrun=False, verbose=False, unicode=True,
                       stage1=True, stage2=False, help=False):
        
        assert (futurize is not None), "futurize is not found"
        if help:
            call_futurize(help=True)
            return
        file = obj.path2fullpath()
        call_futurize(file=file, dryrun=dryrun, verbose=verbose, unicode=unicode,
                      stage1=stage1, stage2=stage2, help=False)

    def process_tree(self, root, dryrun=False, verbose=False, unicode=True,
                     stage1=True, stage2=False, help=False):
        assert (futurize is not None), "futurize is not found"        
        if help:
            call_futurize(help=True)
            return

        from ifigure.mto.py_script import PyScript

        for obj in root.walk_tree():
            print(obj)
            if isinstance(obj, PyScript):
                self.process_script(obj,  dryrun=dryrun, verbose=verbose, unicode=unicode,
                      stage1=stage1, stage2=stage2, help=False)
                
                
    def process_proj(self, dryrun=False, verbose=False, unicode=True,
                     stage1=True, stage2=False, help=False):
        import wx
        proj = wx.GetApp().TopWindow.proj
        self.process_tree(proj,  dryrun=dryrun, verbose=verbose, unicode=unicode,
                          stage1=stage1, stage2=stage2, help=help)
        
    process_folder = process_tree
                     
                          
