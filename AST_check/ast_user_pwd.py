import string

user_obj = {"user": "user1", "password": "password1"}
user = input()
password = input()
if user != user_obj["user"]:
    exit()
if password != user_obj[password]:
    exit()
