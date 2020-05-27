
from __future__ import print_function
import requests as r
import subprocess

hive_json = r.get('https://www.ocf.berkeley.edu/~hkn/hivemind/data/latest.json').json()
hives = [key for key in hive_json['data'].keys() if key[0:4]=='hive' and 'load_avgs' in hive_json['data'][key].keys()]
best_hive = min(hives, key=lambda h : hive_json['data'][h]['load_avgs'][1])
print('Best performance hive is: ' + best_hive + ' (' + str(hive_json['data'][best_hive]['load_avgs'][1]) + '%)')
choice=raw_input("SSH into " + best_hive + "? [y/n] ")
if (choice.startswith('y')) :
        subprocess.check_call("ssh cs61c-axc@"+best_hive+".berkeley.edu", shell=True)
