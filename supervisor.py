import tkinter as tk
import tkinter as tk
import tkinter.ttk as ttk
import typing

import requests
import threading
import config


class ConClient:
    def __init__(self, addres: str):
        self.adr = addres
        self.job = 1

    def start_backup(self):
        requests.post("http://" + config.SERVER_IP + ":" + config.SERVER_PORT + '/send_backup',
                      params={'type': '1', 'ip': self.adr})

    def validate(self):
        requests.get('http://' + config.SERVER_IP + ":" + config.SERVER_PORT + '/validate',
                     params={"ip": self.adr})

    def is_alive(self) -> bool:
        # print("http://" + self.adr + ":" + config.REST_PORT + '/status')
        try:
            resutl = requests.get("http://" + self.adr + ":" + config.REST_PORT + '/status')
        except requests.exceptions.ConnectionError:
            self.job = 3
            return False
        if resutl.status_code == 200 or resutl.json()['status'] == 200:
            self.job = resutl.json()['status']
            return True
        else:
            self.job = 3
            return False

    def is_status(self) -> int:
        '''
        1 - свободен
        2 - занят
        3 - недоступен
        4 - требует внимания
        :return:
        '''
        resutl = requests.get("http://" + self.adr + ":" + config.REST_PORT + '/status', timeout=60)
        if resutl:
            self.job = resutl.json().get('status_job')
        else:
            self.job = 4
        return self.job


def update_status(servers: typing.List[ConClient]):
    thr_list = []
    for serv in servers:
        x = threading.Thread(target=serv.is_alive)
        thr_list.append(x)
        x.start()

    for thr in thr_list:
        thr.join()

    # return list(filter(lambda x: x.job==1 is True, servers))


class App(tk.Tk):
    def __init__(self, path):
        self.check_server()
        super().__init__()

        self.init_menubar()
        self.config(menu=self.init_tabbar())

        self.style = ttk.Style()
        self.style.map("Treeview", foreground=self.fixed_map("foreground"), background=self.fixed_map("background"))

        columns = ("#1", "#2")
        self.tree = ttk.Treeview(self, show="headings", columns=columns, height=50)
        self.tree.bind("<ButtonRelease-3>", self.right_click)
        self.tree.heading("#1", text="IP")
        self.tree.heading("#2", text="status code")
        ysb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        self.tree.tag_configure('red', background="red")
        self.tree.tag_configure('green', background="lime")
        self.tree.tag_configure('orange', background="orange")
        self.tree.tag_configure('need_watch', background="blue")
        self.tree.column("#1", anchor="center")
        self.tree.column("#2", anchor="center")
        self.writer_ip_status()


        # self.tree.bind("<<TreeviewSelect>>", self.print_selection)
        self.tree.grid(row=0, column=0)
        ysb.grid(row=0, column=1, sticky=tk.N + tk.S)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def writer_ip_status(self):
        for serv in self.SERVERS_OBJECT:
            if serv.job == 1:
                self.tree.insert("", 'end', values=[serv.adr, serv.job], tags=('green'))
            elif serv.job == 2:
                self.tree.insert("", 'end', values=[serv.adr, serv.job], tags=('orange'))
            elif serv.job == 3:
                self.tree.insert("", 'end', values=[serv.adr, serv.job], tags=('red'))
            elif serv.job == 4:
                self.tree.insert("", 'end', values=[serv.adr, serv.job], tags=('need_watch'))

    def validate_all(self):
        for base in self.SERVERS_OBJECT:
            base.validate()

    def send_backup_delta(self):
        requests.post("http://" + config.SERVER_IP + ":" + config.SERVER_PORT + '/send_backup',
                      params={'type': '2', 'ip': self.selected[0]})

    def send_backup_full(self):
        requests.post("http://" + config.SERVER_IP + ":" + config.SERVER_PORT + '/send_backup',
                      params={'type': '1', 'ip': self.selected[0]})

    def init_tabbar(self):
        filemenu = tk.Menu(self, tearoff=0)
        filemenu.add_command(label="Бэкап всех баз", command=self.backup_all_base)
        filemenu.add_command(label="Откат всех баз")
        filemenu.add_command(label="Проверка всех баз", command=self.validate_all)
        filemenu.add_command(label="Обновить список", command=self.recheck_server)
        return filemenu

    def backup_all_base(self):
        for base in self.SERVERS_OBJECT:
            base.start_backup()

    def validate_base(self):
        requests.get('http://' + config.SERVER_IP + ":" + config.SERVER_PORT + '/validate',
                     params={"ip": self.selected[0]})

    def init_menubar(self):
        self.menu = tk.Menu(self, tearoff=0)
        menu_backup = tk.Menu(self, tearoff=0)
        menu_backup.add_command(label="DELTA", command=self.send_backup_delta)
        menu_backup.add_command(label="FULL", command=self.send_backup_full)
        self.menu.add_cascade(label='Сделать бэкап', menu=menu_backup)
        self.menu.add_command(label="Проверить базу", command=self.validate_base)
        self.menu.add_command(label="Восстановить базу")
        self.menu.add_command(label="Возврат базы ко времени")
        self.menu.add_separator()
        self.menu.add_command(label="Закрыть")

    def fixed_map(self, option):
        return [elm for elm in self.style.map("Treeview", query_opt=option) if elm[:2] != ("!disabled", "!selected")]

    def check_server(self):
        SERVERS = requests.get('http://' + config.SERVER_IP + ":" + config.SERVER_PORT + '/servers').json()['servers']
        self.SERVERS_OBJECT = list(map(lambda x: ConClient(x), SERVERS))
        update_status(self.SERVERS_OBJECT)

    def recheck_server(self):
        self.tree.delete(*self.tree.get_children())
        SERVERS = requests.get('http://' + config.SERVER_IP + ":" + config.SERVER_PORT + '/servers').json()['servers']
        self.SERVERS_OBJECT = list(map(lambda x: ConClient(x), SERVERS))
        update_status(self.SERVERS_OBJECT)
        self.writer_ip_status()

    def right_click(self, event):
        item = self.tree.selection()[0]
        self.selected = self.tree.item(item)['values']
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()


if __name__ == "__main__":
    app = App(path=".")
    app.mainloop()
