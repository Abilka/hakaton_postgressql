

from flask import Flask, request
import requests

import config
import openpyxl


class Excel:
    def __init__(self):
        self.wb = openpyxl.open('server.xlsx')
        self.sheet = self.wb['Лист1']

    def take_column_A(self):
        return list(map(lambda x: x[0].value, list(self.sheet.iter_rows())))


class ConClient:
    def __init__(self, addres: str):
        self.adr = addres
        self.job = 1

    def start_backup(self):
        return True

    def is_alive(self) -> bool:
        resutl = requests.get(self.adr)
        if resutl and resutl.json().get('status') == 200:
            return True
        else:
            return False

    def is_status(self) -> int:
        '''
        1 - свободен
        2 - занят
        3 - недоступен
        4 - требует внимания
        :return:
        '''
        resutl = requests.get(self.adr + '/status')
        if resutl:
            self.job = resutl.json().get('status_job')
        else:
            self.job = 4
        return self.job

SERVERS_LIST = Excel().take_column_A()
SERVERS_OBJECTS = list(map(lambda x: ConClient(x[0]), SERVERS_LIST))

app = Flask(__name__)

@app.route("/servers")
def server_list():
    return {"servers": Excel().take_column_A()}

@app.route("/send_backup", methods=['POST'])
def send_backup():
    server = request.args['ip']
    type_backup = request.args['type']
    #"http://" + self.adr + ":" + config.REST_PORT + '/status'
    requests.post("http://" + server + ":" + config.REST_PORT + '/backup', params={'start':"True", 'type': str(type_backup)})
    return {"servers": 'ok'}

@app.route("/validate")
def send_validate():
    server = request.args['ip']
    requests.get("http://" + server + ":" + config.REST_PORT + '/validate')
    return {"servers": 'ok'}

app.run(port=5001)
