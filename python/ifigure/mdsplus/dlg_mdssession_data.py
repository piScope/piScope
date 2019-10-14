import os
import weakref
import six
if six.PY2:
    unicode = unicode
else:
    unicode = str
from collections import OrderedDict

import wx
import wx.stc as stc
#import  wx.aui as aui
use_agw = False  # for agw, onClosePage does not work....
if use_agw:
    import wx.lib.agw.aui as aui
else:
    import wx.aui as aui

import ifigure
from ifigure.utils.wx3to4 import TextEntryDialog
from ifigure.widgets.script_editor import Notebook
from ifigure.utils.edit_list import EditListPanel, EDITLIST_CHANGED
from ifigure.widgets.miniframe_with_windowlist import DialogWithWindowList
from ifigure.widgets.book_viewer import FrameWithWindowList

from ifigure.widgets.script_editor import PythonSTC
import ifigure.widgets.dialog as dialog

bitmaps = None

class DlgMdsSessionData(DialogWithWindowList):
    # class DlgMdsSessionData(FrameWithWindowList):
    def __init__(self, parent, data=None, figmds=None, cb=None, noapply=False):
        if data is None:
            return
        if figmds is None:
            return
        self._rvars = tuple()
        self.cb = cb
        self.figmds = weakref.ref(figmds, self.onLinkDead)

        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(DlgMdsSessionData, self).__init__(parent, wx.ID_ANY, style=style,
                                                title=self.figmds().get_full_path())
#        FrameWithWindowList.__init__(self, parent, wx.ID_ANY,
#                          title = self.figmds().get_full_path())

        if bitmaps is None:
            from ifigure.utils.cbook import make_bitmap_list
            from ifigure.ifigure_config import icondir as path
            path1 = os.path.join(path, '16x16', 'variable.png')
            path2 = os.path.join(path, '16x16', 'script.png')
            globals()['bitmaps'] = make_bitmap_list([path1, path2])


#        self.nb_big = wx.Notebook(self)
        panel1 = wx.Panel(self)

        # panel1
        elpl = [['Experiment', figmds.getvar('experiment'), 200, None],
                ['Def Node', figmds.getvar('default_node'), 200, None],
                ['Title', figmds.getvar('title'), 200, None]]

        self.elp = EditListPanel(panel1, elpl)
        self.nb = Notebook(panel1)
        self.bt_var = wx.BitmapButton(
            panel1, wx.ID_ANY, bitmaps[0])  # 'Add Variable...')
        self.bt_script = wx.BitmapButton(
            panel1, wx.ID_ANY, bitmaps[1])  # 'Add Script...')
        self.cb_local = wx.StaticText(
            panel1, wx.ID_ANY, 'Note: Script runs in main thread')
#        p = PythonSTC(self.nb, -1)
#        self.nb.AddPage(p, 'Untitiled')
        sizer = wx.BoxSizer(wx.VERTICAL)
        bsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        bsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        bsizer0 = wx.BoxSizer(wx.VERTICAL)

        bsizer1.Add(self.elp, 1, wx.EXPAND | wx.ALL, 3)
        bsizer1.Add(bsizer0, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        bsizer0.Add(self.bt_var, 0, wx.ALL, 0)
        bsizer0.Add(self.bt_script, 0, wx.ALL, 0)
        bsizer2.Add(self.cb_local, 1, wx.ALL, 3)

        sizer.Add(bsizer1, 0, wx.EXPAND | wx.ALL, 1)
        sizer.Add(self.nb, 1, wx.EXPAND | wx.ALL, 0)
        sizer.Add(bsizer2, 0, wx.EXPAND | wx.ALL, 1)
        panel1.SetSizer(sizer)

#        self.bt_var = wx.Button(panel1, wx.ID_ANY, 'Add Variable...')
#       self.bt_script = wx.Button(panel1, wx.ID_ANY, 'Add Script...')
#        self.cb_local = wx.CheckBox(self, wx.ID_ANY, 'Run script in main thread')

        bt_apply = wx.Button(self, wx.ID_ANY, 'Apply')
        bt_save = wx.Button(self, wx.ID_ANY, 'Save')
#        bt_reset  = wx.Button(self, wx.ID_ANY, 'Reset')
#        bt_cancel = wx.Button(self, wx.ID_ANY, 'Cancel')
#        bsizer0.Add(self.bt_var, 1, wx.ALL, 3)
#        bsizer0.Add(self.bt_script, 1, wx.ALL, 3)
#        bsizer1.Add(self.cb_local, 1, wx.ALL, 3)

        # big_panel
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(panel1, 1, wx.EXPAND)
        from ifigure.utils.wx3to4 import GridSizer
        bsizer = GridSizer(1, 5)
        bsizer.AddStretchSpacer()
        self.GetSizer().Add(bsizer, 0, wx.EXPAND | wx.ALL, 1)
        bsizer.Add(bt_save, 1, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 3)
        bsizer.AddStretchSpacer()
        bsizer.Add(bt_apply, 1, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 3)
        bsizer.AddStretchSpacer()
#        bsizer.Add(bt_reset, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 3)
#        bsizer.Add(bt_cancel, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 3)
        self.Bind(wx.EVT_BUTTON, self.onAddVar, self.bt_var)
        self.Bind(wx.EVT_BUTTON, self.onAddScript, self.bt_script)
        self.Bind(wx.EVT_BUTTON, self.onSave, bt_save)
#        self.Bind(wx.EVT_BUTTON, self.onCancel, bt_cancel)
        self.Bind(wx.EVT_BUTTON, self.onApply, bt_apply)
#        self.Bind(wx.EVT_BUTTON, self.onReset, bt_reset)
        if noapply:
            bt_apply.Hide()
#        self.Bind(wx.EVT_CHECKBOX, self.onHit, cb_local)
        hasscript, lc, script = self.read_script()
        if hasscript:
            self.bt_script.Enable(False)
        self.cb_local.SetLabel(self._lcstr(lc, hasscript))
        self.data2pages(data)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.onClosePage, self.nb)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED,
                  self.onPageChanging, self.nb)
