import codecs
import os
import sys

import platform

def argparse_path(bytestring):
    return os.path.abspath(os.path.expandvars(bytestring.decode(sys.getfilesystemencoding())))

def quote(path):
    if path == '-':
        return path

    q = u''
    if ' ' in path:
        q = u"'"
        if platform.is_windows() or "'" in path:
            assert '"' not in path
            q = u'"'
    return q + path + q

def make_whitespaced_args_string(args):
    result = u' '
    if args:
        result = u' {} '.format(' '.join(args))
    return result

def del_files_command(*args):
    return u'del /q {}'.format(' '.join(quote(p) for p in args))

def copy_file_command(src, dst):
    return u'copy /z {} {}'.format(quote(src), quote(dst))

def write_batch(filepath, commands):
    with codecs.open(filepath, 'a', 'cp866') as fobj:
        for command in commands:
            result_string = u'{} || exit /b 1'.format(command.strip())
            fobj.write(u'{}\r\n'.format(result_string))
        fobj.write(u'\r\n')