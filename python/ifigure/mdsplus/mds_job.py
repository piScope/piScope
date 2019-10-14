from __future__ import print_function
class MDSjob(object):
    def __init__(self, command, *args):
        self.command = command
        self.params = args

    def __repr__(self):
        return str(self.command) + ' ' + str(self.params)

    def print_job(self):
        print((self.command, self.params))

    def txt_job(self):
        return (self.command, self.params)
