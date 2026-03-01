class Ticket:
    def __init__(self):
        self.price_list = list()

    @property
    def total_cost(self):
        total = 0
        for pl in self.price_list:
            total += pl["Цена"] * pl["Количество"]
        return total

    def show_price_list(self):
        return self.price_list

    def add_product(self, name, cost):
        for pl in self.price_list:
            if name == pl["Название товара"]:
                return {"error": 0, "message": "Duplicate product"}
        pl = {"Название товара": name, "Цена": int(cost), "Количество": 0}
        self.price_list.append(pl)
        return {"message": "Ok", "result": [pl]}

    def buy_product(self, name, count):
        for pl in self.price_list:
            if name == pl["Название товара"]:
                pl["Количество"] = count if count > 0 else 0
                break
        else:
            return {"error": 1, "message": "Product not found"}
        return {"message": "Ok", "result": [pl]}

    def show_product(self):
        ret = list()
        for pl in self.price_list:
            if pl["Количество"]:
                ret.append(
                    (
                        pl["Цена"] * pl["Количество"],
                        pl["Цена"],
                        pl["Количество"],
                        pl["Название товара"],
                    )
                )
        ret.sort(reverse=True)
        res = list()
        msg = f'{"Название товара": <28} {"Цена": >8} {"Количество": >11} {"К оплате": >10}'
        res.append(msg)
        for r in ret:
            msg = f"{r[3]: <28} {r[1]: >8} {r[2]: >11} {r[0]: >10}"
            res.append(msg)
        res.append("-" * 60)
        msg = f'{"ИТОГО:": <49} {self.total_cost: >10}'
        res.append(msg)
        return {"message": "Ok", "result": res}

    def update_product(self, name, cost):
        for pl in self.price_list:
            if name == pl["Название товара"]:
                if pl["Количество"] != 0:
                    return {"error": 2, "message": "The item is reserved"}
                break
        else:
            return {"error": 1, "message": "Product not found"}
        res = {"Название товара": name, "Цена": int(cost), "Количество": 0}
        pl.update(res)
        return {"message": "Ok", "result": [res]}

    def remove_product(self, name):
        for pl in self.price_list:
            if name == pl["Название товара"]:
                break
        else:
            return {"error": 1, "message": "Product not found"}
        if pl["Количество"] != 0:
            return {"error": 2, "message": "The item is reserved"}
        self.price_list.remove(pl)
        return {"message": "Ok", "result": [pl]}

    def get_data(self, text):
        head = True
        self.price_list.clear()
        for row in text.split("\n"):
            if head:
                head = False
                continue
            if not row:
                continue
            name, cost = row.split(";")
            self.price_list.append(
                {"Название товара": name, "Цена": int(cost), "Количество": 0}
            )
        return self.price_list

    def __str__(self):
        return f"Ticket: {self.total_cost}"


if __name__ == "__main__":
    text = """Название товара;Цена
Яблоки;50
Бананы;30
Апельсины;40
Груши;45
Киви;60
Мандарины;55
Виноград;70
Арбуз;80
Дыня;75
Клубника;90
Малина;100
Черешня;110
Персики;95
Сливы;85
Лимоны;50
Лаймы;55
Папайя;65
Кокосы;120
Огурцы;30
Помидоры;35
Перец сладкий;40
Брокколи;45
Морковь;25
Картофель;20
Лук;15
Чеснок;10
Шпинат;50
Салат;45
Руккола;60
Цукини;35
Баклажаны;40
Капуста;25
Тыква;30
Репа;20
Фасоль;50
Горошек;40
Кукуруза;30
Молоко;60
Йогурт;70
Сыр;150
Творог;80
Сметана;50
Масло растительное;90
Оливковое масло;200
Хлеб белый;25
Хлеб черный;30
Булочки;15
Круассаны;40
Печенье;20
Шоколад;80
Конфеты;100
Торты;250
Пирожные;150
Кексы;100
Чай черный;40
Чай зеленый;50
Кофе молотый;150
Кофе растворимый;120
Сок апельсиновый;60
Сок яблочный;50
Газировка;30
Минеральная вода;20
Спиртные напитки;300
Пиво светлое;100
Вино красное;200
Вино белое;180
Шампанское;250
Сигареты;150
Зубная паста;70
Шампунь;150
Гель для душа;100
Мыло хозяйственное;30
Крем для рук;90
Детское мыло;50
Стиральный порошок;200
Ополаскиватель для белья;150
Чистящее средство;120
Пакеты для мусора;25
Салфетки бумажные;15
Туалетная бумага;30
Памперсы детские;400
Сосиски куриные;150
Колбаса вареная;200
Мясо говядины;500
Мясо свинины;450
Курица целая;300
Рыба свежая;400
Консервы рыбные;150
Гречка;60
Рис белый;70
Макароны спагетти;40
Овсянка;30
Сахар-песок;20
Соль поваренная;15
Перец черный молотый;50 
Корица молотая;60 
Имбирь молотый;80 
Ванильный сахар;90 
Разрыхлитель теста;30 
Мука пшеничная;25 
Какао-порошок;70 
Орехи грецкие;150 
Фундук жареный;200 
Арахис соленый;100 
Изюм черный;80 
Курага сушеная;90 
Финики сушеные;120 
Сушеные яблоки;70 
Чипсы картофельные;50 
Попкорн сладкий;40 
Сухарики хлебные;30 
"""

    text = """Название товара;Цена
Цемент;450
Кирпич;12
Шпаклевка;350
Лист гипсокартона;600
Доска обрезная;250
"""

    ticket = Ticket()
    ret = ticket.get_data(text)
    print(ret)

    # ret = ticket.remove_product("Сушеные яблоки")

    # ret = ticket.remove_product("Сушеные яблоки")
    # print(ret)

    # ret = ticket.update_product("Сухарики хлебные", 123)
    # print(ret)

    # print(ticket.price_list)

    # ret = ticket.buy_product("Сухарики хлебные", 1)
    # print(ret)

    # ret = ticket.update_product("Сухарики хлебные", 123)
    # print(ret)

    # print(ticket.total_cost)

    # ticket.buy_product("Ополаскиватель для белья", 6)
    # ticket.buy_product("Гречка", 12)
    # ticket.buy_product("Овсянка", 25)
    # ticket.buy_product("Шампунь", 50)
    # ticket.buy_product("Репа", 100)
    # print(ticket.price_list)
    # print(ticket.total_cost)

    # ticket.show_product()
