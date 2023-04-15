###########################################################
# Extensions module
# Import and initialize extension modules
# Plugins and encoders
# Fill in TML tag dictionary
###########################################################
from common.bbsdebug import _LOG 
import importlib
import pkgutil
#from common.connection import Connection
import os

class Encoder:
    def __init__(self, name:str) -> None:
        self.name = name
        self.tml_mono = {}
        self.tml_multi = {}
        self.encode = None
        self.decode = None
        pass


import encoders
import plugins

t_mono ={}

# Register TPL tags for common modules
def RegisterTPLtags():
    for module in os.listdir(os.path.dirname(__file__)):
        if module in ['__init__.py','parser.py','extensions.py','petscii.py'] or module[-3:] != '.py':
            continue
        m = importlib.import_module('common.'+module[:-3])
        if 't_mono' in dir(m):
            t_mono.update(m.t_mono)
            _LOG(f'TML tags added for: {module[:-3].upper()}',v=4)
        del(m)

# Import plugins
def RegisterPlugins():
    Plugins = {}
    p_mods = [importlib.import_module(name) for finder, name, ispkg in pkgutil.iter_modules(plugins.__path__, plugins.__name__ + ".")]
    for a in p_mods:
        if 'setup' in dir(a):
            fname,parms = a.setup()
            Plugins[fname] = (a.plugFunction,parms) 
            _LOG('Loaded plugin: '+fname,v=4)
            t_mono['fname'] = (a.plugFunction,[('c','_C')]+parms)
    return Plugins

# Import encoders
def RegisterEncoders():
    Encoders = {}
    e_mods = [importlib.import_module(name) for finder, name, ispkg in pkgutil.iter_modules(encoders.__path__, encoders.__name__ + ".")]
    for a in e_mods:
        if '_Register' in dir(a):
            encs = a._Register()
            for e in encs:
                Encoders[e['name']] = Encoder(e['name'])
                Encoders[e['name']].encode = e['encode']
                Encoders[e['name']].decode = e['decode']
                Encoders[e['name']].tml_mono = e['tml_mono']
                Encoders[e['name']].tml_multi = e['tml_multi']
                _LOG('Loaded encoder: '+e['name'],v=4)
    return Encoders
