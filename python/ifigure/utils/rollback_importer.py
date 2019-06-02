import sys
import __builtin__


class RollbackImporter:
    def __init__(self):
        "Creates an instance and installs as the global importer"
        self.previousModules = sys.modules.copy()
        self.realImport = __builtin__.__import__
        __builtin__.__import__ = self._import
        self.newModules = {}

    def _import(self, name, globals=None, locals=None, fromlist=[]):
        result = self.realImport(*(name, globals, locals, fromlist))
        self.newModules[name] = 1
        return result

    def uninstall(self):
        for modname in self.newModules:
            if modname not in self.previousModules:
                # Force reload when modname next imported
                del(sys.modules[modname])
        __builtin__.__import__ = self.realImport
