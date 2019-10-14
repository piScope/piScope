from __future__ import print_function

import os
import weakref
from collections import OrderedDict
import six
if six.PY2:
    unicode = unicode
else:
    unicode = str    

import wx
import wx.stc as stc
#import  wx.aui as aui
use_agw = False
if use_agw:
    import wx.lib.agw.aui as aui
else:
    import wx.aui as aui

import ifigure

from ifigure.widgets.script_editor import Notebook
from ifigure.utils.wx3to4 import TextEntryDialog, GridSizer
from ifigure.utils.edit_list import EditListPanel, EDITLIST_CHANGED
from ifigure.widgets.miniframe_with_windowlist import DialogWithWindowList
from ifigure.widgets.book_viewer import FrameWithWindowList
from ifigure.widgets.script_editor import PythonSTC
import ifigure.widgets.dialog as dialog

bitmaps = None

# class NoteBook(aui.AuiNotebook):
#    def SetPageText(self, idx, name, *args, **kargs):
#        name = '{:>3s}'.format(name)
#        return aui.AuiNotebook.SetPageText(self, idx, name, *args, **kargs)
#
#    def GetPageText(self, idx, *args, **kargs):
#        return str(aui.AuiNotebook.GetPageText(self, idx, *args, **kargs)).strip()


# class DlgMdsSession(FrameWithWindowList):

class DlgMdsSession(DialogWithWindowList):
    def __init__(self, parent, data=None, figmds=None, cb=None, noapply=False):
        if data is None:
            return
        if figmds is None:
            return
        self._rvars = tuple()
        self._var_mask = [x for x in figmds._var_mask]
        self.cb = cb
        self.figmds = weakref.ref(figmds, self.onLinkDead)

        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(DlgMdsSession, self).__init__(parent, wx.ID_ANY, style=style,
                                            title=self.figmds().get_full_path())
        # FrameWithWindowList.__init__(self, parent, wx.ID_ANY,
        #                  title = self.figmds().get_full_path())
        if bitmaps is None:
            from ifigure.utils.cbook import make_bitmap_list
            from ifigure.ifigure_config import icondir as path
            path1 = os.path.join(path, '16x16', 'variable.png')
            path2 = os.path.join(path, '16x16', 'script.png')
            globals()['bitmaps'] = make_bitmap_list([path1, path2])

        self.nb_big = wx.Notebook(self)
        panel1 = wx.Panel(self.nb_big)
        panel2 = wx.Panel(self.nb_big)

        # panel1
        elpl = [['Experiment', figmds.getvar('experiment'), 200, None],
                ['Def Node', figmds.getvar('default_node'), 200, None],
                ['Title', figmds.getvar('title'), 200, None]]

        self.elp = EditListPanel(panel1, elpl)
        self.nb = Notebook(panel1)
#        p = PythonSTC(self.nb, -1)
#        self.nb.AddPage(p, 'Untitiled')
        self.bt_var = wx.BitmapButton(
            panel1, wx.ID_ANY, bitmaps[0])  # 'Add Variable...')
        self.bt_script = wx.BitmapButton(
            panel1, wx.ID_ANY, bitmaps[1])  # 'Add Script...')
