import wx.stc as stc


def set_python_style(obj):
    from ifigure.widgets.script_editor import faces
    # my own style....
    # Global default styles for all languages
    # self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "fore:#440000,face:%(mono)s,size:%(size)d" % faces)
    # Default
    obj.StyleSetSpec(stc.STC_P_DEFAULT,
                     "fore:#0000ff,face:%(helv)s,size:%(size)d" % faces)
    obj.StyleClearAll()  # Reset all to be like the default
    # Comments
    obj.StyleSetSpec(stc.STC_P_COMMENTLINE,
                     "fore:#007F00,size:%(size)d" % faces)
    # Number
    obj.StyleSetSpec(stc.STC_P_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
    # String
    obj.StyleSetSpec(stc.STC_P_STRING, "fore:#7F007F,size:%(size)d" % faces)
    # Single quoted string
    obj.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#7F007F,size:%(size)d" % faces)
    # Keyword
    obj.StyleSetSpec(stc.STC_P_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
    # Triple quotes
    obj.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#7F0000,size:%(size)d" % faces)
    # Triple double quotes
    obj.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,
                     "fore:#7F0000,size:%(size)d" % faces)
    # Class name definition
    obj.StyleSetSpec(stc.STC_P_CLASSNAME,
                     "fore:#0000FF,bold,underline,size:%(size)d" % faces)
    # Function or method name definition
    obj.StyleSetSpec(stc.STC_P_DEFNAME,
                     "fore:#007F7F,bold,size:%(size)d" % faces)
    # Operators
    obj.StyleSetSpec(stc.STC_P_OPERATOR, "bold,size:%(size)d" % faces)
    # Identifiers
    obj.StyleSetSpec(stc.STC_P_IDENTIFIER,
                     "fore:#000000,size:%(size)d" % faces)
    # Comment-blocks
    obj.StyleSetSpec(stc.STC_P_COMMENTBLOCK,
                     "fore:#7F7F7F,size:%(size)d" % faces)
    # End of line where string is not closed
    obj.StyleSetSpec(stc.STC_P_STRINGEOL,
                     "fore:#000000,back:#E0C0E0,eol,size:%(size)d" % faces)


def set_cpp_style(obj):
    from script_editor import faces
    # my own style....
    # Global default styles for all languages
    # self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "fore:#440000,face:%(mono)s,size:%(size)d" % faces)
    # Default
    obj.StyleSetSpec(stc.STC_C_DEFAULT,
                     "fore:#0000ff,face:%(helv)s,size:%(size)d" % faces)
    obj.StyleClearAll()  # Reset all to be like the default
    # Comments
    obj.StyleSetSpec(stc.STC_C_COMMENTLINE,
                     "fore:#007F00,size:%(size)d" % faces)
    # Number
    obj.StyleSetSpec(stc.STC_C_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
    # String
    obj.StyleSetSpec(stc.STC_C_STRING, "fore:#7F007F,size:%(size)d" % faces)
    # Single quoted string
    obj.StyleSetSpec(stc.STC_C_CHARACTER, "fore:#7F007F,size:%(size)d" % faces)
    # Keyword
    obj.StyleSetSpec(stc.STC_C_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
    # Class name definition
    obj.StyleSetSpec(stc.STC_C_GLOBALCLASS,
                     "fore:#0000FF,bold,underline,size:%(size)d" % faces)
    # Operators
    obj.StyleSetSpec(stc.STC_C_OPERATOR, "bold,size:%(size)d" % faces)
    # Identifiers
    obj.StyleSetSpec(stc.STC_C_IDENTIFIER,
                     "fore:#000000,size:%(size)d" % faces)
    # Comment-blocks
    obj.StyleSetSpec(stc.STC_C_COMMENTDOC,
                     "fore:#00F700,size:%(size)d" % faces)
    # Comment-blocks
    obj.StyleSetSpec(stc.STC_C_COMMENTDOCKEYWORD,
                     "fore:#007F00,size:%(size)d" % faces)
    # Comment-blocks
    obj.StyleSetSpec(stc.STC_C_COMMENTDOCKEYWORDERROR, "fore:#007F00,size:%(size)d"
                     % faces)
    # End of line where string is not closed
    obj.StyleSetSpec(stc.STC_P_STRINGEOL,
                     "fore:#000000,back:#E0C0E0,eol,size:%(size)d" % faces)


def set_f77_style(obj):
    from ifigure.widgets.script_editor import faces
    # my own style....
    # Global default styles for all languages
    # self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "fore:#440000,face:%(mono)s,size:%(size)d" % faces)
    # Default
    obj.StyleSetSpec(stc.STC_F_DEFAULT,
                     "fore:#0000ff,face:%(helv)s,size:%(size)d" % faces)
    obj.StyleClearAll()  # Reset all to be like the default
    # Comments
    obj.StyleSetSpec(stc.STC_F_COMMENT, "fore:#007F00,size:%(size)d" % faces)
    # Number
    obj.StyleSetSpec(stc.STC_F_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
    # String
    obj.StyleSetSpec(stc.STC_F_STRING1, "fore:#7F007F,size:%(size)d" % faces)
    # String
    obj.StyleSetSpec(stc.STC_F_STRING2, "fore:#7F007F,size:%(size)d" % faces)
    # Keyword
    obj.StyleSetSpec(stc.STC_F_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
    # Keyword
    obj.StyleSetSpec(
        stc.STC_F_WORD2, "fore:#00007F,bold,size:%(size)d" % faces)
    # Keyword
    obj.StyleSetSpec(
        stc.STC_F_WORD3, "fore:#00007F,bold,size:%(size)d" % faces)
    # Preprocessor
    obj.StyleSetSpec(stc.STC_F_PREPROCESSOR,
                     "fore:#7F7F7F,size:%(size)d" % faces)
    # Operators
    obj.StyleSetSpec(stc.STC_F_OPERATOR, "bold,size:%(size)d" % faces)
    # Operators
    obj.StyleSetSpec(stc.STC_F_OPERATOR2, "bold,size:%(size)d" % faces)
    # Identifiers
    obj.StyleSetSpec(stc.STC_F_IDENTIFIER,
                     "fore:#000000,size:%(size)d" % faces)
    # End of line where string is not closed
    obj.StyleSetSpec(stc.STC_F_STRINGEOL,
                     "fore:#000000,back:#E0C0E0,eol,size:%(size)d" % faces)


def set_fortran_style(obj):
    from ifigure.widgets.script_editor import faces
    # my own style....
    # Global default styles for all languages
    # self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "fore:#440000,face:%(mono)s,size:%(size)d" % faces)
    # Default
    obj.StyleSetSpec(stc.STC_F_DEFAULT,
                     "fore:#0000ff,face:%(helv)s,size:%(size)d" % faces)
    obj.StyleClearAll()  # Reset all to be like the default
    # Comments
    obj.StyleSetSpec(stc.STC_F_COMMENT, "fore:#007F00,size:%(size)d" % faces)
    # Number
    obj.StyleSetSpec(stc.STC_F_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
    # String
    obj.StyleSetSpec(stc.STC_F_STRING1, "fore:#7F007F,size:%(size)d" % faces)
    # String
    obj.StyleSetSpec(stc.STC_F_STRING2, "fore:#7F007F,size:%(size)d" % faces)
    # Keyword
    obj.StyleSetSpec(stc.STC_F_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
    # Keyword
    obj.StyleSetSpec(
        stc.STC_F_WORD2, "fore:#00007F,bold,size:%(size)d" % faces)
    # Keyword
    obj.StyleSetSpec(
        stc.STC_F_WORD3, "fore:#00007F,bold,size:%(size)d" % faces)
    # Preprocessor
    obj.StyleSetSpec(stc.STC_F_PREPROCESSOR,
                     "fore:#7F7F7F,size:%(size)d" % faces)
    # Operators
    obj.StyleSetSpec(stc.STC_F_OPERATOR, "bold,size:%(size)d" % faces)
    # Operators
    obj.StyleSetSpec(stc.STC_F_OPERATOR2, "bold,size:%(size)d" % faces)
    # Identifiers
    obj.StyleSetSpec(stc.STC_F_IDENTIFIER,
                     "fore:#000000,size:%(size)d" % faces)
    # End of line where string is not closed
    obj.StyleSetSpec(stc.STC_F_STRINGEOL,
                     "fore:#000000,back:#E0C0E0,eol,size:%(size)d" % faces)
