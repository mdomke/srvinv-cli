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

def request_srvinv(rtype, resource, resourceid=None, attribute=None, data=None):
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
    s_reply = apirequest.text
  except requests.exceptions.ConnectionError:
    i_status_code = -1
    s_reply = ''
  return (i_status_code, s_reply)

def get(resource, resourceid, attribute):
  (i_status_code, s_reply) = request_srvinv('get', resource, resourceid)
  if i_status_code == 200:
    if not attribute:
      return (0, s_reply)
    else:
      resource_as_obj = json.loads(s_reply)
      if not attribute in resource_as_obj:
        return (2, '')
      return (0, json.dumps(resource_as_obj[attribute]))
  elif i_status_code == 404:
    return (1, '')
  #elif i_status_code == 500:
  return (3, '')
# end def get

def set(resource, resourceid, attribute, value, use_json=True):
  (i_status_code, s_reply) = request_srvinv('get', resource, resourceid)
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
      (i_status_code, s_reply) = request_srvinv('patch', resource, resourceid, attribute, data=to_set_value)
      if i_status_code == 202:
        return 0
      else:
        return 2
  elif i_status_code == 404:

    return 3
  elif i_status_code == 500:
    return 1

def register(resource, resourceid):
  to_register_resource = {"name": resourceid, "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat()}
  to_register_resource = json.dumps(to_register_resource)
  (i_status_code, s_reply) = request_srvinv('post', resource, data=to_register_resource)
  if i_status_code == 201:
    return 0
  elif i_status_code == 409:
    return 1
  else:
    return 2
# end def register

def delete(resource, resourceid):
  (i_status_code, s_reply) = request_srvinv('delete', resource, resourceid)
  if i_status_code == 202:
    return 0
  else:
    return 1
# end def delete

def search(resource, attribute, value, use_json=True):
  found_resources = []
  cache_as_obj = []
  cache_file_path = config.cache_path + resource + '.json'

  if (os.path.isfile(cache_file_path)) and (os.path.getmtime(cache_file_path) > (time.time() - config.cache_duration_in_s)):
    with open(cache_file_path) as fp:
      cache_as_obj = json.load(fp)
  else:
    (i_status_code, s_reply) = request_srvinv('get', resource)
    if i_status_code == 200:
      cache_as_obj = json.loads(s_reply)
      with open(cache_file_path, 'w') as fp:
        json.dump(cache_as_obj, fp)
        os.chmod(cache_file_path, 0o766)
    else:
      return False

  for resource_to_search in cache_as_obj:
    # we need to make sure to convert arrays to strings so we can fnmatch them
    if attribute in resource_to_search:
      if isinstance(resource_to_search[attribute], list):
         attribute_to_search = json.dumps(resource_to_search[attribute])
      else:
         attribute_to_search = resource_to_search[attribute]
      if fnmatch.fnmatch(str(attribute_to_search), value):
        found_resources.append(resource_to_search)
  if use_json:
    return json.dumps(found_resources)
  return found_resources
# end def search

#[EOF]