#        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.onPageChange, self.nb)
#        wx.CallLater(1000, self.onPageChange, None)
        # self.append_help_menu()
        self.SetSize((650, 600))
        # self.SetMenuBar(self.menuBar)
        self.Layout()
        self.Show()
        self.Raise()
        # self.set_accelerator_table()
        self.nb.SetSelection(0)
        wx.GetApp().add_palette(self)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        
    def onClose(self, evt):
        wx.GetApp().rm_palette(self)
        self.Destroy()
        evt.Skip()

    def onPageChanging(self, evt):
        ipage = self.nb.GetSelection()
        evt.Skip()

    def onApply(self, evt=None):
        self.onSave(self)
        fig_mds = self.figmds()
        fig_axes = fig_mds.get_figaxes()
        proj = fig_mds.get_root_parent()
        scope = proj.app.find_bookviewer(fig_mds.get_figbook())
        if scope is not None:
            scope._handle_apply_abort(allshot=True, figaxes=[fig_axes])
        if evt is not None:
            evt.Skip()

    def onOk(self, evt):
        # do something to convert texts to data
        # send action to figmds
        data, script = self.pages2data()
        self.update_figmds(data, script)
        self.data = None
        self.Destroy()

    def onCancel(self, evt):
        self.data = None
        self.Destroy()
#        if self.cb is not None:
#            self.cb()

    def onSave(self, evt=None):
        data, script = self.pages2data()
        self.update_figmds(data, script)
        ipage = self.nb.GetSelection()
        for x in range(self.nb.GetPageCount()):
            p = self.nb.GetPage(x)
            name = str(self.nb.GetPageText(x))
            if name.startswith('*'):
                name = name[1:]
            self.nb.SetPageText(x, name)
            p.SetSavePoint()

        if self.nb.GetPageCount() > ipage:
            self.nb.SetSelection(ipage)

        for x in range(self.nb.GetPageCount()):
            p = self.nb.GetPage(x)
            p.SetSavePoint()
        self.onModified(None)
#        for x in range(self.nb.GetPageCount()):
#            p=self.nb.GetPage(x)
#            self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified, p)

    def onReset(self, evt):
        fmds = self.figmds()
        if fmds is None:
            self.Destroy()
#            if self.cb is not None:
#                self.cb()
            return
#        self.Freeze()
#        self.deleteallpages()
        self.data2pages(fmds.getvar('mdsvars'))
#        self.Thaw()

    def onAddVar(self, evt):
        dlg = TextEntryDialog(self.GetTopLevelParent(),
                              "Enter the name of variable", "Add variable", "")
        if dlg.ShowModal() == wx.ID_OK:
            #            self.Freeze()
            new_name = str(dlg.GetValue())
            data, script = self.pages2data()
            if new_name in data:
                return
