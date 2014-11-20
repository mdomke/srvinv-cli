import sys
import os
from ConfigParser import ConfigParser


config = ConfigParser()
config.read([
    os.path.join(sys.prefix, "etc/collins/srvinv.cfg"),
    "/etc/collins/srvinv.cfg",
    "/opt/collins/srvinv.cfg",
    os.path.expanduser("~/.config/srvinv.cfg"),
    "srvinv.cfg"])
