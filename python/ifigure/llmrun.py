import sys
import glob
import os
from os.path import dirname, join

def llmrun():
    venv_bin_dir = dirname(sys.argv[0])
    venv_root = dirname(venv_bin_dir)

    # Dynamically locate the site-packages directory (handles any python3.x version)
    # Find the site-packages directory 
    lib_dir = join(venv_root, "lib")

    # Match paths like lib/site-packages and lib/*/site-packages
    pattern1 = os.path.join(lib_dir, "site-packages")
    pattern2 = os.path.join(lib_dir, "*", "site-packages")

    # Find matches that are actual directories
    matches = [p for p in glob.glob(pattern1) + glob.glob(pattern2) if os.path.isdir(p)]

    # Extract the first match or default to an empty string
    site_packages = matches[0] if matches else ""
    
    sys.path.insert(0, site_packages)
    args = [sys.executable] + list(sys.argv[1:])
    os.execvp(sys.executable, args)

    
