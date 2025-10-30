import os
import sys
import shutil
import subprocess

from setuptools import setup
from setuptools.command.install import install as _install

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_build_system"))  # nopep8

from build_utils import write_desktop_file


def long_description():
    rootdir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(rootdir, 'README.md'), encoding='utf-8') as f:
        return f.read()


class Install(_install):
    def run(self):
        if sys.platform in ("linux", "linux2"):
            write_desktop_file()
        else:
            pass
        _install.run(self)


if __name__ == '__main__':
    cmdclass = {'install': Install, }
    setup(
        cmdclass=cmdclass,
        long_description=long_description(),
        long_description_content_type="text/markdown",)
