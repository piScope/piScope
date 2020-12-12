'''
 addon_utils:
       utility functions commonly used in addons

       onOpenOrg : open original file
       onOpenCurrent : open current file
       onLoadFile : ask user an input and copy a file to
                    owndir as working file.
                    it also ask if copy original file into
                    owndir as original file. this is useful
                    if work is done at different machines.

'''
import os
import wx
import shutil
import tempfile
import ifigure.events
from ifigure.utils.edit_list import DialogEditList


def onOpenOrg(td):
    import ifigure.events

    file = td.path2fullpath('ofile_pathmode',
                            'ofile_path')
    if file == '':
        return
    ifigure.events.SendEditFileEvent(td, None, file, readonly=True)


def onWriteFile(td, filename='', dir='', txt='',
                message='Select File to Save',
                wildcard='Any|*'):
    if filename == '':
        open_dlg = wx.FileDialog(None,
                                 message=message,
                                 defaultDir=dir,
                                 style=wx.FD_SAVE,
                                 wildcard=wildcard)
        if open_dlg.ShowModal() != wx.ID_OK:
            open_dlg.Destroy()
            return
        else:
            filename = str(open_dlg.GetPath())
            open_dlg.Destroy()

    with tempfile.NamedTemporaryFile(
            'w', dir=os.path.dirname(filename), delete=False) as tf:
        tf.write(txt)
        tempname = tf.name
    if not os.path.isabs(filename):
        filename = os.path.join(td.owndir(), filename)
    if os.path.exists(filename):
        os.remove(filename)
    shutil.move(tempname, filename)
#    fid = open(filename, 'w')
#    print "writing contents to ", filename
#    fid.write(txt)
#    fid.close()


def onOpenCurrent(td, modename='addon_pathmode',
                  pathname='addon_path'):

    import ifigure.events
    file = td.path2fullpath(modename, pathname)
    ifigure.events.SendEditFileEvent(td, None, file, readonly=False)


def onLoadFile(td, message="Select File",
               modename='addon_pathmode',
               pathname='addon_path',
               extname='addon_ext',
               wildcard='Any|*',
               ask_org_copy=True,
               file=None,
               reject_loc=None):
    '''
    onLoadFile ask user an file to read.
    copy it to its own directory as filename.
    also another copy is made as filename + '.org'
    for future record

    if ask_org_copy = False: it automatically copy original for
    read only data and make a duplicate file for edit. It is only
    useful when the file size is small
    '''
    if td.getvar("original file") is not None:
        dir = os.path.dirname(td.getvar("original file"))
    else:
        dir = '.'
    if not os.path.exists(dir):
        dir = ''

    if file is None:
        open_dlg = wx.FileDialog(None,
                                 message=message,
                                 defaultDir=dir,
                                 style=wx.FD_OPEN, wildcard=wildcard)
        if open_dlg.ShowModal() != wx.ID_OK:
            open_dlg.Destroy()
            return False
        file = open_dlg.GetPath()
        open_dlg.Destroy()

    if reject_loc is not None:
        rmode, rpath = td.fullpath2path(td, file)
        if rmode in reject_loc:
            m = 'Improper import source location'
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return

    try:
        # this may fail if owndir does not exist
        #print(os.path.dirname(file), td.owndir())
        samefile = os.path.samefile(os.path.dirname(file), td.owndir())
        # print(samefile)
    except BaseException:
        samefile = False
    if ask_org_copy and not samefile:
        from ifigure.widgets.dlg_fileimportmode import DlgFileimportmode
        copy_file, pathmodes, ret = DlgFileimportmode(td,
                                                      ask_copyorg=True)

        '''
        choices = ["auto", "abs", "home", "proj"]
        if td.get_extfolderpath() is not None:
            choices.append(td.get_extfolderpath())
        list6 = [[None,  [True, ['auto']], 127,
                 [{'text':'copy file to project'},
                  {'elp':[['Select path mode', 'auto', 4,
                           {"style":wx.CB_READONLY,
                            "choices": choices}],]}], ],
                 [None, False, 3,
                 {"text":"copy original to project as a separate file"}], ]
        value = DialogEditList(list6, modal = True,
                     style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                     tip = None,
                     parent=None,)

        if not value[0]: return
        ret = value[1][1]
        copy_file = value[1][0][0]
        pathmodes = value[1][0][1]
        if str(pathmodes[0]) == 'auto':
           pathmodes = ['proj', 'home', 'abs']
        '''
    else:
        ret = True
        copy_file = True

    for name, child in td.get_children():
        child.destroy()
    if not td.has_owndir():
        td.mk_owndir()
    od = td.owndir()

    if ret:
        new_ofile = os.path.join(od, os.path.basename(file) + '.org')
        shutil.copyfile(file, new_ofile)
        td.setvar('ofile_pathmode', 'owndir')
        td.setvar('ofile_path', os.path.basename(new_ofile))
        if not 'ofile_path' in td._items:
            td._items.append('ofile_path')
#         td._items.append('ofile_path')
    else:
        new_ofile = file
        td.setvar('ofile_pathmode', 'abs')
        td.setvar('ofile_path', file)
        if 'ofile_path' in td._items:
            td.remove_ownitem(items=['ofile_path'])
            td._items.remove('ofile_path')

    # nl_file is the file to be edited
    if copy_file:
        nl_file = os.path.join(od, os.path.basename(file))
        print(nl_file)
        try:
            # this may fail if owndir does not exist
            if os.path.exists(nl_file):
                samefile = os.path.samefile(file, nl_file)
            else:
                samefile = True
        except BaseException:
            import traceback
            traceback.print_exc()
            samefile = False
        if not samefile:
            print("not the same file")
            #td.remove_ownitem(items=[pathname])
            sss = nl_file.split('.')
            nl_file = '.'.join(sss[:-1])+'1.'+sss[-1]
        shutil.copyfile(file, nl_file)
        td.set_path_pathmode(nl_file, modename, pathname, extname)
    else:
        td.remove_ownitem(items=[pathname])
        td.set_path_pathmode(file, modename, pathname,
                             extname, checklist=pathmodes)
    return True
