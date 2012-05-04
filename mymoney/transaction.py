import time
from datetime import date

class Transaction:
    
    date=None           # date of movement/transaction
    value_date=None     # value date
    description=None    # description of transaction
    value=None          # value of transaction   
    
    
    def __init__(self,date,valuedate,description,value):
        self.date = self.parse_date(date)
        self.value_date = self.parse_date(valuedate)
        self.description = description
        self.value = self.parse_value(value)
    
    def parse_date(self,value):
        return value
    
    def parse_value(self,value):
        return value
    
    # todo: debug! remove this    
    def to_string(self):
        # this is here for debugging purposes only
        return "%s %s %s" % (self.date.isoformat(),self.description,self.value)

