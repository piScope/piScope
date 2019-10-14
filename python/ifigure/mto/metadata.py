from collections import OrderedDict
import six

# this is assigned to figplot
default_metadata_keys = ('name',
                         'long_description')

# this is assigned to figpage
default_metadata_file_keys = ('name',
                              'long_description',
                              'source',
                              'date',
                              'user_name',
                              'user_id',
                              'comment',
                              'keywords')

# this is assigned to figplot under data dictionary key.
default_metadata_data_keys = ('name',
                              'long_description',
                              'unit',
                              'range')
# In addition to this shape and type will be written
# automatically.


class MetadataHolder(object):
    def set_default_metadata(self):
        return self.setvar('metadata', OrderedDict())

    def has_metadata(self):
        return self.getvar('metadata') is not None

    def fill_default_metadatavalue(self):
        pass

    def get_metadata(self):
        return self.getvar('metadata')

    def set_metadata(self, *args):
        '''
        set_metadata({'xdata':'{'name':'',..
                      'ydata':'{'name':''...})
        set_metadata('x_axis', 'xlabel')
        '''
        if len(args) == 1:
            self.setvar('metadata', args[0])
        elif len(args) == 2:
            if self.getvar('metadata') is None:
                self.set_default_metadata()
            self.getvar('metadata')[args[0]] = args[1]

    def update_data_metadata(self, updatename=False):
        # autofill name,  range
        # if data is not give, try to get it
        metadata = self.getvar('metadata')
        for k in six.iterkeys(metadata):
            if k.startswith('data'):
                dd = metadata[k]
                for name in six.iterkeys(dd):
                    axisname = name[0]  # x, y, z, c
                    m = 'get_'+axisname+'axisparam'
                    if hasattr(self, m):
                        m = getattr(self, m)
                        param = m()
                        if updatename:
                            dd[name]['name'] = param.labelinfo[0]
                        dd[name]['range'] = str(param.range)

    def update_file_metadata(self):
        from ifigure.mto.fig_page import FigPage
        if not isinstance(self, FigPage):
            return
        from ifigure.utils.get_username import get_username
        self.getvar('metadata')['user_id'] = get_username()

    def assign_default_file_metadata(self, data=None):
        from ifigure.mto.fig_page import FigPage
        if not isinstance(self, FigPage):
            return
        if self.has_metadata():
            metadata = self.getvar('metadata')
        else:
            metadata = OrderedDict()
        for k in default_metadata_file_keys:
            if not k in metadata:
                metadata[k] = ''
        self.setvar('metadata', metadata)
        self.update_file_metadata()

    def assign_default_metadata(self, data=None):
        '''
        will be overwritten by subclass
        '''
        def fill_dataset(dd, d):
            for key in six.iterkeys(d):
                if not key in dd:
                    dd[key] = OrderedDict()
                for kk in default_metadata_data_keys:
                    if not kk in dd[key]:
                        dd[key][kk] = ''
        if self.has_metadata():
            metadata = self.getvar('metadata')
        else:
            metadata = OrderedDict()
        self.setvar('metadata', metadata)
        for key in default_metadata_keys:
            if not key in metadata:
                metadata[key] = ''
        if data is None:
            try:
                data = self.export()
            except:
                pass
        if data is not None:
            if len(data) == 1:
                if not 'data' in metadata:
                    metadata['data'] = {}
                fill_dataset(metadata['data'], data[0])
            else:
                for kk,  ddd in enumerate(data):
                    if not 'data'+str(kk+1) in metadata:
                        metadata['data'+str(kk+1)] = {}
                    fill_dataset(metadata['data'+str(kk+1)],
                                 ddd)
            self.update_data_metadata(updatename=True)
