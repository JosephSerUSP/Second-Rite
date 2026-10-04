"""Run a Blender Python tool with Python network connections denied in this process.

Usage: blender --factory-startup --disable-autoexec -P offline_blender.py -- TOOL -- ARGS
This does not alter machine networking. A real disconnected-machine check remains owner evidence.
"""
import runpy
import socket
import sys
from pathlib import Path


def deny(*args, **kwargs):
    raise RuntimeError("Network connection denied by offline Blender check")


socket.create_connection=deny
socket.socket.connect=deny
socket.socket.connect_ex=deny
arguments=sys.argv[sys.argv.index("--")+1:]
tool=Path(arguments[0]).resolve()
sys.path.insert(0,str(tool.parent))
sys.argv=[str(tool),*arguments[1:]]
runpy.run_path(str(tool),run_name="__main__")
