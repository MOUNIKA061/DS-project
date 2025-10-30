import subprocess
import sys
import time
import requests
import os

from importlib import import_module

BASE = 'http://127.0.0.1:5000'


def wait_for_server(timeout=15, interval=0.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(BASE, timeout=1)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def start_server():
    # Start the Flask app as a subprocess using the same Python executable
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), '..', 'app.py')]
    # normalize path
    cmd = [sys.executable, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc


def tail_output(proc):
    # non-blocking read of available output lines
    try:
        while proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                print('[server]', line.rstrip())
            else:
                break
    except Exception:
        pass


def run():
    print('Starting server...')
    proc = start_server()
    try:
        ok = wait_for_server(timeout=20)
        if not ok:
            tail_output(proc)
            raise RuntimeError('Server did not start in time')
        print('Server is up — running e2e test')
        # import and run the test
        mod = import_module('GeoVerse.tests.e2e_test')
        try:
            mod.run_e2e()
            print('\nE2E runner: SUCCESS')
        except Exception as e:
            print('\nE2E runner: FAILED -', e)
            raise
    finally:
        print('Stopping server...')
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception as e:
            print('Error stopping server:', e)
        tail_output(proc)


if __name__ == '__main__':
    run()
