import psutil
import time
import sys
import os
import signal

from pathlib import Path

curr_dir = Path(__file__).parent.absolute()
code_path = curr_dir / 'code' / 'target_code.py'

replacement_code = curr_dir / 'code_a.py'

# ! If not terminated, the child process will still run even if this runner is closed!
def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                   timeout=None, on_terminate=None):
    """Kill a process tree (including grandchildren) with signal
    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callabck function which is
    called as soon as a child terminates.
    """
    assert pid != os.getpid(), "won't kill myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        p.send_signal(sig)
    gone, alive = psutil.wait_procs(children, timeout=timeout,
                                    callback=on_terminate)
    return (gone, alive)

def replace_code():
    if code_path.exists():
        code_path.unlink()

    print('New Replaced Path : ')
    print(str(replacement_code.replace(code_path)))

def run_code():
    proc = psutil.Popen([sys.executable, str(code_path)])
    time.sleep(10)  # Let the code run for a while
    kill_proc_tree(proc.pid)


print('Initially running Code A...')
time.sleep(1)

# Run the code
run_code()

# Stop and replace the code
replace_code()

# Run the code after replacement
print('Now running Code Z...')
time.sleep(1)
run_code()
