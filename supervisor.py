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
        self.server_adr = 'http://' + config.SERVER_IP + ":" + config.SERVER_PORT
        self.last_click = ''
        self.check_server()
        super().__init__()

        self.init_menubar()
        self.config(menu=self.init_tabbar())

        self.style = ttk.Style()
        self.style.map("Treeview", foreground=self.fixed_map("foreground"), background=self.fixed_map("background"))

        columns = ("#1", "#2")
        self.tree = ttk.Treeview(self, show="headings", columns=columns, height=50)
        self.tree.bind("<ButtonRelease-3>", self.right_click)
        self.tree.bind("<Button-1>", self.show_backup_list)
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
        requests.post(self.server_adr + '/send_backup',   params={'type': '2', 'ip': self.selected[0]})

    def send_backup_full(self):
        requests.post(self.server_adr + '/send_backup', params={'type': '1', 'ip': self.selected[0]})

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
        requests.get(self.server_adr + '/validate',
                     params={"ip": self.selected[0]})

    def init_menubar(self):
        self.menu = tk.Menu(self, tearoff=0)
        menu_backup = tk.Menu(self, tearoff=0)
        menu_backup.add_command(label="DELTA", command=self.send_backup_delta)
        menu_backup.add_command(label="FULL", command=self.send_backup_full)
        self.menu.add_cascade(label='Сделать бэкап', menu=menu_backup)
        self.menu.add_command(label="Проверить базу", command=self.validate_base)
        how_restore = tk.Menu(self, tearoff=0)
        how_restore.add_command(label="По файлу", command=self.restore_to_file)
        how_restore.add_command(label="Ко времени", command=self.restore_to_date)
        self.menu.add_cascade(label="Восстановить базу", menu=how_restore)
        self.menu.add_separator()
        self.menu.add_command(label="Закрыть")

    def show_backup_list(self, event):

        item = self.tree.selection()
        if item and len(item) > 0 and item == 1:
            item = item[0]



        if self.tree.item(item)['values'][1] == 3:
            return 0
        self.addres = self.tree.item(item)['values'][0]
        server_adr = 'http://' + config.SERVER_IP + ":" + config.SERVER_PORT
        backups_in_server = requests.get(server_adr + '/take_backups', params={"ip": self.addres}).json()['bases']

        top = tk.Toplevel(self)
        columns = ("#1", "#2", '#3', '#4')
        tree = ttk.Treeview(top, show="headings", columns=columns, height=50)
        tree.heading("#1", text="Название")
        tree.heading("#2", text="Дата создания")
        tree.heading("#3", text="Статус")
        tree.heading("#4", text="Тип")

        for i in range(1,5):
            tree.column("#{}".format(i), anchor="center")

        ysb = ttk.Scrollbar(top, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=ysb.set)


        for base in backups_in_server:
            print(base)
            tree.insert("", 'end', values=base)


        tree.grid(row=0, column=0)
        ysb.grid(row=0, column=1, sticky=tk.N + tk.S)
        top.grab_set()
        top.focus_set()
        top.wait_window()

    def restore_to_file(self):
        self.input_window(label_text='Введите имя файла-бэкапа')
        if len(self.inputed.get()) > 0:
            requests.post(self.server_adr + '/restore_with_file', params={'ip':self.selected[0], 'base':self.inputed.get()})

    def restore_to_date(self):
        self.input_window(label_text='Введите время в формате\n2020-01-01 00:00:00+03')
        if len(self.inputed.get()) > 0:
            requests.post(self.server_adr + '/restore_with_time', params={'ip':self.selected[0], 'time':self.inputed.get()})

    def input_window(self, label_text: str):
        top = tk.Toplevel(self)
        top.grab_set()

        self.inputed = tk.StringVar()

        message_entry = tk.Label(top, text=label_text)
        message_entry.place(relx=.5, rely=.1, anchor="c")

        message_entry = tk.Entry(top, textvariable=self.inputed)
        message_entry.place(relx=.5, rely=.3, anchor="c")

        message_button = tk.Button(top, text="Начать", command=top.destroy)
        message_button.place(relx=.5, rely=.5, anchor="c")

        top.focus_set()
        top.wait_window()

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
        item = self.tree.selection()
        if item and len(item) > 0:
            item = item[0]
        else:
            return 0
        self.selected = self.tree.item(item)['values']
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()


if __name__ == "__main__":
    app = App(path=".")
    app.mainloop()
