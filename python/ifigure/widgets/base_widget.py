#
#   this is for the memo of the routines to be
#   implemented for widgets used in propertyeditor
#
#


class base_widget(object):
    def __init__(self):
        self.property = ''

    def SetEditorValue(self,  artist=None):
        # this shouuld define how to update
        # gui based on the data in ifigure_canvas
        pass

    def SetCanvasValue(self,  artist=None):
        pass
        # this shouuld define how to update
        # ifigure_canvas based on GUI
