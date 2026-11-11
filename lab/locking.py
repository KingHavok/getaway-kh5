"""Serialize mutable emulator/catalogue work within one private project."""
import fcntl
from pathlib import Path

def acquire(project):
 handle=(Path(project['workspace'])/'.emulator-lease').open('a+')
 try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  print('Waiting for another operation in this private lab; use separate workspaces for parallel workers',flush=True)
  fcntl.flock(handle,fcntl.LOCK_EX)
 return handle
