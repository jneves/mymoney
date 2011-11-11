from datetime import date, timedelta

class Account():
    def get_information(self):
        pass

    def get_balance(self):
        pass

    def get_movements(self, start_date=(date.today()-timedelta(weeks=1)), end_date=date.today, limit=100):
        pass

    def transfer_money(self, to, value):
        pass

    def pay_mb(self, entity, reference, value):
        pass