#            len(data.keys())
            for i in range(self.nb.GetPageCount()):
                self.nb.GetPage(i).set_syntax('none')

            p = self._new_stc(self.nb, '', syntax='none')
            self.nb.InsertPage(len(data), p, new_name, True)
            self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified, p)
#            data[new_name] = ''
#            self.data2pages(data)
        dlg.Destroy()

    def SetStatusText(self, *args, **kargs):
        pass

    def onOpenFile(self, *args, **kargs):
        pass

    def onSaveFile(self, *args, **kargs):
        # this is called from stc
        self.onApply()

    def onAddScript(self, evt=None):
        hasscript, lc, script = self.read_script()
        if hasscript:
            return

#        self.Freeze()
        data, script = self.pages2data()
        data['script.py'] = ''

        self.data2pages(data)
#        self.bt_script.Enable(False)
#        self.cb_local.SetLabel(self._lcstr(lc, True))
#        self.Thaw()
        evt.Skip()

    def _lcstr(self, value, hasscript):
        if not hasscript:
            return "note : no addtionanl python script after MDS session"
        if value:
            return "note : script runs in main thread"
        else:
            return "note : script runs in subprocess"

#    def onPageChange(self, evt=None):
#        ipage = self.nb.GetSelection()
#        label  = self.nb.GetPageText(ipage)
#        self._selected_page = label

    def onClosePage(self, evt):
        #        print("onClose")
        ipage = self.nb.GetSelection()
        label = str(self.nb.GetPageText(ipage))
        if label.startswith('*'):
            label = label[1:]
        mods = [self.nb.GetPage(x).GetModify()
                for x in range(self.nb.GetPageCount())]
        del mods[ipage]
        if str(label) in self._rvars:
            ret = dialog.message(self,
                                 '"'+label+'"' +
                                 " cannot deleted for current plot type\n(Leave it empty, if you don't need it)",
                                 'Error',
                                 0)
            evt.Veto()
            return
        npage = self.nb.GetPageCount()
        if npage == 1 or npage == 0:
            ret = dialog.message(self,
                                 '"'+label+'"' + " cannot deleted since this is the last page.",
                                 'Error',
                                 0)
            evt.Veto()
            return
        else:
            ret = dialog.message(self,
                                 'Do you want to delete "'+label+'"',
                                 'Error',
                                 2)
            if ret != 'ok':
                evt.Veto()
                return

#        if label == 'script.py' or label == '*script.py':
#            fmds = self.figmds()
#            if fmds is not None:
#              if (fmds.has_owndir() and
#                  fmds.hasvar('path')):
#                  fname = os.path.join(fmds.owndir(), fmds.getvar('path'))
#                  if os.path.exists(fname):
#                      os.remove(fname)
#                      fmds.delvar('pathmode')
#                      fmds.delvar('path')
        self.data = None
#        print label
        if str(label) == 'script.py':
            self.bt_script.Enable(True)

        wx.CallAfter(self._set_save_point, mods)

    def _set_save_point(self, mods):
        # print 'xxx', mods
        for x in range(self.nb.GetPageCount()):
            p = self.nb.GetPage(x)
            txt = self.nb.GetPageText(x)
            if not mods[x]:
                self.nb.GetPage(x).SetSavePoint()
                if txt.startswith('*'):
                    self.nb.SetPageText(x, txt[1:])
            else:
                if not txt.startswith('*'):
                    self.nb.SetPageText(x, '*' + txt)

    def update_figmds(self, data, script):
        fmds = self.figmds()
        var = self.elp.GetValue()
        fmds.setvar('experiment', str(var[0]))
        fmds.setvar('default_node', str(var[1]))
        fmds.setvar('title', str(var[2]))
        d = OrderedDict()
        for key in data:
            name = key
            if key.startswith('*'):
                name = key[1:]
            d[name] = data[key]
        fmds.applyDlgData(d)
        if script != '':
            if not fmds.has_owndir():
                fmds.mk_owndir()
            filename = 'mdsscript.py'
            fmds.setvar('pathmode', 'owndir')
            fmds.setvar('path', filename)
            fname = os.path.join(fmds.owndir(),
                                 fmds.getvar('path'))
            from ifigure.mdsplus.fig_mds import write_scriptfile
            write_scriptfile(fname, script)
        else:
            if (fmds.has_owndir() and
                    fmds.hasvar('path')):
                fname = os.path.join(fmds.owndir(), fmds.getvar('path'))
                if os.path.exists(fname):
                    os.remove(fname)
                    fmds.delvar('pathmode')
                    fmds.delvar('path')

