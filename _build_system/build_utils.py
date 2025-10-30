"""
Helper functions for setup.py
"""

import os
import sys
import subprocess

__all__ = ("abspath", "write_desktop_file")


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def install_prefix():
    import site
    if hasattr(site, "getusersitepackages"):
        usersite = site.getusersitepackages()
    else:
        usersite = site.USER_SITE

    print("running external_install_prefix with the following parameters")
    print("   sys.argv :", sys.argv)
    print("   sys.prefix :", sys.prefix)
    print("   usersite :", usersite)

    if '--user' in sys.argv:
        path = usersite
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    else:
        # when prefix is given...let's borrow pip._internal to find the location ;D
        import pip._internal.locations
        path = pip._internal.locations.get_scheme(
            "petram").purelib
        return path


def write_desktop_file():
    prefix = install_prefix()
    bindir = os.path.dirname(os.path.dirname(os.path.dirname(prefix)))
    bindir = os.path.join(bindir, "bin")

    if os.access("/usr/local/share", os.W_OK):
        share_dir = "/usr/local/share"
    else:
        share_dir = os.path.join(os.getenv("HOME"), '.local', 'share')
    desktop_dir = os.path.join(share_dir, 'applications')

    os.makedirs(desktop_dir, exist_ok=True)

    dfile = os.path.join(desktop_dir, "piscope.desktop")

    try:
        print(f"Writing desktop file '{dfile}' ...")
        fid = open(dfile, "w")
        fid.write("[Desktop Entry]\n")
        fid.write("Name=piScope\n")
        fid.write("Type=Application\n")
        fid.write("Exec="+bindir + "/piscope -d %F\n")
        fid.write("Icon="+prefix +
                  "/ifigure/resources/icon/app_logo_middle.png\n")
        fid.write("Terminal=true\n")
        fid.write("StartupWMClass=Piscope\n")
        fid.write("Categories=Science;\n")
        fid.close()

        # Update the icon cache for the user
        print("Updating icon cache...")
        subprocess.run(["update-desktop-database", share_dir], check=True)

        print("Done successfully.")
    except Exception as e:
        print(f"An error occurred during icon installation: {e}")
