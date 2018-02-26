import codecs
import os
import re

import platform

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

def escape(path):
    return re.sub(r'\^?&', u'^&', path)

def make_whitespaced_args_string(args):
    result = u' '
    if args:
        result = u' {} '.format(' '.join(args))
    return result

def del_files_command(*args):
    return u'del /q {}'.format(' '.join(quote(p) for p in args))

def move_file_commands(src_file, dst_file):
    return [
        u'robocopy {src_folder} {dst_folder} {src_name} /Z /MOV /NS /NC /NDL /NJH /NJS'.format(
            src_folder=quote(os.path.dirname(src_file)),
            dst_folder=quote(os.path.dirname(dst_file)),
            src_name=quote(os.path.basename(src_file))),
        u'if exist {dst_file} del /q {dst_file}'.format(
            dst_file=quote(dst_file)),
        u'ren {src_file} {dst_name}'.format(
            src_file=quote(os.path.join(os.path.dirname(dst_file), os.path.basename(src_file))),
            dst_name=quote(os.path.basename(dst_file)))
    ]

def create_dir_command(dir_path):
    return u'if not exist {path} mkdir {path}'.format(path=quote(dir_path))

def write_batch(filepath, commands, allowed_exit_codes):
    with codecs.open(filepath, 'a', 'cp866') as fobj:
        for command in commands:
            fail_exit_code = 1
            for program, code in allowed_exit_codes.iteritems():
                if program in command.lower():
                    fail_exit_code = code + 1
            exit_clause = u'exit /b 1'
            if fail_exit_code > 1:
                exit_clause = u'if errorlevel {} exit /b 1'.format(fail_exit_code)
            result_string = u'{} || {}'.format(command.strip(), exit_clause)
            fobj.write(u'{}\r\n'.format(result_string))
        fobj.write(u'\r\n')
