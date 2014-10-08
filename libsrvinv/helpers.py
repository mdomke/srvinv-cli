'''
libsrvinv - helpers
little functions that might be needed again and again and again
'''

import json


def is_json(data):
  try:
    json_object = json.loads(data)
  except ValueError as e:
    return False
  return True

# [EOF]
