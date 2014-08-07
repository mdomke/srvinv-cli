'''
libsrvinv - the main library serving default methods for srvinv clients
'''

from . import config
from . import helpers
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
    self.d_times = {}
    self.b_cache_use_file = b_cache_use_file if b_cache_use_file != None else config.cache_use_file
    self.s_cache_path_tmpl = config.cache_path_tmpl
    self.i_cache_duration_in_s = config.cache_duration_in_s
    return
  # end def __init__

  def get(self, s_resource, b_force=False):
    if (not b_force and
        s_resource in self.d_times and
        (time.time() <= self.d_times[s_resource])):
      if self.b_cache_use_file:
        s_cache_file_path = self.s_cache_path_tmpl.format(s_resource)
        if os.path.isfile(s_cache_file_path):
          with open(s_cache_file_path) as fp:
            return json.load(fp)
      else:
        return self.d_cache[s_resource]
    else:
      self.d_times[s_resource] = time.time() + self.i_cache_duration_in_s
      if self.b_cache_use_file:
        s_json_reply = self.fetch(s_resource)
        with open(s_cache_file_path, 'w') as fp:
          fp.write(s_json_reply)
          os.chmod(s_cache_file_path, 0o766)
          return json.loads(s_json_reply)
      else:
        x_reply = self.fetch(s_resource)
        self.d_cache[s_resource] = x_reply
        return x_reply
    return None
  # end def get

  def fetch(self, s_resource):
    (i_status_code, x_reply) = _request_srvinv('get', s_resource)
    if i_status_code == 200:
      return x_reply
    else:
      return None
  # end def fetch
# end class Db

go_srvinv_cache = SrvinvCache()

def _request_srvinv(rtype, resource, resourceid=None, attribute=None, data=None):
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
  except ValueError: # from json.loads
    i_status_code = -2
    x_reply = None
  return (i_status_code, x_reply)
# end def _request_srvinv

def get(resource, resourceid, attribute):
  """returns a tuple of return-code and text
  on success 0 and the requested value
  1 if the resource does not exist
  2 if the attribute does not exist
  3 on error"""
  (i_status_code, x_reply) = _request_srvinv('get', resource, resourceid)
  if i_status_code == 200:
    if not attribute:
      return (0, x_reply)
    else:
      if not attribute in x_reply:
        return (2, None)
      return (0, x_reply[attribute])
  elif i_status_code == 404:
    return (1, None)
  #elif i_status_code == 500:
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
      to_set_value = json.dumps({"value": value})
      i_status_code = _request_srvinv('patch', resource, resourceid, attribute, data=to_set_value)[0]
      if i_status_code == 202:
        return 0
      else:
        return 2
  elif i_status_code == 404:
    return 3
  elif i_status_code == 500:
    return 1

def register(resource, resourceid):
  """register the given resource-name for the given resource
  retuns 0 on success, 1 if the name exists and 2 on error"""
  to_register_resource = {"name": resourceid, "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat()}
  to_register_resource = json.dumps(to_register_resource)
  i_status_code = _request_srvinv('post', resource, data=to_register_resource)[0]
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
  else:
    return 1
# end def delete

def search(resource, attribute, value):
  """searches for objects with the given attribute/value combination
  value supports wildcards
  use_json: return a py-list if set to False, else return a json-string
  returns a list of object dictionaries"""
  found_resources = []

  cache_as_obj = go_srvinv_cache.get(resource)

  for resource_to_search in cache_as_obj:
    # we need to make sure to convert arrays to strings so we can fnmatch them
    if attribute in resource_to_search:
      if isinstance(resource_to_search[attribute], list):
         attribute_to_search = json.dumps(resource_to_search[attribute])
      else:
         attribute_to_search = resource_to_search[attribute]
      if fnmatch.fnmatch(str(attribute_to_search), value):
        found_resources.append(resource_to_search)
  return found_resources
# end def search

#[EOF]
