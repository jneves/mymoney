#!/usr/bin/python

'''
This is a basic script that uses mymoney to simply get the most recent transactions from BPI.
You have to set your username, password and account number.
'''


import mymoney

username = 'username'
password = 'password'
account_number = 'accountnumber'

bank = mymoney.BPINet({"user": username, "pass": password})
try:
    account = bank.get_account(account_number)  
    transactions=account.get_movements()
    for transaction in transactions:
        print("%s\t%s\t%s" % (transaction.date,transaction.description,transaction.value))
except Exception as e:
    print(e)
