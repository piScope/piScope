# this file is incomplete

mode = 'emacs'
code_table = {7801: 'C-N',
              8001: 'C-P',
              6801: 'C-X',
              7001: 'C-P',
              6601: 'C-B',
              8901: 'C-Y',
              8701: 'C-W',
              8702: 'A-W',
              8302: 'C-S',
              9001: 'C-Z',
              6901: 'C-E',
              7501: 'C-K',
              6501: 'C-A', }


def controlDown(key_evt):
    if hasattr(key_evt, 'RawControlDown'):
        controlDown = key_evt.RawControlDown()
    else:
        controlDown = key_evt.ControlDown()
    return controlDown


def interpret_keycombination(key_evt):

    if hasattr(key_evt, 'RawControlDown'):
        mod = (key_evt.RawControlDown() +
               key_evt.AltDown()*2 +
               key_evt.ShiftDown()*4 +
               key_evt.MetaDown()*8)
    else:
        mod = (key_evt.ControlDown() +
               key_evt.AltDown()*2 +
               key_evt.ShiftDown()*4 +
               key_evtprev.MetaDown()*8)

    code = key_evt.GetKeyCode()

    if code*100+mod in code_table:
        return code_table[code*100+mod]
    return None
