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

def get_all_properties(obj, use_str = True):
    ret =  obj.property_for_shell()
    tags = None
    if isinstance(ret, tuple):
       tab = ret[0]
       props = ret[1]
       if len(ret) == 3:
           tags = ret[2]
    else:
       tab = ['']
       props = [ret]
    if tags is None: tags =['']*len(props)

    ll = []
    for tag, plist in zip(tags, props):
        for p in plist:
            if tag == '':
                ll.append(('',  listparam[p][6], listparam[p]))
            else:
                ll.append((tag, listparam[p][6], listparam[p]))

    props =  {}            
    for lll in ll:                
        tag, name, lp = lll
        ret = [call_getter(a, lp, tab = tag) for a in obj._artists]
        if use_str: ret = ret.__repr__()
        if tag == '': 
           props[name] = ret
        else:
           props['_'.join((tag, name))] = ret
    return props
        
def build_data(page, export_flag = None,
               metadata = None,  verbose=True):
    if export_flag is None: export_flag = {}
    if metadata is None: metadata = {}
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
                txt = ['member '+ str(i) + ' exprot ' + ','.join(d.keys()) for i, d in enumerate(dd)]
                print(name + ' : ' + ','.join(txt))
        try:
            props = get_all_properties(obj, use_str = True)
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
    
def hdf_data_export(page = None,
                    filename = 'data.hdf',
                    verbose = False,
                    dry_run = False,
                    data = None,
                    metadata = None,
                    export_flag = None):

    if export_flag is None: export_flag = {}
    if metadata is None: metadata = OrderedDict()
    if data is None:
        if page is None:
            print('Error: Specify either page object or data')
            return
        data, metadata, export_flag =  build_data(page, 
                                    verbose = verbose,
                                    metadata = metadata, 
                                    export_flag = export_flag)
    if dry_run: return

    import h5py
    #from netCDF4 import Dataset
    rootgrp = h5py.File(filename,'w')    
    #rootgrp = Dataset(filename, "w", format="NETCDF4")
    
    import time
    meta = metadata[metadata.keys()[0]]
    print meta
    meta['description'] = "Figure data exported from piScope"
    meta['date']= time.ctime(time.time())
    for key in six.iterkeys(meta):
        rootgrp.attrs[key] = str(meta[key])
    metadata[metadata.keys()[0]] = {}

    for key in six.iterkeys(data):
        labels = (key, )
        if (labels in export_flag and
            not export_flag[labels]): continue
        key_grp = rootgrp.create_group(key)
        
        data_keys = [k for k in  data[key].keys() if k.startswith('data')]
        for i, k in enumerate(data_keys):
            if len(data_keys) > 1:
                data_grp = key_grp.create_group(k)
            else:
                data_grp = key_grp
            ddd = data[key][k]
            for key2 in six.iterkeys(ddd):
                labels = (key, k, key2)
                #print 'checking ', labels
                if (labels in export_flag and
                     not export_flag[labels]): continue

                do_complex = False
                if ddd[key2].dtype == complex:                        
                    do_complex = True
                try:
                     meta = metadata[key][k][key2]  # plot, data, xdata
                except:
                     meta = {}
                if do_complex:
                    cdata_grp = data_grp.create_group(key2 + '(Complex)')
                    dataset1 = cdata_grp.create_dataset('Real', data=ddd[key].real)
                    dataset2 = cdata_grp.create_dataset('Imag', data=ddd[key].imag)
                    for key3 in six.iterkeys(meta):
                        cdata_grp.attrs[key3] =  str(meta[key3])
                    dataset1.attrs['comment'] = 'real part'
                    dataset2.attrs['comment'] = 'imaginary part'
                    dataset1.attrs['shape']   = str(ddd[key].real.shape)
                    dataset2.attrs['shape']   = str(ddd[key].imag.shape)
                else:
                    dataset = data_grp.create_dataset(key2,data=ddd[key2])
                    for key3 in six.iterkeys(meta):
                        dataset.attrs[key3] =  str(meta[key3])
                    dataset.attrs['shape']  =  str(ddd[key2].shape)                        
        try:
            meta = metadata[key]
        except:
            meta = {}
        for key3 in six.iterkeys(meta):
            if not isinstance(meta[key3], dict):
                key_grp.attrs[key3] =  str(meta[key3])
                    
        props = data[key]['property']
        for key2 in six.iterkeys(props):
            labels = (key, 'property', key2)
            if (labels in export_flag and
                not export_flag[labels]): continue
            key_grp.attrs[key2] = str(props[key2])

            
                    
    rootgrp.close()        

    return data
    
