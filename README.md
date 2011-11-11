MyMoney
=======

Abstract
--------

API to access bank account information

Description
-----------

Build an API that applications can use to access bank account information. Implementation uses webscraping to access the information given client credentials. Code will be done for as many banks as we can test. We need programmers for sample apps and testers with homebanking credentials. 

API
---

* access = Bank(info)
* access.get_account_list()
* account.get_account_information()
* account.get_account_balance()
* account.get_movements()
* access.search_movement(*account, *date, *id, *entity)
* account.transfer_money(to)
* account.pay_mb(entity, reference, value)

