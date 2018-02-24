import os
import platform
import sys

class Error(Exception):
    pass

def argparse_path(bytestring):
    return os.path.abspath(os.path.expandvars(bytestring.decode(sys.getfilesystemencoding())))

def run(main):
    error = None
    return_code = 0
    try:
        return_code = main()
    except Error as e:
        error = e.message
    except KeyboardInterrupt:
        error = u'Interrupted by user'
    if error is not None:
        platform.print_string(error)
        return_code = 1
    sys.exit(return_code)
