'''
libsrvinv - the main library serving default methods for srvinv clients
'''

from . import config
from . import helpers
from netaddr import IPNetwork, IPAddress
import netifaces
import requests
import json
import os
import fnmatch
import time
from datetime import datetime

api_url = config.master_url + config.api_version + '/'

session = requests.Session()


class SrvinvCache:
    def __init__(self, b_cache_use_file=None):
        self.d_cache = {}
        self.df_times = {}
        self.b_cache_use_file = b_cache_use_file if \
            b_cache_use_file is not None else config.cache_use_file
        self.s_cache_path_tmpl = config.cache_path_tmpl
        self.i_cache_duration_in_s = config.cache_duration_in_s
        return
    # end def __init__

    def get(self, s_resource, b_force_update=False, b_cache_use_file=None):
        """retrive a given resource from srvinv and cache it in a dictionary or file
        s_resource: srv, net or env
        b_force_update: retrive even if cache duration is not reached
        b_cache_use_file: select if caching to file or to py-dict"""
        if b_cache_use_file is None:
            b_cache_use_file = self.b_cache_use_file
        if b_cache_use_file:
            return self._file_get(s_resource, b_force_update)
        else:
            return self._dict_get(s_resource, b_force_update)
    # end def get

    def _file_get(self, s_resource, b_force_update=False):
        """retrive resource from srvinv and cache it to file"""
        s_cache_file_path = self.s_cache_path_tmpl.format(s_resource)
        if b_force_update or not os.path.isfile(s_cache_file_path):
            b_do_update = True
        else:
            f_cache_time = os.path.getmtime(s_cache_file_path)
            b_do_update = (time.time() > (
                f_cache_time + self.i_cache_duration_in_s))
        if b_do_update:
            x_reply = self.fetch(s_resource)
            with open(s_cache_file_path, 'w') as fp:
                json.dump(x_reply, fp)
                os.chmod(s_cache_file_path, 0o766)
                return x_reply
        else:
            with open(s_cache_file_path) as fp:
                return json.load(fp)
        return None
    # end def _file_get

    def _dict_get(self, s_resource, b_force_update=False):
        """retrive resource from srvinv and cache it to py-dict"""
        f_cur_utime = time.time()
        if (b_force_update or (s_resource not in self.df_times)):
            b_do_update = True
        else:
            s_cache_file_path = self.s_cache_path_tmpl.format(s_resource)
            f_cache_time = self.df_times[s_resource]
            b_do_update = (f_cur_utime > f_cache_time)
        if b_do_update:
            self.df_times[s_resource] = (
                f_cur_utime + self.i_cache_duration_in_s)
            x_reply = self.fetch(s_resource)
            self.d_cache[s_resource] = x_reply
            return x_reply
        else:
            return self.d_cache[s_resource]
        return None
# end def _dict_get

    def fetch(self, s_resource):
        """only return data if srvinv sends status-code 200 on 'get'"""
        (i_status_code, x_reply) = _request_srvinv('get', s_resource)
        if i_status_code == 200:
            return x_reply
        else:
            return None
    # end def fetch
# end class Db

go_srvinv_cache = SrvinvCache()


def get_iface_to_addr():
    interfaces = netifaces.interfaces()
    interfaces_to_inv = {}
    for interface in interfaces:
        addrs = netifaces.ifaddresses(interface)
        interfaces_to_inv[interface] = addrs
    return interfaces_to_inv


def get_priv_info(d_iface_to_addr=None):
    s_net_id = None
    s_priv_ip = None
    s_priv_interface = None
    if d_iface_to_addr is None:
        d_iface_to_addr = get_iface_to_addr()
    networks = search('net', 'name', '*')
    for s_iface, d_addr in d_iface_to_addr.items():
        if s_iface.startswith('lo'):
            continue
        if netifaces.AF_INET not in d_addr:
            continue
        ips = d_addr[netifaces.AF_INET]
        for ip in ips:
            o_ip = IPAddress(str(ip['addr']))
            if not o_ip.is_private():
                continue
            if ip['addr'] == '127.0.0.1':
                continue
            for net in networks:
                if (('netmask' in net) and
                        (o_ip in IPNetwork(net['netmask']))):
                    s_priv_ip = str(ip['addr'])
                    s_priv_interface = s_iface
                    s_net_id = net['name']
                    break
    return (s_priv_ip, s_priv_interface, s_net_id)


