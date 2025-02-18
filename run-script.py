import subprocess
import sys
import os.path
import json

with open("%s/%s" % (sys.path[0], 'script-aliases.json'), 'r') as f:
    aliases = json.load(f)

def call_script(scr):
    try:
        if scr.endswith('.py'):
            call_python_script(scr)
        else:
            call_bash_script(scr)
    except subprocess.CalledProcessError as e:
        # This is the specific exception raised by check_call() on failure
        print("Error running script '%s': %s" % (scr, e))
        # Optionally exit with the same return code
        sys.exit(e.returncode)
    except Exception as e:
        # This catches any other error
        print("Unexpected error while running script '%s': %s" % (scr, e))
        sys.exit(1)


def call_bash_script(scr):
    subprocess.check_call("~/Code/Scripts/%s %s" % (scr, ' '.join(sys.argv[2:])), shell=True)

def call_python_script(scr):
    subprocess.check_call("python ~/Code/Scripts/%s %s" % (scr, ' '.join(sys.argv[2:])), shell=True)

#script = aliases[sys.argv[1]]
if (len(sys.argv) > 1):
    script = sys.argv[1]
    if (script in aliases):
        script = aliases[sys.argv[1]]
        call_script(script)
    elif (os.path.isfile("%s/%s" % (sys.path[0], script))):
        call_script(script)
    elif (os.path.isfile("%s/%s.py" % (sys.path[0], script))):
        call_script(script + '.py')
    else:
        print("Unable to find script %s" % (script))
else:
    print('No script specified')
