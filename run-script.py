import subprocess
import sys
import os.path
import json

with open("%s/%s" % (sys.path[0], 'script-aliases.json'), 'r') as f:
    aliases = json.load(f)

def call_bash_script(scr):
    subprocess.check_call("~/Code/Scripts/%s %s" % (scr, ' '.join(sys.argv[2:])), shell=True)

#script = aliases[sys.argv[1]]
if (len(sys.argv) > 1):
    script = sys.argv[1]
    if (script in aliases):
        script = aliases[sys.argv[1]]
        call_bash_script(script)
    elif (os.path.isfile("%s/%s" % (sys.path[0], script))):
        call_bash_script(script)
    else:
        print "Unable to find script %s" % (script)
else:
    print 'No script specified'
