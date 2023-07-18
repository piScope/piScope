#
#   dialog.py
#
#   these are routine to show dialog
#   these are made to eliminate import wx
#   from mto fils.
#
#   read  : file read dialog
#   write : file write dialog
#   dlg_message   :  message dialog
#   dlg_textentry  : text entry dialog
#
import wx
import os
from ifigure.utils.wx3to4 import TextEntryDialog, deref_proxy


def read(parent=None,
         message='Select file to read',
         wildcard='*',
         defaultfile='',
         defaultdir=''):

    open_dlg = wx.FileDialog(parent, message=message,
                             wildcard=wildcard, style=wx.FD_OPEN)
    if defaultfile != '':
        open_dlg.SetFilename(os.path.basename(defaultfile))
        if os.path.dirname(defaultfile) != '':
            open_dlg.SetDirectory(os.path.dirname(defaultfile))
    if defaultdir != '':
        open_dlg.SetDirectory(defaultdir)

    path = ''
    if open_dlg.ShowModal() == wx.ID_OK:
        path = open_dlg.GetPath()
        open_dlg.Destroy()
    open_dlg.Destroy()
    return path


def readdir(parent=None, message='Select directory to read', wildcard='*', defaultfile=''):

    open_dlg = wx.DirDialog(parent, message=message,)
    if defaultfile != '':
        open_dlg.SetFilename(os.path.basename(defaultfile))
        if os.path.dirname(defaultfile) != '':
            open_dlg.SetDirectory(os.path.dirname(defaultfile))
    path = ''
    if open_dlg.ShowModal() == wx.ID_OK:
        path = open_dlg.GetPath()
        open_dlg.Destroy()
    open_dlg.Destroy()
    return path


def write(parent=None, defaultfile='',
          message='Select file to write', wildcard='*',
          return_filterindex=False,
          warn_overwrite=False):
    '''
    wrap FileDialog, Note that defaultfile can be absolute path
    '''
    style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT if warn_overwrite else wx.FD_SAVE

    open_dlg = wx.FileDialog(parent, message=message,
                             wildcard=wildcard,
                             style=style)
    if defaultfile != '':
        open_dlg.SetFilename(os.path.basename(defaultfile))
        if os.path.dirname(defaultfile) != '':
            open_dlg.SetDirectory(os.path.dirname(defaultfile))

    path = ''
    wc = ''
    if open_dlg.ShowModal() == wx.ID_OK:
        path = open_dlg.GetPath()
        wc = open_dlg.GetFilterIndex()
        open_dlg.Destroy()
    open_dlg.Destroy()
    if return_filterindex:
        return path, wc
    else:
        return path


def writedir(parent=None,  message='Directory to write'):

    dlg = wx.DirDialog(parent, message=message)
    path = ''
    wc = ''
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        dlg.Destroy()
        return path
    else:
        dlg.Destroy()
        return None


def readdir(parent=None,  message='Directory to read'):

    dlg = wx.DirDialog(parent, message=message)
    path = ''
    wc = ''
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        dlg.Destroy()
        return path
    else:
        dlg.Destroy()
        return None


def textentry(parent=None, message='', title='', def_string='', center=False,
              center_on_screen=False):
    dlg = TextEntryDialog(parent,
                          message, caption=title, value=def_string)
    if center:
        dlg.Centre()
    if center_on_screen:
        dlg.CentreOnScreen()
    if dlg.ShowModal() == wx.ID_OK:
        new_name = str(dlg.GetValue())
        dlg.Destroy()
        return True, new_name

    dlg.Destroy()
    return False, ''


def textselect(parent=None, message='', title='', def_string='',
               center=False, choices=[''],
               center_on_screen=False,
               endmodal_on_lastvalue=False):
    s = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
         "choices": choices}

    if def_string == '':
        def_string = choices[0]
    if message != '':
        ll = [[None, message, 2, None],
              ['Selection', def_string,  104,  s], ]
    else:
        ll = [['Selection', def_string,  104,  s], ]
    from ifigure.utils.edit_list import EditListDialog

    if endmodal_on_lastvalue:
        endmodal_lastvalue = endmodal_on_lastvalue
    else:
        endmodal_lastvalue = None
    dlg = EditListDialog(parent, wx.ID_ANY, title, ll,
                         endmodal_value=endmodal_lastvalue)
    if center:
        dlg.Centre()
    if center_on_screen:
        dlg.CentreOnScreen()
    val = dlg.ShowModal()
    value = dlg.GetValue()
    #print(val, wx.ID_OK)
    if val == wx.ID_OK:
        dlg.Destroy()
        return True, value[-1]
    dlg.Destroy()
    return False, value[-1]


def message(parent=None, message='', title='', style=0,
            icon=wx.ICON_EXCLAMATION,
            center_on_screen=False,
            center_on_parent=False,
            labels=None):
    if style == 0:
        style0 = wx.OK
    if style == 1:
        style0 = wx.CANCEL
    if style == 2:
        style0 = wx.OK | wx.CANCEL
    if style == 3:
        style0 = wx.OK | wx.NO
    if style == 4:
        style0 = wx.YES | wx.NO
    if style == 5:
        style0 = wx.YES | wx.NO | wx.CANCEL

#    from wx.lib.agw.genericmessagedialog import GenericMessageDialog as dia
    from wx import MessageDialog as dia
    style0 = style0 | icon

    dlg = dia(parent,
              message,
              title,
              style0)
    if labels is not None:
        dlg.SetOKCancelLabels(labels[0], labels[1])
    if center_on_screen:
        dlg.CentreOnScreen()
    if center_on_parent:
        dlg.CentreOnParent()

    ret = dlg.ShowModal()
    if ret == wx.ID_OK:
        ret = 'ok'
    elif ret == wx.ID_CANCEL:
        if style != 3:
            ret = 'cancel'
        else:
            ret = 'no'
    elif ret == wx.ID_YES:
        ret = 'yes'
    elif ret == wx.ID_NO:
        ret = 'no'
    dlg.Destroy()
    return ret


def showtraceback(parent=None, txt='', title="Error", traceback='None\n',
                  center_on_screen=True):
    from ifigure.widgets.dlg_message_scroll import DlgMessageScroll

    dlg = DlgMessageScroll(parent, wx.ID_ANY, title)
    if center_on_screen:
        dlg.CentreOnScreen()
    dlg.update(txt + '\n'+traceback)
    ret = dlg.ShowModal()

    dlg.Destroy()


def progressbar(parent, message, title, count):
    dlg = wx.ProgressDialog(title, message, count, parent)

    def close_dlg(evt, dlg=dlg):
        dlg.Destroy()
    dlg.Bind(wx.EVT_CLOSE, close_dlg)
    return dlg
