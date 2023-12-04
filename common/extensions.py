###########################################################
# Extensions module
# Import and initialize extension modules
# Plugins and encoders
# Fill in TML tag dictionary
###########################################################
from common.bbsdebug import _LOG
from common.classes import Encoder 
import importlib
import pkgutil
import os

import encoders
import plugins

t_mono ={}

#######################################
# Register TML tags for common modules
#######################################
def RegisterTMLtags():
    global t_mono
    for module in os.listdir(os.path.dirname(__file__)):
        if module in ['__init__.py','parser.py','extensions.py','petscii.py'] or module[-3:] != '.py':
            continue
        m = importlib.import_module('common.'+module[:-3])
        if 't_mono' in dir(m):
            t_mono.update(m.t_mono)
            _LOG(f'TML tags added for: {module[:-3].upper()}',v=4)
        del(m)

#######################
# Register plugins
#######################
def RegisterPlugins():
    global t_mono
    Plugins = {}
    p_mods = [importlib.import_module(name) for finder, name, ispkg in pkgutil.iter_modules(plugins.__path__, plugins.__name__ + ".")]
    for a in p_mods:
        if 'setup' in dir(a):
            fname,parms = a.setup()
            if 'plugPrefs' in dir(a):
                _LOG('Plugin: '+fname+' has preferences', v=4)
                prefs = a.plugPrefs
            else:
                prefs = None
            Plugins[fname] = (a.plugFunction,parms,prefs) 
            _LOG('Loaded plugin: '+fname,v=4)
            t_mono[fname] = (a.plugFunction,[('c','_C')]+parms)
    return Plugins

########################
# Register encoders
########################
def RegisterEncoders():
    Encoders = {}
    e_mods = [importlib.import_module(name) for finder, name, ispkg in pkgutil.iter_modules(encoders.__path__, encoders.__name__ + ".")]
    for a in e_mods:
        if '_Register' in dir(a):
            encs = a._Register()
            for e in encs:
                Encoders[e.name] = e
                _LOG('Loaded encoder: '+e.name,v=4)
    return Encoders
