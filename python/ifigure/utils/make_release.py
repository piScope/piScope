from __future__ import print_function
#
#  description
#     make_release generate a release version directory
#     if runs hg log and hg summary
#

import shutil
import os
import time
import subprocess
import traceback
import ifigure

check = ['ifigure_app', 'startup', 'add_on']


def header_text(f):
    txt = ('#  Title:\t' + f,
           '#',
           '#  Author:\tSyun\'ichi Shiraiwa',
           '#',
           '#  E-mail:\tshiraiwa@psfc.mit.edu',
           '#',
           '#  Notice:\t Beta version restriction.',
           '#         \t Do not copy this version. Although piScope will',
           '#         \t distributed under GPL, the distributing this version',
           '#         \t and any derived work is not allowd',
           '#*******************************************',
           '#     Copyright(c) 2012-14 S. Shiraiwa      ',
           '#*******************************************',
           '',)
    return '\n'.join(txt)


def make_header(release='piscope_release'):
    source = os.path.dirname(os.path.dirname(
        os.path.dirname(ifigure.__file__)))
    root = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(ifigure.__file__))))
    release = os.path.join(root, release)

    c = 0
    for dirpath, dirname, filenames in os.walk(release):
        for f in filenames:
            path = os.path.join(dirpath, f)
            if path.endswith('~'):
                os.remove(path)
                continue

            if path.endswith('.py'):
                lines = open(path, 'r').readlines()
                if len(lines) == 0:
                    continue
                if lines[0].startswith('#!'):
                    continue
                for l in lines:
                    if l.upper().find('COPYRIGHT(C)') != -1:
                        print(('skipping ', path))
                        break
                else:
                    #                     print 'processing ', path
                    fid = open(path, 'w')
                    fid.write(header_text(f))
                    for l in lines:
                        fid.write(l)
                    fid.close()
                    c = c + 1
    print(('total ', str(c) + ' files are processed'))
#            if c > 3: return


def check_print():
    # check if print statement is used
    source = os.path.dirname(os.path.dirname(
        os.path.dirname(ifigure.__file__)))

    c = 0
    for dirpath, dirname, filenames in os.walk(source):
        for f in filenames:
            path = os.path.join(dirpath, f)
            if path.endswith('~'):
                os.remove(path)
                continue

            if path.endswith('.py'):
                lines = open(path, 'r').readlines()
                if len(lines) == 0:
                    continue
                for l in lines:
                    if l.upper().find('PRINT ') != -1:
                        if l.find('#') != -1:
                            if l.find('#') < l.upper().find('PRINT '):
                                continue
                        print((path, l))
                        c = c + 1
    print(('total ', str(c) + ' PRINT statement detected'))
#            if c > 3: return


def make_release(release='piscope_release', version='beta'):
    '''
    make_release(release = 'piscope_release', version = 'beta')
    '''
    source = os.path.dirname(os.path.dirname(
        os.path.dirname(ifigure.__file__)))

    pwd = os.getcwd()
    try:
        os.chdir(source)
        log = subprocess.check_output(['git', 'log'])
        fid = open(os.path.join(source, 'git_log'), 'w')
        fid.write(log)
        fid.close()
        #log = subprocess.check_output(['hg', 'summary'])
        #fid = open(os.path.join(source, 'hg_summary'), 'w')
        # fid.write(log)
        # fid.close()
        root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(ifigure.__file__))))
        release = os.path.join(root, release)
        version_file = os.path.join(release, 'python', 'ifigure', 'version.py')

        if os.path.exists(release):
            try:
                shutil.rmtree(release)
            except:
                pass
        shutil.copytree(source, release)

        for dirpath, dirname, filenames in os.walk(release):
            for f in filenames:

                path = os.path.join(dirpath, f)

                if path.endswith('~'):
                    os.remove(path)
                    continue
    #            if any([path.find(x) != -1 for x in check]): continue
    #            if path.endswith('.py'):
    #                 os.remove(path)
                if f.startswith('._'):
                    #                 print path
                    os.remove(path)
                    continue
                if f.startswith('.DS_Store'):
                    os.remove(path)
                    continue
                if f.startswith('.nfs'):
                    print(('removing ', path))
                    os.remove(path)
                    continue

    #            print 'processed ', path
        fid = open(version_file, 'w')
        fid.write('ifig_version = "' + time.strftime('%Y %B %d') +
                  '_' + version + ' with OpenGL backend"\n')
        fid.close()

        make_header(release=release)
    except:
        traceback.print_exc()
    finally:
        os.chdir(pwd)
