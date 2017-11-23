import subprocess

def run(logger, cmd, ignoreErrors=False, **kwargs):
    process = subprocess.Popen(cmd, **kwargs)
    logger.info(cmd)
    stdout, stderr = process.communicate()
    if not ignoreErrors and process.returncode != 0:
        logger.error(stderr)
        raise Exception('External command error')
    return stdout, stderr
