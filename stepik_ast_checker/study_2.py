text = """
from solution import Ticket

ticket = Ticket()
name = "Яблоки"
cost = 200
result = ticket.add_product(name, cost)
print(result)
name = "Картофель"
cost = 90
result = ticket.add_product(name, cost)
print(result)
name = "Яблоки"
cost = 200
result = ticket.add_product(name, cost)
print(result)
print(ticket.show_price_list())
"""

exec(text)
