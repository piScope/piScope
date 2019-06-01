import wx
from ifigure.utils.edit_list import DialogEditList


def DlgFileimportmode(folder, parent=None, ask_copyorg=False):

    choices = ["auto", "abs", "home", "proj"]
    if folder.get_extfolderpath() is not None:
        choices.append(folder.get_extfolderpath())
    list6 = [[None,  [True, ['auto']], 127,
              [{'text': 'copy file to project'},
               {'elp': [['Select path mode', 'auto', 4,
                         {"style": wx.CB_READONLY,
                          "choices": choices}], ]}], ], ]
    if ask_copyorg:
        list6.append([None, False, 3,
                      {"text": "copy original to project as a separate file"}])
    value = DialogEditList(list6, modal=True,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                           tip=None,
                           parent=parent,)

    if not value[0]:
        return

#    print value[1]
#    ret = value[1][1]
    copy_file = value[1][0][0]
    path_modes = value[1][0][1]
    if str(path_modes[0]) == 'auto':
        path_modes = ['proj', 'home', 'abs']

    copy_org = False
    if ask_copyorg:
        copy_org = value[1][1]

    return copy_file, path_modes, copy_org
