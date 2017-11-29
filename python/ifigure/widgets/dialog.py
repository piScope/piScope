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
import wx, os
from ifigure.utils.wx3to4 import TextEntryDialog

def read(parent=None, message='Select file to read', wildcard='*', defaultfile=''):

    open_dlg = wx.FileDialog (parent, message=message,
                              wildcard=wildcard,style=wx.FD_OPEN)
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

def readdir(parent=None, message='Select directory to read', wildcard='*', defaultfile=''):

    open_dlg = wx.DirDialog (parent, message=message,)
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
          warn_overwrite = False):
    '''
    wrap FileDialog, Note that defaultfile can be absolute path
    '''
    style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT if warn_overwrite else wx.FD_SAVE
    
    open_dlg = wx.FileDialog (parent, message=message,
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
    dlg = wx.DirDialog (parent, message=message)
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
    dlg = wx.DirDialog (parent, message=message)
    path = ''
    wc = ''
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        dlg.Destroy()
        return path        
    else:
        dlg.Destroy()
        return None

def textentry(parent=None, message='', title='', def_string='', center=False):
    dlg = TextEntryDialog(parent, 
          message, caption=title, value=def_string)
    if center: dlg.Centre()
    if dlg.ShowModal() == wx.ID_OK:
        new_name = str(dlg.GetValue())
        dlg.Destroy()
        return True, new_name

    dlg.Destroy()
    return False, ''

def textselect(parent=None, message='', title='', def_string='', 
              center=False, choices = ['']):
    s ={"style":wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER,
                "choices": choices}
    if message != '':
        ll = [[None, message, 2, None],
              ['Selection', choices[0],  104,  s],]
    else:
        ll = [['Selection', choices[0],  104,  s],]
    from ifigure.utils.edit_list import EditListDialog

    dia = EditListDialog(parent, wx.ID_ANY, title, ll)
    if center: dia.Centre()
    val = dia.ShowModal()
    value=dia.GetValue()
    if val == wx.ID_OK:
       dia.Destroy()
       return True, value[-1]
    dia.Destroy()
    return False, value[-1]

def message(parent=None, message='', title='', style=0, 
            icon=wx.ICON_EXCLAMATION):
    if style == 0:
       style0 = wx.OK
    if style == 1:
       style0 = wx.CANCEL
    if style == 2:
       style0 = wx.OK|wx.CANCEL
    if style == 3:
       style0 = wx.OK|wx.NO
    if style == 4:
       style0 = wx.YES|wx.NO
    if style == 5:
       style0 = wx.YES|wx.NO|wx.CANCEL

    from wx.lib.agw.genericmessagedialog import GenericMessageDialog as dia
#    from wx.lib.agw.genericmessagedialog import GMD_USE_AQUABUTTONS as g
#    from wx import MessageDialog as dia
    style0 = style0|icon
#    print icon
    dlg = dia(parent,
                         message, 
                         title, 
                         style0)

    ret=dlg.ShowModal()
    if ret  == wx.ID_OK:
       ret = 'ok'
    elif ret  == wx.ID_CANCEL:
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

def showtraceback(parent = None, txt='', title='', traceback='None\n'):
    dlg=wx.MessageDialog(parent, 
                         txt + '\n'+
                         traceback,
                         title, 
                         wx.OK)
    ret=dlg.ShowModal()
    dlg.Destroy()

def progressbar(parent, message, title, count):   

    dlg = wx.ProgressDialog(title, message, count, parent)
    def close_dlg(evt, dlg=dlg):
        dlg.Destroy()
    dlg.Bind(wx.EVT_CLOSE, close_dlg)
    return dlg

