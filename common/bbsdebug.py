##### Debug logging #####

import sys
import datetime

#ANSI CODES
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


#Print Log message to console
def _LOG(*message, _end='\n', date=True, id=0):
	if id != 0:
		idt = '['+str(id)+']'
	else:
		idt = '[*]'
	if date == True:
		t = datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds')
	else:
		t = ''
	print(idt, t, *message, file=sys.stderr, end=_end)
