import subprocess
import sys
import os.path
import json
import shutil

with open("%s/%s" % (sys.path[0], 'script-aliases.json'), 'r') as f:
    aliases = json.load(f)

def script_path(scr):
    if os.path.isabs(scr):
        return scr
    return os.path.abspath("%s/%s" % (sys.path[0], scr))

def call_script(scr):
    try:
        if scr.endswith('.py'):
            call_python_script(scr)
        elif scr.endswith('.ts') or scr.endswith('.tsx'):
            call_typescript_script(scr)
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
    subprocess.check_call([script_path(scr)] + sys.argv[2:])

def call_python_script(scr):
    subprocess.check_call([sys.executable, script_path(scr)] + sys.argv[2:])

def call_typescript_script(scr):
    full_path = script_path(scr)

    tsx = shutil.which("tsx")
    if tsx:
        subprocess.check_call([tsx, full_path] + sys.argv[2:])
        return

    pnpm = shutil.which("pnpm")
    if pnpm:
        subprocess.check_call([pnpm, "dlx", "tsx", full_path] + sys.argv[2:])
        return

    npx = shutil.which("npx")
    if npx:
        subprocess.check_call([npx, "--yes", "tsx", full_path] + sys.argv[2:])
        return

    raise SystemExit("TypeScript runner not found. Install `tsx` (recommended) or `pnpm`/`npx`.")

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
    elif (os.path.isfile("%s/%s.ts" % (sys.path[0], script))):
        call_script(script + '.ts')
    elif (os.path.isfile("%s/%s.tsx" % (sys.path[0], script))):
        call_script(script + '.tsx')
    else:
        print("Unable to find script %s" % (script))
else:
    print('No script specified')
