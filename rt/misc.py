from __future__ import print_function

import subprocess
import sys

def run(logger, cmd, ignoreErrors=False, **kwargs):
    process = subprocess.Popen(cmd, **kwargs)
    logger.info(cmd)
    stdout, stderr = process.communicate()
    if not ignoreErrors and process.returncode != 0:
        logger.error(stderr)
        raise Exception('External command error')
    return stdout, stderr

def is_windows():
    return sys.platform == 'win32'

def safe_print(s, *args, **kwargs):
    if isinstance(s, basestring):
        if not isinstance(s, unicode):
            raise Exception('Non-unicode string encountered')
        if is_windows():
            s = s.encode(sys.stdout.encoding, errors='ignore')
    print(s, *args, **kwargs)
