from __future__ import print_function

'''

   Export (partial) Figure Data to HDF file



'''
import traceback
import six
from collections import OrderedDict

from ifigure.widgets.artist_widgets import listparam, call_getter


def set_default_export_flag(obj, name, flag):
    from ifigure.mto.fig_page import FigPage
    from ifigure.mto.fig_axes import FigAxes

    name = (name, )
    if isinstance(obj, FigPage):
        flag[name] = True
        return
    if isinstance(obj, FigAxes):
        flag[name] = False
        return
    try:
        dd = obj.export()
    except NotImplementedError:
        flag[name] = False
        return
    flag[name] = True


def select_unique_properties(parent, dataset, flags):
    nb_done = []
    page = parent.get_figpage()
    for name, child in parent.get_children():
        nb = child.get_namebase()
        if nb in nb_done:
            continue
        nb_done.append(nb)
        objs = [child for name, child in parent.get_children()
                if child.get_namebase() == nb]
        names = [page.name + '.' + '.'.join(page.get_td_path(obj)[1:])
                 for obj in objs]
        if len(objs) == 1:
            labels = (names[0], 'property')
            flags[labels] = False
            for key in six.iterkeys(dataset[names[0]]['property']):
                labels = (names[0], 'property', key)
                flags[labels] = False
        props = [dataset[name]['property'] for name in names]
        pp = tuple()
        for p in props:
            pp = pp + tuple(p)
        for x in set(pp):
            value = not (len(set([p.get(x, None) for p in props])) == 1)
            if value:
                for name in names:
                    labels = (name, 'property')
                    flags[labels] = value
            for name in names:
                labels = (name, 'property', x)
                flags[labels] = value


def select_unique_properties_all(page, dataset, flags):
    for obj in page.walk_tree():
        if obj.num_child() > 0:
            select_unique_properties(obj, dataset, flags)
    for key in six.iterkeys(flags):
        if (key[0] == page.name and len(key) >= 2 and
                key[1] == 'property'):
            flags[key] = False


def set_all_properties_all(flags, value):
    keys = list(flags)
    for labels in keys:
        if len(labels) < 2:
            continue
        if labels[1] == 'property':
            flags[labels] = value
            
    keys = list(flags)
    for labels in keys:
        if not (labels[0], 'property') in flags:
            flags[(labels[0], 'property')] = value


def get_all_properties(obj):
    ret = obj.property_for_shell()
    tags = None
    if isinstance(ret, tuple):
        tab = ret[0]
        props = ret[1]
        if len(ret) == 3:
            tags = ret[2]
    else:
        tab = ['']
        props = [ret]
    if tags is None:
        tags = ['']*len(props)

    ll = []
    for tag, plist in zip(tags, props):
        for p in plist:
            if tag == '':
                ll.append(('',  listparam[p][6], listparam[p]))
            else:
                ll.append((tag, listparam[p][6], listparam[p]))

    props = {}
    for lll in ll:
        tag, name, lp = lll
        ret = [call_getter(a, lp, tab=tag) for a in obj._artists]
        if len(ret) == 1:
            ret = str(ret[0])
        else:
            ret = [str(x) for x in ret]
        if tag == '':
            props[name] = ret
        else:
            props['_'.join((tag, name))] = ret
    return props


def build_data(page, export_flag=None,
               metadata=None,  verbose=True):
    if export_flag is None:
        export_flag = {}
    if metadata is None:
        metadata = {}
    book = page.get_figbook()
    page.assign_default_file_metadata()
    dataset = OrderedDict()

    for obj in page.walk_tree():
        if obj is page:
            name = page.name
        else:
            name = page.name + '.' + '.'.join(page.get_td_path(obj)[1:])

        dataset[name] = {}
        set_default_export_flag(obj, name, export_flag)
        try:
            dd = obj.export()
        except NotImplementedError:
            if verbose:
                print(name + ' does not have data to export')
        except:
            print('Unexpected error')
            raise
        else:
            if len(dd) == 1:
                dataset[name]['data'] = dd[0]
            else:
                for kk,  ddd in enumerate(dd):
                    dataset[name]['data'+str(kk+1)] = ddd
            obj.assign_default_metadata()
            obj.update_data_metadata()
            if verbose:
                txt = ['member ' + str(i) + ' exprot ' + ','.join(list(d))
                       for i, d in enumerate(dd)]
                print(name + ' : ' + ','.join(txt))
        try:
            props = get_all_properties(obj)
        except:
            print('Unexpected error')
            raise
        else:
            dataset[name]['property'] = props
            if verbose:
                txt = '\n'.join([k + ':' + props[k] for k in props])
                print('property')
                print(txt)
        if obj.has_metadata():
            metadata[name] = obj.getvar('metadata')
    return dataset, metadata, export_flag


