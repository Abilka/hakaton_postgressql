import subprocess
import threading

from flask import Flask, request

import config
import json

class Client:
    def __init__(self):
        self.job = 1

    def backup(self, is_full: int = 1):
        self.job = 2
        backup_type = 'DELTA'
        if is_full == 1:
            backup_type = "FULL"
        subprocess.call(
            [config.PATH_PROPOSATAGE, 'backup', '-B', config.BACKUP_PATH, '--instance', config.BACKUP_INSTANCE,
             '-b', backup_type, '-h', 'localhost', '-p', str(config.CONNECT_PORT), '-U', config.BACKUP_ACCOUNT_NAME,
             '-d',
             'postgres'])
        self.job = 1
        return True

    def validate(self):
        self.job = 2
        subprocess.call(
            [config.PATH_PROPOSATAGE, 'validate', '-B', config.BACKUP_PATH, '--instance', config.BACKUP_INSTANCE,
             '--format=json', '>', config.TEMP_FILE + '/temp.txt'])
        with open(config.TEMP_FILE+'/temp.txt', 'r') as f:
            data = json.loads(f.read())[0]["backups"]
        ok_amount = list(map(lambda x: x['status'], data))
        if len(ok_amount) == len(data):
            self.job = 1
            return True
        self.job = 4
        return False



app = Flask(__name__)

Me = Client()


@app.route("/backup", methods=['POST'])
def send_with_online():
    is_backup = request.args.get("start")
    type_backup = int(request.args.get("type"))
    if is_backup == "True" and Me.job == 1:
        threading.Thread(target=Me.backup, args=(type_backup,)).start()
        return {'status': Me.job, 'backup': "ok", 'type': type_backup}
    else:
        return {'status': Me.job, 'backup': "not", 'type': type_backup}


@app.route("/status")
def status_client():
    return {'status': Me.job}

@app.route("/validate")
def validate_base():
    if Me.job == 1:
        Me.validate()
        return {'status': Me.job}

if __name__ == "__main__":
    app.run()
