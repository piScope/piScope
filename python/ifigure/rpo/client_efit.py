from __future__ import print_function
#
#  example program to connect proxy_efit
#
import sys
import Pyro4
import Pyro4.util

sys.excepthook = Pyro4.util.excepthook

nshost = 'cmodws30.psfc.mit.edu'
nameserver = Pyro4.locateNS(host=nshost)
uri = nameserver.lookup("proxy_efit")
proxy = Pyro4.Proxy(uri)
print(proxy.run_minus_5(shot='1120710012', time='1000'))