#        fmds._script_local = self.cb_local.GetValue()
#        print self.GetParent()
        self.GetParent().property_editor.update_panel()
        # should change varviewer here too

    def checkscripttab(self):
        data = OrderedDict()
        for ipage in range(self.nb.GetPageCount()):
            name = str(self.nb.GetPageText(ipage))
            if name.startswith('*'):
                name = name[1:]
            p = self.nb.GetPage(ipage)
            data[name] = str(p.GetText())

        return 'script.py' in data

    def pages2data(self):
        data = OrderedDict()
        for ipage in range(self.nb.GetPageCount()):
            name = str(self.nb.GetPageText(ipage)).strip()
            if name.startswith('*'):
                name = name[1:]
            p = self.nb.GetPage(ipage)
            data[name] = str(p.GetText()).strip()
            p.SetSavePoint()
        script = ''
        if 'script.py' in data:
            script = data['script.py']
            del data['script.py']
        return data, script

    def data2pages(self, data):
        fmds = self.figmds()

        hasscript, lc,  script = self.read_script()
        if 'script.py' in data:
            script = data['script.py']
            hasscript = True
            del data['script.py']

        # set button
        self.cb_local.SetLabel(self._lcstr(lc, hasscript))

        # prepare pages
        npage = len([key for key in data])
        if hasscript:
            npage = npage + 1
        while self.nb.GetPageCount() != npage:
            if self.nb.GetPageCount() > npage:
                self.nb.DeletePage(self.nb.GetPageCount()-1)
            elif self.nb.GetPageCount() < npage:
                title = 'tmp_key' + str(self.nb.GetPageCount())
                p = self._new_stc(self.nb, '', syntax='python')
                title = '{:>3s}'.format(title)
                self.nb.AddPage(p, title, True)
                self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified, p)

        for ipage, key in enumerate(data):
            self.nb.SetPageText(ipage, key)
            p = self.nb.GetPage(ipage)
            if ipage == len(data)-1 and hasscript:
                pass
            else:
                p.set_syntax('none')
            self._set_stc_txt(p, data[key])

        if hasscript:
            self.nb.SetPageText(npage-1, 'script.py')
            p = self.nb.GetPage(npage-1)
            self._set_stc_txt(p, script)
            p.set_syntax('python')
            self.bt_script.Enable(False)
        else:
            self.bt_script.Enable(True)

    def read_script(self):
        from ifigure.mdsplus.fig_mds import read_scriptfile
        fmds = self.figmds()
        lc = fmds.get_script_local()
        if fmds is None:
            return
        if (fmds.has_owndir() and
                fmds.hasvar('path')):
            fname = os.path.join(fmds.owndir(), fmds.getvar('path'))
            txt = read_scriptfile(fname)
            return True,  lc, txt
        return False, lc,  ''

    def get_filelist(self):
        return self.file_list

    def onModified(self, e=None):
        ipage = self.nb.GetSelection()
#        print 'onModified', ipage
        txt = self.nb.GetPageText(ipage)
        p = self.nb.GetPage(ipage)
#        print [self.nb.GetPage(x).GetModify() for x in range(self.nb.GetPageCount())]
        # print p.GetModify()
        if not txt.startswith('*') and p.GetModify():
            self.nb.SetPageText(ipage, '*'+txt)
        if txt.startswith('*') and not p.GetModify():
            self.nb.SetPageText(ipage, txt[1:])

    def onLinkDead(self, obj):
        #        if self.cb is not None:
        #            self.cb()
        try:
            self.Destroy()
        except:
            pass

    def _new_stc(self, parent, txt, syntax='none'):
        p = PythonSTC(parent, -1, syntax=syntax)
        self._set_stc_txt(p, txt)
        p.EmptyUndoBuffer()
        p.Colourise(0, -1)
        # line numbers in the margin
        p.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        #p.SetMarginWidth(1, 25)
        p.set_syntax(syntax)
        return p

    def _set_stc_txt(self, p, txt):
        #        mod = p.GetModify()
        try:
            p.SetText(txt)
#            if not mod: p.SetSavePoint()
        except UnicodeDecodeError:
            p.SetText(unicode(txt, errors='ignore'))
#            if not mod: p.SetSavePoint()
        pass
