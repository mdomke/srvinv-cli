# -*- coding: UTF-8 -*-

# Copyright:
#   2014 perfide <github.com/perfide>
# License: CC0 (public domain)
#   http://creativecommons.org/publicdomain/zero/1.0/

"""json-like functions for bson objects of pymongo

bson.json_util offers dumps and loads since pymongo 2.3
This module also offers dump and load.
And it makes dumps and loads available on pymongo <= 2.2 (Debian/wheezy)

Usage:
The four functions accept the same parameters
as its pendants from the json module.

https://api.mongodb.org/python/current/api/bson/json_util.html
https://docs.python.org/3/library/json.html
"""

import json
from bson import json_util

dump = lambda fp: json.dump(fp, default=json_util.default)
load = lambda fp: json.load(fp, object_hook=json_util.object_hook)

try:
    # pymongo >= 2.3
    from bson.json_util import dumps, loads
except ImportError:
    # pymongo <= 2.2
    dumps = lambda py_object: json.dumps(
        py_object, default=json_util.default)
    loads = lambda json_string: json.loads(
        json_string, object_hook=json_util.object_hook)

# [EOF]
