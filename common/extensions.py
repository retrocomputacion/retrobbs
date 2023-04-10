###########################################################
# Extensions module
# Import and initialize extension modules
# Plugins and encoders
###########################################################
from common.bbsdebug import _LOG 
import importlib
import pkgutil
from common.connection import Connection

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
