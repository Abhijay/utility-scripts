import subprocess
import sys
import os.path
import glob

index = int(sys.argv[1]) -1 if (len(sys.argv) > 1) else 0;

curr_directory = os.getcwd()
school_dir_index = curr_directory.split('/').index('School');
if school_dir_index > -1:
    class_pdfs = glob.glob('/'.join(os.getcwd().split('/')[:school_dir_index+4])+'/*.pdf')
    if (class_pdfs):
        print('Opening %s' % class_pdfs[index])
        subprocess.check_call("open \"%s\"" % class_pdfs[index], shell=True)
    else:
        print('No textbook found')
        exit()

else:
    print('Not in a valid school directory.')
    exit()
