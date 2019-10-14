from __future__ import print_function


'''
PostOffice 
simple postoffice to send a file
'''

import wx
import binascii
#import sys, socket, shlex, threading, os, binascii, subprocess, time, tempfile
from ifigure.widgets.passwd_dialog import PasswordDialog, UsernamePasswordDialog
from ifigure.utils.setting_parser import iFigureSettingParser as SP
from ifigure.utils.edit_list import DialogEditList
from ifigure.utils.mailfile import checkPasswd, sendMail
from ifigure.widgets.dlg_preference import PrefComponent
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('PostOffice')

coding = 'utf-8'

class PostOffice(PrefComponent):
    def __init__(self):
        PrefComponent.__init__(self, 'PostOffice')
        p = SP()
        self.setting = p.read_setting('pref.postoffice_config')
        self.passwd = None
        self.username = None
        self.parent = None

    def save_setting(self):
        p = SP()
        p.write_setting('pref.postoffice_config', self.setting)

    def set_parent(self, parent):
        self.parent = parent
        return self

    def ask_passwd(self, parent=None):
        if parent is None:
            parent = self.parent
        p_dlg = UsernamePasswordDialog(parent,
                                       title="Mail Server Connection (SSL)",
                                       label=("Enter Name/Password for SMPT server (" +
                                              self.setting["server"] + ':' + str(self.setting["ssl_port"])+")"))
        a = p_dlg.ShowModal()
        if a == wx.ID_OK:
            if checkPasswd(self.setting["server"],
                           ssl_port=self.setting["ssl_port"],
                           ssl_username=p_dlg.result[0],
                           ssl_passwd=p_dlg.result[1]):
                self.username = p_dlg.result[0]
                self.passwd = binascii.b2a_hex(p_dlg.result[1].encode(coding))
            else:
                print('Wrong username/password')
        p_dlg.Destroy()

    def get_dialoglist(self):
        lists = self._elp_panel_list()
        hints = [None]*len(lists)
        return lists, hints

    def set_dialog_result(self, data):
        self._elp_process_panelvalue(data)

    def edit_setting(self):
        list6 = self._elp_panel_list()
        value = DialogEditList(list6, modal=True,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=None,)
        if value[0] is True:
            self._elp_process_panelvalue(value[1])

    def _elp_panel_list(self):
        list6 = [["Subject (default)", self.setting["default_title"], 0, None],
                 ["Message (default)", self.setting["default_message"], 0, None],
                 ["To (default)", self.setting["default_to"], 0, None],
                 ["Mail server", self.setting["server"], 0, None],
                 ["Use ssl", self.setting["use_ssl"],
                     1, {"values": ["on", "off"]}],
                 ["Ssl port", str(self.setting["ssl_port"]), 0, None], ]
        return list6

    def _elp_process_panelvalue(self, value):
        self.setting["default_title"] = str(value[0])
        self.setting["default_message"] = str(value[1])
        self.setting["default_to"] = str(value[2])
        self.setting["server"] = str(value[3])
        self.setting["use_ssl"] = str(value[4])
        self.setting["ssl_port"] = int(value[5])

    def send_message(self, message='', parent=None):
        if parent is None:
            parent = self.parent
        if self.passwd is None:
            self.ask_passwd(parent=parent)
        if self.passwd is None:
            return

        list6 = [["subject", self.setting["default_title"], 0, None],
                 ["to", self.setting["default_to"], 0, None], ]
#                 ["mail server", self.setting["server"], 0, None],
#                 ["use ssl", self.setting["use_ssl"], 1, {"values":["on", "off"]}],
#                 ["ssl port", str(self.setting["ssl_port"]), 0, None],]

        value = DialogEditList(list6, modal=True,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=parent,)

        if value[0] is True:
            subject = str(value[1][0])
            message = message
            to = str(value[1][1])
        else:
            return

        passwd = binascii.a2b_hex(self.passwd)
        sendMail([to], subject, message, files=[],
                 server=self.setting["server"],
                 ssl=(self.setting["use_ssl"] == "on"),
                 ssl_port=int(self.setting["ssl_port"]),
                 ssl_username=self.username,
                 ssl_passwd=passwd)

    def send_file(self, file, parent=None):
        if parent is None:
            parent = self.parent
        if self.passwd is None:
            self.ask_passwd(parent=parent)
        if self.passwd is None:
            return

        list6 = [["To:", self.setting["default_to"], 0, None],
                 ["Subject:", self.setting["default_title"], 0, None],
                 [None, self.setting["default_message"], 35, {'nlines': 10}], ]

#                 ["mail server", self.setting["server"], 0, None],
#                 ["use ssl", self.setting["use_ssl"], 1, {"values":["on", "off"]}],
#                 ["ssl port", str(self.setting["ssl_port"]), 0, None],]

        value = DialogEditList(list6, modal=True,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None, title='Edit Message for Send File',
                               parent=parent, size=(400, -1))

        if value[0] is True:
            to = str(value[1][0])
            subject = str(value[1][1])
            message = str(value[1][2])

        else:
            return

        passwd = binascii.a2b_hex(self.passwd).decode(coding)
        
        sendMail([to], subject, message, files=[file],
                 server=self.setting["server"],
                 ssl=(self.setting["use_ssl"] == "on"),
                 ssl_port=int(self.setting["ssl_port"]),
                 ssl_username=self.username,
                 ssl_passwd=passwd)
