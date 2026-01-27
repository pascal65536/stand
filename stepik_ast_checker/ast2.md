::python3
::header

::code
ticket = Ticket()
ret = ticket.add_product('Товар1', 99)
print(ret)

{'message': 'Ok', 'result': [{'Название товара': 'Товар1', 'Цена': 99, 'Количество': 0}]}

::footer

text = '''ticket = Ticket()
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
print(result)'''
    