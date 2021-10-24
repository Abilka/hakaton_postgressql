import os
import shutil
import subprocess
import threading

import requests
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
        cmd = subprocess.Popen(
            [config.PATH_PROPOSATAGE, 'validate', '-B', config.BACKUP_PATH, '--instance', config.BACKUP_INSTANCE,
             '--format=json', '>', config.TEMP_FILE + '/temp.txt'])
        try:
            data = json.loads(cmd.communicate()[0])[0]['backups']
        except:
            self.job = 4
            return {'status': 4}
        self.job = 1
        return True


    def restor_to_file(self, bp_id: str):
        self.job = 2
        subprocess.call([r"C:\Program Files\PostgreSQL\12\bin\pg_ctl.exe", 'stop', '-D', r'C:\Program Files\PostgreSQL\12\data', '-w'])
        for file in os.listdir(config.DATA_PATH):
            shutil.rmtree(config.DATA_PATH+'\\'+file,ignore_errors=True)
            try:
                os.remove(config.DATA_PATH+'\\'+file)
            except:
                pass

        try:
            subprocess.call(
            [config.PATH_PROPOSATAGE, 'restore', '-B', config.BACKUP_PATH, '--instance', config.BACKUP_INSTANCE, '-i', bp_id])
        except:
            pass
        subprocess.call([r"C:\Program Files\PostgreSQL\12\bin\pg_ctl.exe", 'start', '-N', r"postgresql-x64-12", '-D', r"C:\Program Files\PostgreSQL\12\data", '-w'])

        self.job = 1

        return True

    def restor_to_date(self, time: str):
        os.system(r'"C:\Program Files\PostgreSQL\12\bin\pg_ctl.exe" stop -D "C:\Program Files\PostgreSQL\12\data" -w')
        # 2020-01-01 00:00:00+03
        # 2021-10-23 00:00:00+03
        # формат времени
        self.job = 2
        for file in os.listdir(config.DATA_PATH):
            shutil.rmtree(config.DATA_PATH + '\\' + file, ignore_errors=True)
            try:
                os.remove(config.DATA_PATH + '\\' + file)
            except:
                pass
        subprocess.call(
            [config.PATH_PROPOSATAGE, 'restore', '-B', config.BACKUP_PATH, '--instance', config.BACKUP_INSTANCE, '--recovery-target-time', time])
        self.job = 1
        os.system('"C:\\Program Files\\PostgreSQL\\12\\bin\\pg_ctl.exe" runservice -N "postgresql-x64-12" -D "C:\\Program Files\\PostgreSQL\\12\\data" -w')
        return True

    def show_backups(self) -> dict:
        self.job = 2
        #, '>', config.TEMP_FILE + '/temp.txt'
        cmd = subprocess.Popen(
            [config.PATH_PROPOSATAGE, 'show', '-B',  config.BACKUP_PATH, '--format=json'], stdout=subprocess.PIPE, stderr=None, shell=True)
        data = json.loads(cmd.communicate()[0])[0]['backups']
        self.job = 1
        return {"bases": list(map(lambda x: [x['id'], x['end-time'], x['status'], x['backup-mode']], data))}

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
    if Me.job == 1 or Me.job == 4:
        Me.validate()
        return {'status': Me.job}

@app.route("/show_backups")
def show_backups():
    if Me.job == 1:
        return Me.show_backups()

@app.route("/restore_f")
def restore_file_filename():
    if Me.job == 1:
        return {'result': Me.restor_to_file(request.args['base']), 'status': Me.job}

@app.route("/restore_t")
def restore_file_time():
    if Me.job == 1:
        return {'result': Me.restor_to_date(request.args['time']), 'status': Me.job}

if __name__ == "__main__":
    app.run()
