import threading
import time
from tkinter import *

class UserInterface(threading.Thread):
    buffer = []

    def run(self):
        """
        Which the user or client sees and works with.
        This method runs every time to see whether there are new messages or not.
        """
        print ("ui, run")
        # TODO: Add CLI
        # self.t_cli = threading.Thread(target=self.runCLI)
        # self.t_cli.daemon = True
        # self.t_cli.start()
        self.runGUI()

    def runCLI(self):
        while True:
            message = input("Write your command:\n")
            self.buffer.append(message)

    def fill_buffer(self):
        self.buffer.append(self.cmd.get())
        self.buffer.append(self.msg.get())
        # self.message_label.config(text='change the value')
        # print("cmd, msg: ", self.cmd.get(), self.msg.get())

    def clear_entry_fields(self):
       self.cmd.delete(0,END)
       self.msg.delete(0,END)

    def runGUI(self):
        master = Tk()
        self.received_message = 'Received message: No message received!'
        # self.received_message = 'No message received!'
        # self.message_label = Label(master, text=self.received_message).grid(row=0)
        Label(master, text="Enter command:").grid(row=1)
        Label(master, text="Enter message:").grid(row=2)

        self.cmd = Entry(master)
        self.msg = Entry(master)
        self.cmd.insert(10,"Advertise")
        self.msg.insert(10,"Hi")

        self.cmd.grid(row=1, column=1)
        self.msg.grid(row=2, column=1)

        Button(master, text='Ok', command=self.fill_buffer).grid(row=3, column=0, sticky=W, pady=4)
        Button(master, text='Clear', command=self.clear_entry_fields).grid(row=3, column=1, sticky=W, pady=4)

        mainloop( )