def get_own_srvid(s_priv_ip=None):
    if not s_priv_ip:
        s_priv_ip = get_priv_info()[0]
    if not s_priv_ip:
        return None
    s_srvid = 'srv{:03d}{:03d}'.format(
        *[int(x) for x in s_priv_ip.split('.')[2:]])
    return s_srvid


def _request_srvinv(rtype, resource, resourceid=None,
                    attribute=None, data=None):
    """builds a url and sends a requests to srvinv
    returns a tuple of http-status-code and json-parsed
    on connection error the code is set to -1"""
    if not resource.endswith('s'):
        resource += 's'
    s_url = api_url + resource
    if resourceid:
        s_url += '/' + resourceid
    if attribute:
        s_url += '/' + attribute
    try:
        apirequest = session.request(rtype, s_url, data=data)
        i_status_code = apirequest.status_code
        if apirequest.text:
            x_reply = json.loads(apirequest.text)
        else:
            x_reply = None
    except requests.exceptions.ConnectionError:
        i_status_code = -1
        x_reply = None
    except ValueError:
        # from json.loads
        i_status_code = -2
        x_reply = None
    return (i_status_code, x_reply)
# end def _request_srvinv


def get(resource, resourceid=None, attribute=None):
    """returns a tuple of return-code and text
    on success 0 and the requested value
    1 if the resource does not exist
    2 if the attribute does not exist
    3 on error"""
    if resource == 'srv' and resourceid == 'self':
        resourceid = get_own_srvid()
    (i_status_code, x_reply) = _request_srvinv('get', resource, resourceid)
    if i_status_code == 200:
        if not attribute:
            return (0, x_reply)
        else:
            if attribute not in x_reply:
                return (2, None)
            return (0, x_reply[attribute])
    elif i_status_code == 404:
        return (1, None)
    # i.e. code 500
    return (3, None)
# end def get


def set(resource, resourceid, attribute, value):
    """sets a attribut of a existing object
    return 0 on succes, 1/2 if first/second connections fails
    and 3 is the object does not exist"""
    i_status_code = _request_srvinv('get', resource, resourceid)[0]
    if i_status_code == 200:
            # validate if value is json so we dont put it in there as string
            try:
                value = json.loads(value)
            except TypeError:
                # is pyobj, like list or tuple
                pass
            except ValueError:
                # is unparseable string
                pass
            # dict needs to be encapsulated
            if type(value) == dict:
                value = [value]
            to_set_value = json.dumps({"value": value})
            i_status_code = _request_srvinv(
                'patch', resource, resourceid, attribute, data=to_set_value)[0]
            if i_status_code == 202:
                return 0
            elif i_status_code == 304:
                return 4
            else:
                return 2
    elif i_status_code == 404:
        return 3
    elif i_status_code == 500:
        return 1


def register(resource, resourceid):
    """register the given resource-name for the given resource
    retuns 0 on success, 1 if the name exists and 2 on error"""
    to_register_resource = {
        "name": resourceid,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    to_register_resource = json.dumps(to_register_resource)
    i_status_code = _request_srvinv(
        'post', resource, data=to_register_resource)[0]
    if i_status_code == 201:
        return 0
    elif i_status_code == 409:
        return 1
    else:
        return 2
# end def register


def delete(resource, resourceid):
    """deletes the given resource-name in the given resource
    returns 0 on success and 1 on errror"""
    i_status_code = _request_srvinv('delete', resource, resourceid)[0]
    if i_status_code == 202:
        return 0
    elif i_status_code == 404:
        return 1
    else:
        return 2
# end def delete


def search(resource, attribute, value):
    """searches for objects with the given attribute/value combination
    value supports wildcards
    use_json: return a py-list if set to False, else return a json-string
    returns a list of object dictionaries"""
    found_resources = []

    cache_as_obj = go_srvinv_cache.get(resource)
    if cache_as_obj is None:
        return None

    for resource_to_search in cache_as_obj:
        # we need to make sure to convert arrays to strings
        #     so we can fnmatch them
        if attribute in resource_to_search:
            if isinstance(resource_to_search[attribute], list):
                attribute_to_search = json.dumps(resource_to_search[attribute])
            else:
                attribute_to_search = resource_to_search[attribute]
            if fnmatch.fnmatch(str(attribute_to_search), value):
                found_resources.append(resource_to_search)
    return found_resources
# end def search

# [EOF]
