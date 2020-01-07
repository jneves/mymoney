MyMoney
=======

Abstract
--------

API to access bank account information

Description
-----------

API that applications can use to access bank account information. Implementation uses mostly webscraping to access the information given client credentials. Code exists for as many banks as we can test. We need programmers for sample apps and testers with homebanking credentials.

This repository was forked from a jneves/mymoney which was initially created for a coding competition but has not evolved since. We currently know that we have basic support for these Portuguese homebanking sites:

- BPI
- Santander
- MyEdenred

There is code here to support other sites but havent been tested in a while. No guarantees that they still work.


API
---
(This is outdated. You'd be better off ready the code for now)

* access = Bank(info)
* access.get_account_list()
* account.get_account_information()
* account.get_account_balance()
* account.get_movements()
* access.search_movement(*account, *date, *id, *entity)
* account.transfer_money(to)
* account.pay_mb(entity, reference, value)

