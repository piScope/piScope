from  multiprocessing import Process, Lock
import wx, tarfile, os, gzip, tempfile

lc = Lock()

def do_tarzip(filename, d, lc):
         ### make tar.gz file
         lc.acquire()
         fid = open(filename, 'w')
         tfid= tarfile.open(mode='w:gz', fileobj=fid)
         basename=os.path.basename(d)
         for item in os.listdir(d):
            # not to save '.trash' directory which 
            # is used for temporary data
            if item != '.trash':
               print(item)
               tfid.add(os.path.join(d, item), 
                     arcname=os.path.join(basename,item))
         tfid.close()
         fid.close()
         lc.release()

def do_zip(filename, tarname,  d, lc):
         ### make .gz file
         lc.acquire()
         with open(tarname, 'rb') as f_in:
              with gzip.open(filename,  'wb') as f_out:
                   f_out.writelines(f_in)
         os.remove(tarname)
         lc.release()

class MPTarzip(object):
    worker = None
    def Run(self, filename, d, odir):
        print("starting tar....(save)")         
#        wx.GetApp().TopWindow.set_window_title(saveflag = True)
        tarname =  self.make_tar(filename, d, lc)
        print("starting tar.gz....(save)")         
#        MPTarzip.worker = Process(target = do_tarzip, args = (filename, d, lc))
        MPTarzip.worker = Process(target = do_zip, args = (filename, tarname,
                                                           d, lc))
        MPTarzip.worker.start()
        self.odir = odir 
        self.d    = d
        wx.CallLater(100, self.CheckFinished)

    def make_tar(self, filename, d, lc):
        ### make tar.gz file
#        lc.acquire()
        fid = tempfile.NamedTemporaryFile('w+b',
                                          dir = os.path.dirname(filename),
                                          delete = False)
        #fid = open(filename+'.tar', 'w')
        tfid= tarfile.open(mode='w:', fileobj=fid)
        basename=os.path.basename(d)
        for item in os.listdir(d):
            # not to save '.trash' directory which 
            # is used for temporary data
            if item != '.trash':
               #print(item)
               tfid.add(os.path.join(d, item), 
                     arcname=os.path.join(basename,item))
        tfid.close()
        fid.close()
#        lc.release()
        return fid.name


    def CheckFinished(self):
        if MPTarzip.worker.is_alive():
            wx.GetApp().TopWindow.set_window_title()
            wx.CallLater(2000, self.CheckFinished)
        else:
            if self.odir != self.d:
                app = wx.GetApp().TopWindow
                app.proj._delete_tempdir(self.odir)
            wx.GetApp().TopWindow.set_window_title()
            print("...finished (save)")

    def isReady(self):
        if MPTarzip.worker is None: 
            return True
        if MPTarzip.worker.is_alive(): 
            return False
        return True
