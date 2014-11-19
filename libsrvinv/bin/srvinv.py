#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright:
#   2014 brtz <github.com/brtz>
#   2014 perfide <github.com/perfide>
# License: Apache License 2.0+
#   http://www.apache.org/licenses/LICENSE-2.0

"""srvinv - a command-line-interface to the srvinv server inventory server

usage examples:
---------------
srvinv get srv srvid --attribute interfaces
  returns a srvid's interfaces formatted as json
srvinv set srv srvid --attribute is_provisioned --value "true"
  sets is_provisioned to true on a srvid
srvinv register srv srvid
  will register a new srvid in inventory
srvinv delete srv srvid
  will remove a srvid from inventory
"""

import argparse

import libsrvinv
import libsrvinv.bson_helper as json


def main(verb, resource, resourceid, attribute, value):
    i_ret = 0

    if verb == 'get':
        if value is not None:
            print('value set in get operation')
        else:
            (i_ret, x_text) = libsrvinv.get(resource, resourceid, attribute)
            if i_ret == 0:
                print(json.dumps(x_text))
            elif i_ret == 1:
                print('resource not found')
            elif i_ret == 2:
                print('attribute not set')
            elif i_ret == 3:
                print('error communicating with srvinv daemon')
            elif i_ret == 9:
                print('error unable to build srv-id')
            else:
                print('unknown error {}'.format(i_ret))

    elif verb == 'set':
        if attribute is None:
            print('missing attribute')
        elif value is None:
            print('missing value')
        else:
            i_ret = libsrvinv.set(resource, resourceid, attribute, value)
            if i_ret == 0:
                pass
            elif i_ret in (1, 2):
                print('error communicating with srvinv daemon')
            elif i_ret == 3:
                print('resource not found')
            elif i_ret == 4:
                print('attribute unchanged')
            elif i_ret == 9:
                print('error unable to build srv-id')
            else:
                print('unknown error {}'.format(i_ret))

    elif verb == 'add':
        return_code = libsrvinv.add(resource, resourceid, attribute, value)
        if return_code == -1:
            print('item exists')
        elif return_code == 1:
            print('failed to get attribute')
        elif return_code == 2:
            print('attribute is not a list')
        elif return_code == 3:
            print('failed to set attribute')
        elif return_code == 9:
            print('error unable to build srv-id')

    elif verb == 'remove':
        return_code = libsrvinv.remove(resource, resourceid, attribute, value)
        if return_code == -1:
            print('item does not exist')
        elif return_code == 1:
            print('failed to get attribute')
        elif return_code == 2:
            print('attribute is not a list')
        elif return_code == 3:
            print('failed to set attribute')
        elif return_code == 9:
            print('error unable to build srv-id')

    elif verb == 'register':
        i_ret = libsrvinv.register(resource, resourceid)
        if i_ret == 1:
            print('conflict: already registered')
        elif i_ret == 2:
            print('error communicating with srvinv daemon')
        elif i_ret == 9:
            print('error unable to build srv-id')
        elif i_ret != 0:
            print('error failed with error-code {}'.format(i_ret))

    elif verb == 'delete':
        i_ret = libsrvinv.delete(resource, resourceid)
        if i_ret == 1:
            print('resource not found')
        elif i_ret == 9:
            print('error unable to build srv-id')
        elif i_ret != 0:
            print('error communicating with srvinv daemon')

    else:
        print('error unknown verb: {}'.format(verb))

    return i_ret
# end def main

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "verb",
        type=str,
        help="verbs to be used",
        choices=['get', 'set', 'add', 'remove', 'register', 'delete'],
    )
    parser.add_argument(
        "resource",
        type=str,
        help="resources to be used",
        choices=('env', 'net', 'srv'),
    )
    parser.add_argument(
        "resourceid",
        type=str,
        help="the resource ids (comma-separated list)",
    )
    parser.add_argument(
        'attribute',
        type=str,
        help='the attribute to be accessed',
        nargs='?',
        default=None,
    )
    parser.add_argument(
        'value',
        type=str,
        help='the value to be setted in an attribute',
        nargs='?',
        default=None,
    )
    parser.add_argument(
        "--attribute",
        type=str,
        help="the attribute to be accessed (deprecated)",
    )
    parser.add_argument(
        "--value",
        type=str,
        help="the value to be setted in an attribute (deprecated)",
    )

    args = parser.parse_args()

    i_out = 0
    for resourceid in args.resourceid.split(','):
        i_ret = main(args.verb, args.resource, resourceid,
                     args.attribute, args.value)
        if i_ret:
            i_out = i_ret

    exit(i_out)


if __name__ == "__main__":
    run()

# [EOF]
