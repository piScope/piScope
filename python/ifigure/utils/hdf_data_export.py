'''

   Export (partial) Figure Data to HDF file



'''
import traceback
import six
from collections import OrderedDict

from ifigure.widgets.artist_widgets import listparam, call_getter 

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
        
def build_data(page, verbose=True):
    book = page.get_figbook()    
    dataset = OrderedDict()
    for obj in page.walk_tree():
        if obj is page:
            name = page.name
        else:
            name = page.name + '.' + '.'.join(page.get_td_path(obj)[1:])
        dataset[name] = {}
        try:
            dd = obj.export()
        except NotImplementedError:
            if verbose:            
                print(name + ' does not have data to export')
        except:
            print('Unexpected error')
            raise
        else:
            for kk,  ddd in enumerate(dd):
               dataset[name]['data'+str(kk+1)] = ddd
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
                
    return dataset
    
def hdf_data_export(page = None,
                    filename = 'data.hdf',
                    verbose = True,
                    dry_run = False,
                    data = None,
                    export_flag = None):
    if data is None:
        if page is None:
            print('Error: Specify either page object or data')
            return
        data = build_data(page, verbose = verbose)
    if dry_run: return
    if export_flag is None: export_flag = {}
    
    from netCDF4 import Dataset
    rootgrp = Dataset(filename, "w", format="NETCDF4")
    
    import time
    
    rootgrp.description = "Figure data exported from piScope"
    rootgrp.history = "Created " + time.ctime(time.time())    

    for key in six.iterkeys(data):
        key_grp = rootgrp.createGroup(key)
        
        props = data[key]['property']
        for key2 in six.iterkeys(props):
            labels = (key, 'property', key2)
            #print 'checking ', labels            
            if (labels in export_flag and
                not export_flag[labels]): continue
            setattr(key_grp, key2, props[key2])

            
        data_keys = [k for k in  data[key].keys() if k.startswith('data')]
        for i, k in enumerate(data_keys):
            ddd = data[key][k]
            for key2 in six.iterkeys(ddd):
                labels = (key, k, key2)
                #print 'checking ', labels
                if (labels in export_flag and
                     not export_flag[labels]): continue
                
                dimnames = []
                dataname = '_'.join(('data', str(i), key2))
                for j, s in enumerate(ddd[key2].shape):
                   dimname = dataname + '_s_' + str(j+1)
                   dim= key_grp.createDimension(dimname, s)
                   dimnames.append(dimname)

                do_complex = False
                if ddd[key2].dtype == float:
                    stype = 'f8'
                elif ddd[key2].dtype == int:
                    stype = 'i8'               
                elif ddd[key2].dtype == complex:                        
                    stype = 'f8'
                    do_complex = True
                else:
                    continue
                if do_complex:
                    var = key_grp.createVariable('Re_'+key2 ,stype,
                                                 tuple(dimnames))
                    var[:] = ddd[key2].real                        
                    var = key_grp.createVariable('Im_'+key2 ,stype,
                                                 tuple(dimnames))
                    var[:] = ddd[key2].imag                        
                else:
                    var = key_grp.createVariable(key2 ,stype, tuple(dimnames))
                    var[:] = ddd[key2]
                        
                    
    rootgrp.close()        

    return data
    
