from __future__ import print_function
import hgapi
import os
import traceback


def pull(dir1, dir2, dry_run=False):
    '''
       pull from dir2 to dir1

       example) pull('/Users/shiraiwa/hg_root', 'ssh://cmodws60/hg_root', dry_run = False)
    '''
    for root, dirs, files in os.walk(dir1):
        if '.hg' in dirs:
            dirs.remove('.hg')
            repo = hgapi.Repo(root)
            url = dir2+root[len(dir1):]
            try:
                out = repo.hg_command('incoming', url)
                lines = out.split('\n')
                numc = len([1 for l in lines if l.startswith('changeset')])
                if numc > 0:
                    print(str(numc) + ' is coming from ' + url)

            except:
                if traceback.format_exc().find('no changes found') != -1:
                    print(url + ' is updated')
                    continue
                if traceback.format_exc().find('There is no Mercurial') != -1:
                    print('no repo found in '+url)
                    continue
                traceback.print_exc()
                continue
            if dry_run:
                continue
            try:
                repo.hg_pull(url)
            except:
                traceback.print_exc()


def push(dir1, dir2, dry_run=False):
    '''
       pull from dir2 to dir1

       example) pull('/Users/shiraiwa/hg_root', 'ssh://cmodws60/hg_root', dry_run = False)
    '''
    for root, dirs, files in os.walk(dir1):
        if '.hg' in dirs:
            dirs.remove('.hg')
            repo = hgapi.Repo(root)
            url = dir2+root[len(dir1):]
            try:
                out = repo.hg_command('outgoing', url)
                lines = out.split('\n')
                numc = len([1 for l in lines if l.startswith('changeset')])
                if numc > 0:
                    print(str(numc) + ' is coming from ' + url)

            except:
                if traceback.format_exc().find('no changes found') != -1:
                    print(url + ' is updated')
                    continue
                if traceback.format_exc().find('There is no Mercurial') != -1:
                    print('no repo found in '+url)
                    continue
                traceback.print_exc()
                continue
            if dry_run:
                continue
            try:
                repo.hg_push(url)
            except:
                traceback.print_exc()
