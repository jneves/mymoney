#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append("..")

import mymoney
import cmd
import getpass

class BankShell(cmd.Cmd):
    prompt = "MyMoneybits> "
    banks = []
    accounts = {}
    account_names = {}
    def do_cgd(self, line):
        "Adicionar um acesso à CGD."
        password = getpass.getpass("Insira o seu código de acesso: ")
        bank = mymoney.CGDCaixaDirecta({"user": line, "pass": password})
        try:
            accounts = bank.get_account_list()
            for acc in accounts:
                account = bank.get_account(acc[0])
                self.accounts["%s-%s" % (account.bank.name, acc[0])] = account
                self.account_names["%s-%s" % (account.bank.name, acc[0])] = acc[1]
            self.banks.append(bank)
        except Exception, e:
            print e

    def do_montepio(self, line):
        "Adicionar um acesso ao Montepio."
        print "Insira o seu código de acesso:"
        password = getpass.getpass("Insira o seu código de acesso: ")
        bank = mymoney.MontepioNet24({"user": line, "pass": password})
        try:
            accounts = bank.get_account_list()
            for acc in accounts:
                account = bank.get_account(acc[0])
                self.accounts["%s-%s" % (account.bank.name, acc[0])] = account
                self.account_names["%s-%s" % (account.bank.name, acc[0])] = acc[1]
            self.banks.append(bank)
        except:
            pass

    def do_listar(self, line):
        "Listar contas."
        for bank in self.banks:
            print bank.name
            print "-------------------------------------------"
            for account in bank.get_account_list():
                self.accounts
                print "%s-%s: %s" % (bank.name, account[0], account[1].replace("&amp;","&"))

    def do_mostrar(self, line):
        "Mostrar detalhes de conta"
        if line:
            for mov in self.accounts[line].get_information():
                print "%s: %s" % mov

    def do_movimentos(self, line):
        "Mostrar movimentos"
        if line:
            for mov in self.accounts[line].get_movements():
                print "%s\t%s\t%s%s\t%s" % (mov[1], mov[0], mov[3], mov[4], mov[2]) 
        else:
            for account in self.accounts.values():
                for mov in account.get_movements():
                    print "%s\t%s\t%s%s\t%s" % (mov[1], mov[0], mov[3], mov[4], mov[2])            
    
    def do_saldo(self, line):
        "Obter saldo de uma conta, ou de todas."
        if line:
            print "€ %.02f" % float(self.accounts[line].get_balance().replace(",","."))
        else:
            total = 0
            for account in self.accounts.values():
                total += float(account.get_balance().replace(",","."))
            print "€ %.02f" % total

    def do_mostrar(self, line):
        "Mostrar detalhes de conta."
        print line

    

    def do_sair(self, line):
        "Sair do banco."
        return True

    do_EOF = do_sair

shell = BankShell()
shell.cmdloop("Bem-vindo ao seu banco!")
