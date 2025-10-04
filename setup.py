from setuptools import setup
import os


def long_description():
    rootdir = os.path.abspath(os.path.dirname(__file__))    
    with open(os.path.join(rootdir, 'README.md'), encoding='utf-8') as f:
        return f.read()

def run_setup():
    setup(
       long_description = long_description(),
       long_description_content_type = "text/markdown",)

def main():
    run_setup()


if __name__ == '__main__':
    main()
