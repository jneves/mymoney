import time
from datetime import date

class Transaction:
    def __init__(self,date,valuedate,description,value):
        self.date = self.parse_date(date)
        self.value_date = self.parse_date(valuedate)
        self.description = description
        self.value = value
    
    def parse_date(self,value):
        pass
    
    # todo: debug! remove this    
    def tostring(self):
        # this is here for debugging purposes only
        print self.date.isoformat()
        print self.description
        print self.value

