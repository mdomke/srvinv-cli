'''
libsrvinv - the main library serving default methods for srvinv clients
'''

import config
import helpers
import requests
import json
import os
import fnmatch
import time
from datetime import datetime

api_url = config.master_url + config.api_version + '/'

def get(resource, resourceid, attribute):
  apirequest = requests.get(api_url + resource + 's/' + resourceid)
  if apirequest.status_code == 200:
    if not attribute:
      return apirequest.text
    else:
      resource_as_obj = json.loads(apirequest.text)
      return json.dumps(resource_as_obj[attribute])
  elif apirequest.status_code == 404:
    print 'resource not found'
    return False
  elif apirequest.status_code == 500:
    print 'error communicating with srvinv daemon'
    return False

def set(resource, resourceid, attribute, value, use_json=True):
  apirequest = requests.get(api_url + resource + 's/' + resourceid)
  if apirequest.status_code == 200:
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
      apirequest = requests.patch(api_url + resource + 's/' + resourceid + '/' + attribute, data=to_set_value)
      if apirequest.status_code == 202:
        return to_set_value
      else:
        print 'error communicating with srvinv daemon'
        return False
  elif apirequest.status_code == 404:
    print 'resource not found'
    return False
  elif apirequest.status_code == 500:
    print 'error communicating with srvinv daemon'
    return False

def register(resource, resourceid):
  to_register_resource = {"name": resourceid, "created_at": unicode(datetime.utcnow()), "updated_at": unicode(datetime.utcnow())}
  to_register_resource = json.dumps(to_register_resource)
  apirequest = requests.post(api_url + resource + 's', data=to_register_resource)
  if apirequest.status_code == 201:
    return to_register_resource
  elif apirequest.status_code == 409:
    print 'conflict: already registered'
    return False
  else:
    print 'error communicating with srvinv daemon'
    return False

def delete(resource, resourceid):
  apirequest = requests.delete(api_url + resource + 's/' + resourceid)
  if apirequest.status_code == 202:
    return 'deleted ' + resource + ': ' + resourceid
  else:
    print 'error communicating with srvinv daemon'
    return False

def search(resource, attribute, value, use_json=True):
  found_resources = []
  cache_as_obj = []
  cache_file_path = config.cache_path + resource + '.json'

  if (os.path.isfile(cache_file_path)) and (os.path.getmtime(cache_file_path) > (time.time() - config.cache_duration_in_s)):
    with open(cache_file_path) as fp:
      cache_as_obj = json.load(fp)
  else:
    apirequest = requests.get(api_url + resource + 's')
    if apirequest.status_code == 200:
      cache_as_obj = json.loads(apirequest.text)
      with open(cache_file_path, 'w') as fp:
        json.dump(cache_as_obj, fp)
        os.chmod(cache_file_path, 0766)
    else:
      print 'error communicating with srvinv daemon'
      return False

  for resource_to_search in cache_as_obj:
    # we need to make sure to convert arrays to strings so we can fnmatch them
    if attribute in resource_to_search.keys():
      if isinstance(resource_to_search[attribute], list):
         attribute_to_search = json.dumps(resource_to_search[attribute])
      else:
         attribute_to_search = resource_to_search[attribute]
      if fnmatch.fnmatch(str(attribute_to_search), value):
        found_resources.append(resource_to_search)
  if use_json:
    return json.dumps(found_resources)
  return found_resources