def hdf_data_export(page=None,
                    filename='data.hdf',
                    verbose=False,
                    dry_run=False,
                    data=None,
                    metadata=None,
                    export_flag=None):

    if export_flag is None:
        export_flag = {}
    if metadata is None:
        metadata = OrderedDict()
    if data is None:
        if page is None:
            print('Error: Specify either page object or data')
            return
        data, metadata, export_flag = build_data(page,
                                                 verbose=verbose,
                                                 metadata=metadata,
                                                 export_flag=export_flag)
    if dry_run:
        return

    import h5py
    #from netCDF4 import Dataset
    rootgrp = h5py.File(filename, 'w')
    #rootgrp = Dataset(filename, "w", format="NETCDF4")

    import time
    meta = metadata[list(metadata)[0]]
    meta['description'] = "Figure data exported from piScope"
    meta['date'] = time.ctime(time.time())
    for key in six.iterkeys(meta):
        rootgrp.attrs[key] = str(meta[key])
    metadata[list(metadata)[0]] = {}

    for key in six.iterkeys(data):
        labels = (key, )
        if (labels in export_flag and
                not export_flag[labels]):
            continue
        key_grp = rootgrp.create_group(key)

        data_keys = [k for k in data[key] if k.startswith('data')]
        for i, k in enumerate(data_keys):
            if len(data_keys) > 1:
                data_grp = key_grp.create_group(k)
            else:
                data_grp = key_grp
            ddd = data[key][k]
            for key2 in six.iterkeys(ddd):
                labels = (key, k, key2)
                # print 'checking ', labels, ddd.keys()
                if (labels in export_flag and
                        not export_flag[labels]):
                    continue

                do_complex = False
                if ddd[key2].dtype == complex:
                    do_complex = True
                try:
                    meta = metadata[key][k][key2]  # plot, data, xdata
                except:
                    meta = {}
                if do_complex:
                    cdata_grp = data_grp.create_group(key2 + '(Complex)')
                    dataset1 = cdata_grp.create_dataset(
                        'Real', data=ddd[key2].real)
                    dataset2 = cdata_grp.create_dataset(
                        'Imag', data=ddd[key2].imag)
                    for key3 in six.iterkeys(meta):
                        cdata_grp.attrs[key3] = str(meta[key3])
                    dataset1.attrs['comment'] = 'real part'
                    dataset2.attrs['comment'] = 'imaginary part'
                    dataset1.attrs['shape'] = str(ddd[key2].real.shape)
                    dataset2.attrs['shape'] = str(ddd[key2].imag.shape)
                else:
                    dataset = data_grp.create_dataset(key2, data=ddd[key2])
                    for key3 in six.iterkeys(meta):
                        dataset.attrs[key3] = str(meta[key3])
                    dataset.attrs['shape'] = str(ddd[key2].shape)
        try:
            meta = metadata[key]
        except:
            meta = {}
        for key3 in six.iterkeys(meta):
            if not isinstance(meta[key3], dict):
                key_grp.attrs[key3] = str(meta[key3])

        props = data[key]['property']
        for key2 in six.iterkeys(props):
            labels = (key, 'property', key2)
            if (labels in export_flag and
                    not export_flag[labels]):
                continue
            key_grp.attrs[key2] = str(props[key2])

    rootgrp.close()

    return data
