from __future__ import print_function

import codecs
import datetime
import os
import subprocess
import sys
import traceback

LOG_CATEGORY_INFO = u'INFO'
LOG_CATEGORY_ERROR = u'ERROR'
LOG_CATEGORY_WARNING = u'WARNING'

def logEntry(category, message, header=False):
    if header:
        decorator = u'=' * 10
        message = u'{} {} {}'.format(decorator, message, decorator)
    output = u'[{}] [{}] {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), category, message)
    try:
        with codecs.open(os.path.join(os.path.dirname(__file__), 'daemon.log'), 'a', 'utf-8') as fobj:
            fobj.write(output)
    except UnicodeEncodeError:
        print(traceback.format_exc(), file=sys.stderr)
    sys.stderr.flush()

def jobs(root):
    for filename in os.listdir(root):
        filepath = os.path.join(root, filename)
        if os.path.isfile(filepath) and filename.endswith('.job'):
            with codecs.open(filepath, 'r', 'utf-8') as fobj:
                for line in (l.strip() for l in fobj):
                    data = line.split()
                    tune = data[0]
                    path = ' '.join(data[1:])
                    yield (path, tune)

def vbr(filepath):
    cmd = 'ffprobe -select_streams v -show_entries packet=size:stream=duration -of compact=p=0:nk=1 "{}"'.format(filepath)
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    print(stdout)
    exit()

def encode(src, dst, tune, maxrate):
    bufsize = maxrate
    # TODO RUN
    # cmd = 'ffmpeg -y -i "{src}" -threads 4 -an -sn -c:v libx264 -preset veryslow -tune {tune} -profile:v high -level:v 4.1 -crf 18 "{dst}"'

def main():
    while True:
        for srcpath, tune in jobs(os.path.dirname(__file__)):
            dstpath = os.path.join(os.path.dirname(srcpath), u'{}_enc.mkv'.format(os.path.splitext(os.path.basename(srcpath))[0]))
            vbr(srcpath)
            exit()

    # # os.path.dirname(__file__)
    # while True:
    #     for job in os.listdir(cwd):
    #         if os.path.splitext(job)[1] == '.job':
    #             with codecs.open(job, 'r', 'utf-8') as jobfile:
    #                 for line in jobfile:
    #                     line = line.strip()
    #                     tune = line.split()[0]
    #                     filename = ' '.join(line.split()[1:])
    #                     if os.path.isfile(filename):
    #                         srcname = os.path.abspath(filename)
    #                         dstname = os.path.join(os.path.dirname(srcname), u'{}_enc.mkv'.format(os.path.splitext(filename)[0]))
    #                         log(u'START {}'.format(srcname))
    #                         process = subprocess.Popen(cmd.format(src=srcname, dst=dstname, tune=tune), shell=True)
    #                         process.communicate()
    #                         log(u'READY {}'.format(srcname))
    #                 os.remove(job)

if __name__ == '__main__':
    main()
