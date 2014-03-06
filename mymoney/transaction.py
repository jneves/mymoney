import time
from datetime import date

class Transaction:
    
    def __init__(self,date,valuedate,description,value):
        self.date = self.parse_date(date)               # date of movement/transactoin
        self.value_date = self.parse_date(valuedate)    # value date
        self.description = description                  # description of transaction
        self.value = self.parse_value(value)            # value of transaction
    
    def parse_date(self,value):
        return value
    
    def parse_value(self,value):
        return value
    
    def __str__(self):
        # this is here for debugging purposes only
        #return "%s %s %s" % (self.date.isoformat(),self.description,self.value)
        return "%s\t%s\t%s" % (self.date.isoformat(),self.description,self.value)

