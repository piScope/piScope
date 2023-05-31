from __future__ import print_function

import wx
import tarfile
import os
import gzip
import tempfile
import time

import traceback
from ifigure.widgets.dialog import showtraceback, message

from threading import Lock
local_lc = Lock()

from multiprocessing import Process, Lock

def do_zip(filename, tarname,  d):
    # make .gz file
    #lc.acquire()
    with open(tarname, 'rb') as f_in:
         with gzip.open(filename, 'wb') as f_out:
             f_out.writelines(f_in)
    os.remove(tarname)
    #lc.release()

class MPTarzip(object):
    worker = None
    #lc = Lock()

    def Run(self, filename, d, odir):
        if not self.isReady():
            return False
        try:
            os.getcwd()
        except FileNotFoundError:
            os.chdir(os.path.expanduser("~"))

        print("starting tar....(save)")

        try:
            tarname = self.make_tar(filename, d)
        except PermissionError:
            message(wx.GetApp().TopWindow,
                    'Permission error', 'Error', 0)
            return False
        except:
            showtraceback(wx.GetApp().TopWindow, txt=traceback.format_exc())
            return False

        print("starting tar.gz....(save)")
        MPTarzip.worker = Process(target=do_zip, args=(filename, tarname, d))

        try:
            MPTarzip.worker.start()
        except:
            showtraceback(wx.GetApp().TopWindow, txt=traceback.format_exc())
            return False

        self.odir = odir
        self.d = d
        wx.CallLater(100, self.CheckFinished)

        return True

    def make_tar(self, filename, d):
        # make tar.gz file
        #        lc.acquire()
        fid = tempfile.NamedTemporaryFile('w+b',
                                          dir=os.path.dirname(filename),
                                          delete=False)
        #fid = open(filename+'.tar', 'w')
        tfid = tarfile.open(mode='w:', fileobj=fid)
        basename = os.path.basename(d)
        for item in os.listdir(d):
            # not to save '.trash' directory which
            # is used for temporary data
            if item != '.trash':
                # print(item)
                tfid.add(os.path.join(d, item),
                         arcname=os.path.join(basename, item))
        tfid.close()
        fid.close()
#        lc.release()
        return fid.name

    def CheckFinished(self):
        if MPTarzip.worker.is_alive():
            top = wx.GetApp().TopWindow
            if top is not None:
                top.set_window_title()
            wx.CallLater(2000, self.CheckFinished)
        else:
            if self.odir != self.d:
                app = wx.GetApp().TopWindow
                app.proj._delete_tempdir(self.odir)
            top = wx.GetApp().TopWindow
            if top is not None:
                top.set_window_title()
            MPTarzip.worker = None
            print("...finished (save)")
            local_lc.release()

    def isReady(self):
        if MPTarzip.worker is None:
            return True
        if MPTarzip.worker.is_alive():
            return False
        return True
