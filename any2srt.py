import os
import re
import shutil
import subprocess
import sys

class ConvertError(Exception):
    pass

def search_line(regexp, lines, error_message):
    for line in lines:
        match = re.search(regexp, line)
        if match:
            return match.groupdict()
    raise ConvertError(error_message)

if __name__ == '__main__':
    src_path = sys.argv[1]
    dst_path = sys.argv[2]
    command = ['SubtitleEdit', '/convert', src_path, 'srt', '/fixcommonerrors']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    output, _ = process.communicate()
    cleaned_output = [line for line in output.splitlines() if line]

    try:
        num_files = int(search_line(
            r'(?P<num>\d+) file\(s\) converted',
            cleaned_output,
            'Unable to find statistics')['num'])
        if num_files != 1:
            raise ConvertError('Conversion failed!')

        tmp_path = search_line(
            r'{} -> (?P<path>.+?)\.\.\.'.format(os.path.basename(src_path)),
            cleaned_output,
            'Unable to find file name')['path']
        if not os.path.isfile(tmp_path):
            raise ConvertError('Temporary file not found')
        shutil.move(tmp_path, dst_path)
    except ConvertError as e:
        print(e.message)
        print(u'\n'.join(cleaned_output))
        sys.exit(1)

    sys.exit(0)