#        self.cb_local = wx.CheckBox(self, wx.ID_ANY, 'Run script in main thread')
        self.cb_local = wx.StaticText(panel1, wx.ID_ANY,
                                      'Note: Script runs in main thread')
        self.rb_mask = wx.CheckBox(panel1, wx.ID_ANY, 'Ignore this variable')
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
        sizer.Add(self.rb_mask, 0, wx.ALL, 1)
        sizer.Add(bsizer2, 0, wx.EXPAND | wx.ALL, 1)
        panel1.SetSizer(sizer)

        # panel2
        panel2.SetSizer(wx.BoxSizer(wx.VERTICAL))
        s = {"style": wx.CB_READONLY,
             "choices": ["timetrace", "stepplot", "plot", "contour", "image", "axline", "axspan", "surface"]}
        elp2 = [[None,  'timetrace',  31, s],
                [None,  ((False, (-1, 1)), (False, (-1, 1))),
                 32, None],
                ["update",   '',  0,   {}], ]
        self.elp2 = EditListPanel(panel2, elp2)
        self.elp2.Bind(EDITLIST_CHANGED, self.onEL_Changed)
        self.bt = wx.Button(panel2, wx.ID_ANY, 'Format...')
        panel2.GetSizer().Add(self.elp2, 1, wx.EXPAND)
        panel2.GetSizer().Add(self.bt, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        self.bt.Bind(wx.EVT_BUTTON, self.onFormat)

        # big_panel
        self.nb_big.AddPage(panel1, 'Signal')
        self.nb_big.AddPage(panel2, 'Setting')
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(self.nb_big, 1, wx.EXPAND)
        bt_apply = wx.Button(self, wx.ID_ANY, 'Apply')
        bt_save = wx.Button(self, wx.ID_ANY, 'Save')

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
        self.Bind(wx.EVT_CHECKBOX, self.onMaskHit, self.rb_mask)
#        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.onPageChange, self.nb)
#        wx.CallLater(1000, self.onPageChange, None)
        self.set_panel2(figmds)

        # self.append_help_menu()
        # self.append_help2_menu(self.helpmenu)
        # self.SetMenuBar(self.menuBar)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.SetSize((650, 600))
        self.Layout()
        self.SetSize((650, 700))
        self.Show()
        self.Raise()
        # self.set_accelerator_table()
        self.nb.SetSelection(0)
        self.set_mask_button()
        wx.GetApp().add_palette(self)

    def onClose(self, evt):
        wx.GetApp().rm_palette(self)
        self.Destroy()
        evt.Skip()

    def onFormat(self, evt):
        from ifigure.mto.fig_plot import FigPlot
        from ifigure.mto.fig_contour import FigContour
        from ifigure.mto.fig_image import FigImage
        from ifigure.mto.fig_surface import FigSurface
        from ifigure.mto.fig_axline import FigAxline
        from ifigure.mto.fig_axspan import FigAxspan
        from ifigure.mto.fig_text import FigText

        from ifigure.utils.edit_list import EditListDialog
        from ifigure.widgets.artist_widgets import listparam
        figtype = self.elp2.GetValue()[0]
        if (figtype == 'plot' or figtype == 'timetrace' or figtype == 'stepplot'):
            s = {"style": wx.CB_READONLY,
                 "choices": ["line", "dot", "both"]}
            l = [[None,  'format plot', 2, None],
                 ["mode",  'line',  4, s], ]
        elif figtype == 'contour':
            l = [[None,  'format contour', 2, None],
                 listparam['contour_nlevel2'][:4], ]
        else:
            l = None
        if l is None:
            return
        dia = EditListDialog(self, wx.ID_ANY, '',
                             l, nobutton=False,
                             pos=self.GetScreenPosition(),)
        val = dia.ShowModal()
        value = dia.GetValue()
        dia.Destroy()
        if val != wx.ID_OK:
            return

        fig_mds = self.figmds()
        if figtype in ('plot', 'timetrace', 'stepplot'):
            figplots = [child for name, child in fig_mds.get_children()
                        if isinstance(child, FigPlot)]
            artists = []
            for p in figplots:
                artists.extend(p._artists)

            opt = fig_mds.getvar('plot_options')[figtype]
            if str(value[1]) == 'line':
                opt = (('',), opt[1].copy())
                for a in artists:
                    a.set_marker(None)
                    a.set_linestyle('-')
            elif str(value[1]) == 'dot':
                opt = (('s',), opt[1].copy())
                for a in artists:
                    a.set_marker('s')
                    a.set_linestyle('None')
                    a.set_markersize(3)
                    a.set_markerfacecolor(a.get_color())
                    a.set_markeredgecolor(a.get_color())
            elif str(value[1]) == 'both':
                opt = (('-o',), opt[1].copy())
                for a in artists:
                    a.set_marker('o')
                    a.set_linestyle('-')
                    a.set_markersize(3)
                    a.set_markerfacecolor(a.get_color())
                    a.set_markeredgecolor(a.get_color())

            fig_mds.getvar('plot_options')[figtype] = opt

            for k, child in enumerate(figplots):
                child.setvar('s', opt[0][0])
#                col = fig_mds._color_order[k % len(fig_mds._color_order)]
#                opt[1]['color'] = col
#                opt[1]['markerfacecolor'] = col
#                opt[1]['markeredgecolor'] = col
#                for key in opt[1]:
#                     child.getvar('kywds')[key] = opt[1][key]
        elif figtype == 'contour':
            #            print(value[1])
            for name, child in fig_mds.get_children():
                if isinstance(child, FigContour):
                    child.set_contour_nlevel2(value[1])
            if value[1][0]:
                opt = ((value[1][1][0][1],), {})
            else:
                opt = ((int(value[1][2][0]),), {})
            fig_mds.getvar('plot_options')[figtype] = opt

            figplots = [child for name, child in fig_mds.get_children()
                        if isinstance(child, FigContour)]
            for child in figplots:
                child.setvar('n', opt[0][0])
        else:
            return
        fig_mds.get_figaxes().set_bmp_update(False)
        import ifigure.events
        ifigure.events.SendPVDrawRequest(fig_mds.get_figbook(),
                                         wait_idle=True, refresh_hl=False)

    def onMaskHit(self, evt):
        ipage = self.nb.GetSelection()
        txt = self.nb.GetPageText(ipage)
        txt = ''.join(txt.split('*'))
        if self.rb_mask.GetValue():
            self._var_mask.append(txt)
        else:
            self._var_mask = [x for x in self._var_mask if x != txt]
        evt.Skip()

    def onPageChanging(self, evt):
        ipage = self.nb.GetSelection()
        self.set_mask_button()
        evt.Skip()

    def set_mask_button(self):
        ipage = self.nb.GetSelection()
        txt = self.nb.GetPageText(ipage)
        txt = ''.join(txt.split('*'))
        self.rb_mask.SetValue(txt in self._var_mask)

    def set_panel2(self, figmds):
        value = [figmds.get_mdsfiguretype(None),
                 figmds.get_mdsrange(None),
                 figmds.get_mdsevent(None)]
        self.elp2.SetValue(value)

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
        v = self.elp2.GetValue()
        self.data = None
        self.Destroy()
        if self.cb is not None:
            self.cb(v)

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
#            name = str(self.nb.GetPageText(x))
#            if name.startswith('*'): name = name[1:]
            p.SetSavePoint()
            self.nb.SetPageTextModifiedMark(x, False)

        v = self.elp2.GetValue()
        if self.cb is not None:
            self.cb(v)
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
                dlg.Destroy()
                return
#            len(data.keys())
            for i in range(self.nb.GetPageCount()):

                label = str(self.nb.GetPageText(i))
                if label.startswith('*'):
                    label = label[1:]
                if label == 'script.py':
                    self.nb.GetPage(i).set_syntax('python')
                else:
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
        data['script.py'] = '\n'

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
        print('onClose')
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
                                 " cannot be deleted for current plot type\n(Leave it empty, if you don't need it)",
                                 'Error',
                                 0)
            evt.Veto()
            return
        npage = self.nb.GetPageCount()
        if npage == 1 or npage == 0:
            ret = dialog.message(None,
                                 '"'+label+'"' + " cannot be deleted since this is the last page.",
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

        self.data = None
        if str(label) == 'script.py':
            self.bt_script.Enable(True)

        if self.cb is not None:
            v = self.elp2.GetValue()
            self.cb(v)
        wx.CallAfter(self._set_save_point, mods)

    def _set_save_point(self, mods):
        # print 'xxx', mods
        for x in range(self.nb.GetPageCount()):
            #            p = self.nb.GetPage(x)
            #            txt = self.nb.GetPageText(x)
            self.nb.SetPageTextModifiedMark(x, mods[x])
#            if not mods[x]:
#               self.nb.GetPage(x).SetSavePoint()
#               if txt.startswith('*'):
#                  self.nb.SetPageText(x, txt[1:])
#            else:
#               if not txt.startswith('*'):
#                  self.nb.SetPageText(x,'*'+ txt)

    def update_figmds(self, data, script):
        fmds = self.figmds()
        fmds._var_mask = [x for x in self._var_mask]
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
            fmds.write_script(script)
        else:
            fmds.remove_script()

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
            name = str(self.nb.GetPageText(ipage))
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
                self.nb.AddPage(p, title, select=True)
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
            fmds = self.figmds()
            fname = os.path.join(fmds.owndir(), 'mdsscript.py')
            self.nb.SetSelection(npage-1)
            self.nb.SetPageText(npage-1, 'script.py', doc_name=fname)
            p = self.nb.GetPage(npage-1)
            p.set_syntax('python')
            self._set_stc_txt(p, script)
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
        p = self.nb.GetPage(ipage)
        self.nb.SetPageTextModifiedMark(ipage, p.GetModify())

    def onLinkDead(self, obj):
        #        if self.cb is not None:
        #            self.cb()
        try:
            self.Destroy()
        except:
            pass

    def onEL_Changed(self, evt):
        from ifigure.mdsplus.fig_mds import required_variables
        print(evt.widget_idx)
        if evt.widget_idx == 0:
            plot_type = str(evt.elp.GetValue()[0])
            v = required_variables[plot_type]
            self.set_required_variables(v)

    def set_required_variables(self, variables):
        self._rvars = variables
        data, script = self.pages2data()
        chk = self.checkscripttab()
        for x in self._rvars:
            if not x in data:
                p = self._new_stc(self.nb, '', syntax='none')
                title = '{:>3s}'.format(x)
                if script == '':
                    self.nb.AddPage(p, title, select=True)
                else:
                    self.nb.InsertPage(self._rvars.index(x),
                                       p, title, select=True)
                self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified, p)

#        if chk: data['script.py'] = script
#        self.data2pages(data)
#        self.nb.SetSelection(0)

    def _new_stc(self, parent, txt, syntax='none'):
        p = PythonSTC(parent, -1, syntax=syntax)

        #self._set_stc_txt(p, txt)
        p.EmptyUndoBuffer()
        p.Colourise(0, -1)
        # line numbers in the margin
        p.SetMarginType(1, stc.STC_MARGIN_NUMBER)
#        p.SetMarginWidth(1, 25)
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
