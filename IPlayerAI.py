"""
  ----------------------------------------------------------------------------
  "THE BEER-WARE LICENSE"
  As long as you retain this notice you can do whatever you want with this
  stuff. If you meet an employee from Windward some day, and you think this
  stuff is worth it, you can buy them a beer in return. Windward Studios
  ----------------------------------------------------------------------------
  """

class Route(object):
    def __init__(self, startpoint, endpoint, person, length):
        self.startpoint = startpoint
        self.endpoint = endpoint
        self.person = person
        self.length = length


