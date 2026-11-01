import subprocess


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)
