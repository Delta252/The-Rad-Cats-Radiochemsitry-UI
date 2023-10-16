import tkinter as tk
from tkinter import ttk
from PIL import Image
import customtkinter as ctk
import Serial_lib as com 
from Serial_lib import Pump, Valve, Shutter, Mixer, Extract, Vessel, Nano
import os, cv2, time, multiprocessing, random, datetime
from flask import Flask, render_template, Response, request
import logging, csv
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

#pyinstaller --onedir -w --add-data "c:\users\idan\appdata\local\programs\python\python310\lib\site-packages\customtkinter;customtkinter\" UI.py
# UI styles 

font_XS = ("Consolas", 16, "normal")
font_S = ("Consolas", 18, "normal")
font_M = ("Consolas", 25, "normal")
font_L = ("Consolas", 30, "normal")

def set_mode(i: int):
    if i==0: ctk.set_appearance_mode("light")
    if i==1: ctk.set_appearance_mode("dark")
set_mode(0)
ctk.set_default_color_theme("dark-blue")
path = os.path.dirname(os.path.realpath(__file__))
class ProgressBar():
    def __init__(self, master, buffer):
        self.Pbar = ctk.CTkProgressBar(master, width= 300, height=25, corner_radius=5)
        self.time_est = ctk.CTkLabel(master, font=font_XS, text = "")
        self.buffer = buffer
    
    def SET(self, n_tasks: int):
        self.Pbar.place(relx=0.5, rely=0.4, anchor='center')
        self.time_est.place(relx=0.9, rely=0.4, anchor='center')
        self.Pbar.set(0)
        self.n_tasks = n_tasks
    
    def refresh(self):
        ratio = (self.n_tasks-self.buffer.Length())/self.n_tasks
        self.Pbar.set(ratio)
        estimated_time = 3*self.buffer.Length() #~3 seconds per task
        self.time_est.configure(text = "{} s".format(estimated_time))
        if ratio==1:
            self.Pbar.place_forget()
            self.time_est.place_forget()
            ratio=0.0

class MyTabView(ctk.CTkTabview):
    def __init__(self, master, pages = ["Module", "Vessels", "Phone"], **kwargs):
        super().__init__(master, **kwargs)

        for page in pages:
            self.add(page)

class MyLabel(ctk.CTkLabel):
    def __init__(self, master, text="NA", font=font_S, **kwargs):
        super().__init__(master,text=text, font=font, **kwargs)
        
    def update(self, new_text: str, **kwargs):
        self.configure(text = new_text, **kwargs)

# UI functions
def update_label(label, new_text):
    label.configure(text = new_text)
    return label

def add_image(frame, file_name, relx, rely, size = (200,40), anchor='center'):
    photo = ctk.CTkImage(Image.open(os.path.join(path, 'static\\', 'images\\', file_name), "r"), size=size)
    label = ctk.CTkLabel(frame, image = photo, text="")
    label.image = photo
    label.place(relx = relx, rely = rely, anchor = anchor)

def btn(frame, text: str, command=None, width=50, height=20, font=font_XS):
    btn = ctk.CTkButton(frame, 
                        text=text,
                        font=font,
                        border_width=0,
                        border_color='black',
                        corner_radius=5, 
                        width=width, height=height, 
                        compound = 'left',
                        command = command)
    return btn

def btn_img(frame, text: str,  file_name: str, command=None, Xresize = 30, Yresize = 30, font = font_M):
    try:
        photo = ctk.CTkImage(Image.open(os.path.join(path,'static\\', 'images\\', file_name), "r"), size = (Xresize,Yresize))
    except:
        photo=None
    btn = ctk.CTkButton(frame, 
                        text=text, 
                        image = photo,
                        font=font,
                        #fg_color='darkgrey',
                        #hover_color='darkblue', 
                        #border_width=1,
                        #border_color='black',
                        corner_radius=10, 
                        width=200, height=40,
                        command = command,
                        compound = 'left')
    btn.image = photo
    return btn

def entry_block(frame, text: str, spin=False, from_ = 0, to = 10, drop_list=None, wrap=True, width=50, **kwargs):
    """label followed by entry widget"""
    lbl = ctk.CTkLabel(frame, font=font_XS, text = text)
    if (spin):
        entry = ttk.Spinbox(frame, from_=from_, to=to, width=5, font= font_XS, wrap=wrap, **kwargs)
        entry.set(from_)
    elif (type(drop_list) == list):
        entry = ctk.CTkOptionMenu(frame,
                        values=drop_list,
                        width= 100,
                        **kwargs)
    else:
        entry = ctk.CTkEntry(frame,
                            width=width,
                            height=25,
                            font=font_XS,
                            border_width=0,
                            corner_radius=2, 
                            **kwargs)

    return lbl, entry

def place_2(rely, lbl, entry, relx = 0.5):
    lbl.place(relx = relx-0.05, rely = rely, anchor = 'e')
    entry.place(relx = relx, rely = rely, anchor = 'w')
    return lbl, entry

def place_n(widgets,rely, boundary=(0,1)):
    #equally distributed widgets across frame 
    L_bound, R_bound = boundary
    segment = R_bound-L_bound
    n = len(widgets)
    for i in range(len(widgets)):
        point = segment*(i+1)/(n+1)+L_bound
        try:
            widgets[i].place(relx = point, rely=rely, anchor='center')
        except:pass

def popup(text):
    popup = tk.Tk()
    popup.wm_title("Warning!")
    w = 250
    h = 100

    # get screen width and height
    ws = popup.winfo_screenwidth() 
    hs = popup.winfo_screenheight()

    # calculate x and y coordinates for the Tk root window
    x = (ws/2) - (w/2)
    y = (hs/2) - (h/2)

    popup.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    label = ttk.Label(popup, text=text, font=font_M)
    label.pack(side="top", fill="x", padx= 10, pady=10)
    B1 = ttk.Button(popup, text="Okay", command = popup.destroy)
    B1.pack(pady=10)
    popup.mainloop()

def check_isnumber(value, type = 'float'):
    if value != '':
        if type == 'float':
            try:
                float(value)
                value = float(value)
                return value
            except ValueError:
                popup('Please, insert a number')
        if type == 'int':
            try:
                int(value)
                value = int(value)
                return value
            except ValueError:
                popup('Please, insert an integer')
    else:
        pass

def Auto_Experiment(In, Out, Dose, Desktop = False):

    # type: (list [float], int, float, bool) -> int
    """
    -1 if Error,
    0 if Pass
    """

    tot_vol=0.0
    # check LDS sensors of relevant modules
    for i in range(len(In)):
        try:
            vol=In[i]
            if vol!=0.0:
                try:
                    Comps.pumps[i].poll()
                except:
                    print('this module does not exist')
                    return -1
                    
                if Comps.pumps[i].LDS.state == False:
                    # To do : Try 10 times before showing error box 
                    print("Please fill The vessel of Input module {}".format(i+1))
                    return -1
                
        except:
            pass
    for i in range(len(In)):
        try:
            vol=In[i]
            tot_vol+=vol  
            Comps.pumps[i].pump(vol)
        except:
            pass
    try:
        Comps.shutter.open()
        Comps.mixer.mix()
    except:pass
    try:
        time = Comps.radiate.D2T(float(Dose))
        Comps.BLOCK(time)
    except:pass
    try:
        Comps.mixer.stop()
        Comps.shutter.close() 
    except:pass

    try:
        output_index = Out
        if 0<=output_index<=4:
            com.valve_states(Comps.valves, 0)
            Comps.extract.set_slot(output_index+1)
            Comps.pumps[4].pump(-(tot_vol*2+10))
            Comps.pumps[5].pump((tot_vol*2+30))
        else:
            com.valve_states(Comps.valves, Out-4)
            Comps.pumps[4].pump(-(tot_vol*2+10))
    except:
        print('error ouptut')
        pass
    buffer.NOTIFY('Experiment Over')
    return 0  

#init comms
com.delete_file()
Comps = com.Components()
Comms = com.Comms(Comps)
phone = com.notif()
buffer = com.Buffer(Comms, Comps)
radiate = com.Cabin()

def init_module(label=None):
    global arduinos, device, gui
    buffer.RESET()
    try: Comms.CLOSE_SERIAL_PORT(arduinos)
    except: pass
    Ports = Comms.ID_PORTS_AVAILABLE()
    arduinos = [0]*7
    valves = [0]*5
    pumps = [0]*6
    LDS = [0]*5
    shutter = 0
    mixer = 0
    extract = 0
    temp = 0
    ves_in = [0]*5
    ves_out = [0]*7
    ves_main = Vessel(0, "ves_main")
    with open(os.path.join(path,"static\\hardware.csv"), "r") as hardware:
        modules_data = hardware.read().split("\n")
        for module_data in modules_data:
            module_data = module_data.split(",")
            print(module_data)
    for i in range(len(Ports)):
        print("\nSource: ", Ports[i])
        device = Comms.OPEN_SERIAL_PORT(Ports[i])
        #print("\nDevice: ", device)
        while(device.inWaiting() == 0):
            time.sleep(0.1)

        message = Comms.READ(device)
        
        deviceID  = message[0][0:4]
        print("\narduino: ", deviceID)
        
        if deviceID=="1001":
            ves_in[0] = Vessel()
            LDS[0]=com.LDS(device, deviceID, Comms)
            pumps[0] = Pump(device, deviceID, 1, buffer, LDS[0])
            arduinos[0] = Nano(device, deviceID, Ports[i])
            arduinos[0].add_component("Input Module 1")
        if deviceID=="1002":
            ves_in[1] = Vessel()
            LDS[1]=com.LDS(device, deviceID, Comms)
            pumps[1] = Pump(device, deviceID, 1, buffer, LDS[1]) 
            arduinos[1] = Nano(device, deviceID, Ports[i])
            arduinos[1].add_component("Input Module 2")          
        if deviceID=="1003":
            ves_in[2] = Vessel()
            LDS[2]=com.LDS(device, deviceID, Comms)
            pumps[2] = Pump(device, deviceID, 1, buffer, LDS[2])
            arduinos[2] = Nano(device, deviceID, Ports[i])
            arduinos[2].add_component("Input Module 3")
        if deviceID=="1004":
            ves_in[3] = Vessel()
            LDS[3]=com.LDS(device, deviceID, Comms)
            pumps[3] = Pump(device, deviceID, 1, buffer, LDS[3])
            arduinos[3] = Nano(device, deviceID, Ports[i])
            arduinos[3].add_component("Input Module 4")
        if deviceID=="1005":
            arduinos[4] = Nano(device, deviceID, Ports[i])
            arduinos[4].add_component("Ouput Module")
            temp=com.Temp(device, deviceID, Comms)
            for i in range(5):
                valves[i] = Valve(device, deviceID, i+1, buffer)
            for i in range(6):
                ves_out[i] = Vessel(0, 'Product '+str(i))
            
            pumps[4] = Pump(device, deviceID, 1, buffer)
            
        if deviceID=="1006":
            arduinos[5] = Nano(device, deviceID, Ports[i])
            arduinos[5].add_component("Shutter Module") 
            shutter = Shutter(device, deviceID, 1, buffer)
            mixer = Mixer(device, deviceID, 1, buffer)
        if deviceID=="1007":
            extract = Extract(device, deviceID, 1, buffer, n_slots = 5)
            pumps[5] = Pump(device, deviceID, 1, buffer)
            arduinos[6] = Nano(device, deviceID, Ports[i])
            arduinos[6].add_component("Extraction Module")
    for i in range(len(arduinos)):
        try:arduinos.remove(0)
        except:pass
    
    buffer.phone = phone
    buffer.arduinos = arduinos
    Comps.buffer = buffer
    Comps.arduinos = arduinos  #array
    Comps.ves_in = ves_in     #array
    Comps.ves_out = ves_out   #array
    Comps.ves_main = ves_main
    Comps.valves = valves        #array
    Comps.pumps = pumps         #array
    Comps.mixer = mixer
    Comps.shutter = shutter
    Comps.extract = extract
    Comps.radiate = radiate
    Comps.Temp = temp
    Comps.Bubble = [-1]*3
    Comps.LDS = LDS

    if len(arduinos):
        Comps.modules=[]
        for arduino in arduinos:
            Comps.modules.append("{}: {}\n".format(arduino.ID, arduino.get_components()))
    else:
        Comps.modules=['no modules found']

    try:update_label(label, '\n'.join(Comps.modules)) 
    except:pass
    print("\n------------ End initialisation --------------\n\n")

# UI classes
class Frame(ctk.CTkFrame):
    def __init__(self, master, text="", **kwargs):
        super().__init__(master, **kwargs)
        self.label = ctk.CTkLabel(self, text=text)
        self.label.grid(row=0, column=0, padx=20)

class P_Login(ctk.CTk):
    def __init__(self, *args, **kwargs):
        ctk.CTk.__init__(self, *args, **kwargs)
        ctk.CTk.wm_title(self, "Login")

        title = ctk.CTkLabel(self, text = "Login", font=font_L)
        title.place(relx = 0.5, rely = 0.06, anchor = 'center')

        self.geometry("700x400") 
        self.minsize(500,200) 

        frame_login = Frame(self)  # this is the frame that holds all the login details and buttons
        frame_login.place(relx= 0.5, rely = 0.55, relwidth=0.9, relheight=0.8, anchor = 'center')

        lbl_user, entry_user = place_2(0.3, *entry_block(frame_login, text = "Username: ", width=100))
        lbl_pw, entry_pw = place_2(0.5, *entry_block(frame_login, text = "Password: ", width=100))
        view_pass = ctk.CTkCheckBox(frame_login, text="show", onvalue="", offvalue="*", command=lambda: entry_pw.configure(show=view_pass.get()))
        view_pass.place(relx=0.85, rely=0.5, anchor='center')
        entry_pw.configure(show="*")
        view_pass.deselect()
        entry_user.insert(0, 'Arcadius')
        entry_pw.insert(0, 'Arcadius')

        btn_login = btn(frame_login, text="Login", command=lambda: getlogin())
        btn_register = btn(frame_login, text="Register", command=lambda: go_signup())
        
        check_status = ctk.CTkCheckBox(frame_login, text="operator", onvalue="operator", offvalue="viewer")
        btn_new_account = btn(frame_login, text="Create Account", command=lambda: signup())
        btn_login_frame = btn(frame_login, text="Already signed up?", command=lambda: login())

        
        def login():
            btn_new_account.place_forget()
            check_status.place_forget()
            btn_login_frame.place_forget()
            lbl_user.configure(text='Username: ')
            lbl_pw.configure(text='Password: ')
            btn_login.place(rely=0.70, relx=0.50)
            btn_register.place(rely=0.70, relx=0.75)
        
        def go_signup():
            btn_login.place_forget()
            btn_register.place_forget()
            lbl_user.configure(text='New Username: ')
            lbl_pw.configure(text='New Password: ')
            btn_login_frame.place(rely=0.70, relx=0.75)
            btn_new_account.place(relx=0.5, rely=0.85, anchor='center')
            check_status.place(relx=0.5, rely = 0.7, anchor= 'center')
            
        def getlogin():
            global gui
            username = entry_user.get()
            password = entry_pw.get()
            # if your want to run the script as it is set validation = True
            validation = validate(username, password)
            if validation:
                # tk.messagebox.showinfo("Login Successful",
                #                        "Welcome {}".format(username))
                top.destroy()
                gui = Main()
                gui.after(200,task)
                gui.after(200,GUI_Server_Comms)
                gui.after(3000, sensor_update)
                gui.mainloop()
            else:
                tk.messagebox.showerror("Information", "The Username or Password you have entered are incorrect ")

        def validate(username, password):
            # Checks the text file for a username/password combination.
            try:
                with open(os.path.join(path,"static\\", "credentials.csv"), "r") as credentials:
                    users_data = credentials.read().split("\n")
                    for user_data in users_data:
                        user_data = user_data.split(",")
                        if user_data[0] == username and user_data[1] == password:
                            return True
                    return False
            except FileNotFoundError:
                print("You need to Register first")
                return False
        
        def signup():
            # Creates a text file with the Username and password
            user = entry_user.get()
            pw = entry_pw.get()
            validation = validate_user(user)
            if not validation:
                tk.messagebox.showerror("Information", "That Username already exists")
            else:
                if len(pw) > 3:
                    credentials = open(os.path.join(path,"static\\","credentials.csv"), "a")
                    status = check_status.get()
                    credentials.write(f"{user},{pw},{status}\n")
                    credentials.close()
                    tk.messagebox.showinfo("Information", "Your account details have been stored.")
                    login()
                else:
                    tk.messagebox.showerror("Information", "Your password needs to be longer than 3 values.")

        def validate_user(username):
            # Checks the csv file for a username/password combination.
            try:
                with open(os.path.join(path,"static\\","credentials.csv")) as credentials:
                    for line in credentials:
                        line = line.split(",")
                        if line[0] == username:
                            return False
                return True
            except FileNotFoundError:
                return True
        
        login()
        
class MenuBar(tk.Menu):
    def __init__(self, parent):
        tk.Menu.__init__(self, parent)

        self.configure(background= 'blue', fg='red')

        self.add_command(label="Home", command=lambda: parent.show_frame(P_Home))
        self.add_command(label="Auto", command=lambda: parent.show_frame(P_Auto))
        self.add_command(label="Manual", command=lambda: parent.show_frame(P_Code))
        self.add_command(label="Testing", command=lambda: parent.show_frame(P_Test))
        menu_help = tk.Menu(self, tearoff=0)
        self.add_cascade(label="More", menu=menu_help)
        menu_help.add_command(label="Reset All",font=('Arial',11), command=lambda: init_module())
        menu_help.add_command(label="Parameter",font=('Arial',11), command=lambda: parent.show_frame(P_Param))

class Main(ctk.CTk):
    def __init__(self, *args, **kwargs):
        ctk.CTk.__init__(self, *args, **kwargs)
        ctk.CTk.wm_title(self, "ARCaDIUS")
        self.geometry("1100x700") 
        self.minsize(700,400) 
        container = ctk.CTkFrame(self, height=700, width=1200)
        container.pack(side="top", fill = "both", expand = "true")
        container.grid_rowconfigure(0, weight= 1)
        container.grid_columnconfigure(0, weight= 1)

        self.frames = {}

        for F in (P_Init, P_Home, P_Test, P_Auto, P_Code, P_Iter, P_Hist, P_Param, P_Monit):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(P_Init)

        menubar = MenuBar(self)
        ctk.CTk.config(self, menu=menubar)
        self.connect_cam()

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
        self.visible_frame = cont

    def connect_cam(self):
        global cam
        vid = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if not vid.isOpened():
            vid = cv2.VideoCapture(0)
        
        self.vid_frame_size = (int(vid.get(3)),int(vid.get(4)))
        self.vid = vid
        cam = vid
    
    def get_cam_frame(self, label, resize=1.0):
        try:
            #only update camera if frame is raised.
            _, frame = self.vid.read()
            opencv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            captured_image = Image.fromarray(opencv_image) #.transpose(Image.FLIP_LEFT_RIGHT)
            photo_image = ctk.CTkImage(captured_image, size=(int(self.vid_frame_size[0]*resize),int(self.vid_frame_size[1]*resize)))
            label.cv_image = frame
            label.photo_image = photo_image
            label.configure(image=photo_image)
        except:
            pass

    def update_buffer_list(self, textbox):
        prev_text = textbox.get("0.0", "end").strip()
        commands = buffer.READ()
        text = '\n'.join(commands).strip()
        if (prev_text!=text):
            textbox.configure(state= 'normal')
            textbox.delete("0.0", "end")
            textbox.insert("0.0", text)
            textbox.configure(state= 'disabled')
    
    def Quit_application(self):
        self.destroy()

class P_Init(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self, parent)

        title = ctk.CTkLabel(self, text = "SETUP", font=font_L)
        title.place(relx = 0.5, rely = 0.1, anchor = 'center')
        
        frame1 = Frame(self, text = "Setup communcation")
        frame1.place(relx= 0.5, rely = 0.55, relwidth=0.9, relheight=0.8, anchor = 'center')

        details = ctk.CTkLabel(frame1, font=font_XS, text='\n'.join(Comps.modules),justify= 'left')
        details.place(relx = 0.5, rely = 0.5, anchor = 'center') 

        btn1 = btn(frame1, text = 'reset', command=lambda: init_module(details))
        btn2 = btn(frame1, text="Continue", command=lambda: controller.show_frame(P_Home), width = 100, height=30, font = font_S)
        place_n([btn1, btn2], rely = 0.9, boundary = (0.3,0.7))

        init_module(details)

class P_Home(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self, parent)
        add_image(self, "arcadius.png", relx=0.5, rely=0.05, size=(300,60), anchor = 'n')

        btn1=btn_img(self, "Automatic", "auto.png", command=lambda: controller.show_frame(P_Auto))
        btn2=btn_img(self, "Testing", "iter.png", command=lambda: controller.show_frame(P_Test))
        btn3=btn_img(self, "Manual", "code.png", command=lambda: controller.show_frame(P_Code))
        place_n([btn1, btn3, btn2], 0.4)

        btn1=btn_img(self, "Monitor", "manual.png", command=lambda: controller.show_frame(P_Monit))
        btn2=btn_img(self, "History", "book.png", command=lambda: controller.show_frame(P_Hist))
        btn3=btn_img(self, "Param", "param.png", command=lambda: controller.show_frame(P_Param))
        place_n([btn1, btn2, btn3], 0.6)

        btn_exit = btn(self, text="Exit", command=lambda: controller.Quit_application())
        btn_exit.place(relx = 0.5, rely = 0.8, anchor = 'center')

class P_Param(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self,parent)
        title = ctk.CTkLabel(self, text = "Parameters", font=font_L)
        title.place(relx = 0.5, rely = 0.05, anchor = 'center')

        tabs = MyTabView(self, pages = ["Module", "Interface"])
        tabs.place(relx = 0.5, rely = 0.55, relwidth=0.8, relheight=0.8, anchor = 'center')

        frame_vessel = Frame(tabs.tab("Module"), text="Vessel levels")
        frame_vessel.place(relx= 0.7, rely = 0.25, relwidth=0.3, relheight=0.4, anchor = 'center')

        frame_nano = Frame(tabs.tab("Module"), text="Arduinos")
        frame_nano.place(relx= 0.3, rely = 0.25, relwidth=0.3, relheight=0.4, anchor = 'center')

        frame_cabinet = Frame(tabs.tab("Module"), text="Cabinet")
        frame_cabinet.place(relx= 0.3, rely = 0.75, relwidth=0.3, relheight=0.3, anchor = 'center')
        
        frame_push = Frame(tabs.tab("Interface"), text="Push notification")
        frame_push.place(relx= 0.5, rely = 0.5, relwidth=0.4, relheight=0.3, anchor = 'center')

        #arduino
        details = ctk.CTkLabel(frame_nano, font=font_XS, text='\n'.join(Comps.modules),justify= 'left')
        details.place(relx = 0.5, rely = 0.5, anchor = 'center') 
        btn_flush = btn(frame_nano, text = 'reset', command=lambda: init_module(details))
        btn_flush.place(relx=0.5, rely=0.1, anchor='center')

        # cabinet
        _, ent_height = place_2(0.5, *entry_block(frame_cabinet,'Cabinet height:'), 0.7)
        ent_height.insert(0, str(Comps.radiate.cabin_height))
        btn_save = btn(frame_cabinet, text ='save', command=lambda: Comps.radiate.set_cabin_height(float(ent_height.get())))
        btn_save.place(relx = 0.5, rely = 0.8, anchor = 'center')

        # vessels
        n = 3
        ent_Rname = [0]*n
        ent_Rvol = [0]*n
        names, volumes =  com.read_detail('details.csv')
        for i in range(n):
            if i==0: text = 'A'
            elif i==1: text = 'B'
            elif i==2: text = 'C'
            _, ent_Rname[i] = place_2(0.2 + 0.2*i, *entry_block(frame_vessel, text=text), relx = 0.25)
            _, ent_Rvol[i]  = place_2(0.2 + 0.2*i, *entry_block(frame_vessel, text=(' Vol: ')), relx = 0.75)
           
            ent_Rname[i].insert(0,names[i])
            ent_Rvol[i].insert(0,volumes[i])

        btn1 = btn(frame_vessel, text ='save', command=lambda: com.vessel_detail(ent_Rname, ent_Rvol))
        btn1.place(relx = 0.5, rely = 0.8, anchor = 'center')

        # interface
        mode_switch = ctk.CTkSwitch(master=tabs.tab("Interface"), text="Dark Mode", command=lambda: set_mode(mode_switch.get()), onvalue=1, offvalue=0)
        mode_switch.select()
        mode_switch.place(relx=0.5, rely=0.1, anchor='center')

        global rem_control
        rem_control = ctk.CTkSwitch(master=tabs.tab("Interface"), text="Remote control", onvalue=1, offvalue=0)
        rem_control.select()
        rem_control.place(relx=0.5, rely=0.3, anchor='center')

        _, ent_app = place_2(0.3, *entry_block(frame_push, text='app token'), relx=0.27)
        _, ent_user = place_2(0.6, *entry_block(frame_push, text='user key'), relx=0.27)
        btn_save = btn(frame_push, 'save', command=lambda: phone.set_token(ent_app.get(), ent_user.get()))
        btn_save.place(relx=0.5, rely= 0.9, anchor='center')
        ent_app.configure(width=200)
        ent_user.configure(width=200)
        ent_app.insert(0, phone.app_token)
        ent_user.insert(0, phone.user_key)

class P_Test(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self,parent)
        title = ctk.CTkLabel(self, text = "Testing", font=font_L)
        title.place(relx = 0.5, rely = 0.05, anchor = 'center')
        
        frame1 = Frame(self, text = "Valve")
        frame1.place(relx=0.175, rely=0.15, relwidth=0.3, relheight=0.8, anchor = 'n')
        frame12 = Frame(frame1, text = "shutter", fg_color = 'transparent')
        frame12.place(relx=0, rely=1, relwidth=1, relheight=0.5, anchor = 'sw')

        frame2 = Frame(self, text = "Pump")
        frame2.place(relx=0.5, rely=0.15, relwidth=0.3, relheight=0.8, anchor = 'n')

        frame3 = Frame(self, text = "Mixer")
        frame3.place(relx=0.825, rely=0.15, relwidth=0.3, relheight=0.38, anchor = 'n')

        frame4= Frame(self, text = "Extract")
        frame4.place(relx=0.825, rely=0.55, relwidth=0.3, relheight=0.4, anchor = 'n')

        #box 1 Valve
        _, ent_valve = place_2(0.2, *entry_block(frame1, "select valve: ", spin=True, from_=1, to=len(Comps.valves)))

        btn1 = btn(frame1, text="close", command=lambda: Comps.valves[int(ent_valve.get())-1].close())
        btn2 = btn(frame1, text="open", command=lambda: Comps.valves[int(ent_valve.get())-1].open())
        btn3 = btn(frame1, text="mid", command=lambda: Comps.valves[int(ent_valve.get())-1].mid())
        place_n([btn1, btn2, btn3], rely=0.3)
        #box 1.2 Shutter
        
        btn1 = btn(frame12, text="close", command=lambda: Comps.shutter.close())
        btn2 = btn(frame12, text="open", command=lambda: Comps.shutter.open())
        btn3 = btn(frame12, text="mid", command=lambda: Comps.shutter.mid())
        place_n([btn1, btn2, btn3], rely=0.3)

        #box 2 pump
        _, ent_pump = place_2(0.2,*entry_block(frame2, "select pump: ", spin=True, from_=1, to=len(Comps.pumps)))
        _, ent_vol = place_2(0.3, *entry_block(frame2, "Volume (ml)"))

        btn1 = btn(frame2, text="send", command=lambda: Comps.pumps[int(ent_pump.get())-1].pump(float(ent_vol.get())))
        btn1.place(relx = 0.5, rely = 0.4, anchor = 'center')

        #box 3 mixer
        btn0 = btn(frame3, text="slow", command=lambda: Comps.mixer.slow())
        btn1 = btn(frame3, text="normal", command=lambda: Comps.mixer.mix())
        btn3 = btn(frame3, text="fast", command=lambda: Comps.mixer.fast())
        btn2 = btn(frame3, text="stop", command=lambda: Comps.mixer.stop())
        place_n([btn0, btn1, btn3, btn2], rely = 0.2)

        #box 4 extract
        _, ent_ext = place_2(0.2,*entry_block(frame4, "select slot: ", spin=True, from_=1, to=5))
        ent_ext.config(command=lambda: Comps.extract.set_slot(int(ent_ext.get())))
        
class P_Auto(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self,parent)
        title = ctk.CTkLabel(self, text = "Automatic", font=font_L)
        title.place(relx = 0.5, rely = 0.1, anchor = 'center')

        frame1 = Frame(self, text = 'Gold Nano Particle Experiment')
        frame1.place(relx= 0.5, rely = 0.55, relwidth=0.45, relheight=0.8, anchor = 'e')
        frame2 = Frame(self, fg_color = 'transparent')
        frame2.place(relx= 0.5, rely = 0.55, relwidth=0.45, relheight=0.8, anchor = 'w')

        ent_P = [0]*4
        _, ent_P[0] = place_2(0.2, *entry_block(frame1, text="Gold    (ml)"))
        _, ent_P[1] = place_2(0.3, *entry_block(frame1, text="Alcohol (ml)"))
        _, ent_P[2] = place_2(0.4, *entry_block(frame1, text="Input 3 (ml)"))
        _, ent_P[3] = place_2(0.5, *entry_block(frame1, text="Water   (ml)"))
        _, ent_I = place_2(0.6, *entry_block(frame1, text="Total dosage (Gy)"))

        
        out_list = ["OUTPUT 1", "OUTPUT 2", "OUTPUT 3", "OUTPUT 4", "OUTPUT 5", "RECYCLE", "INPUT 3", "SPARE", "SPARE", "SPARE"]
        _, sel_output = place_2(0.7, *entry_block(frame1, text="Select Output", drop_list=out_list))

        btn1 = btn(frame1, text="Start", width = 100, height=35, command=lambda: experiment(), font=font_S)
        btn1.place(relx = 0.5, rely = 0.8, anchor = 'center')
        btn2 = btn(frame1, text="Wash", command=lambda: com.WASH(Comps)) 
        btn2.place(relx = 0.8, rely = 0.8, anchor = 'center')
        # temperature
        self.temperature_label = ctk.CTkLabel(self, text='')
        self.temperature_label.place(relx = 0.9, rely = 0.1, anchor = 'center')
        try:
            Comps.Temp.new_label(self.temperature_label)
        except:
            pass
        #progress bar
        Pbar = ProgressBar(frame2, buffer)

        def user_input_check(entry_Pump, module_number):
            """
            checks the user input for pumping liquids from input modules
            returns True if input can be executed
            Flase otherwise
            """
            try:
                volume=float(entry_Pump.get())
                if volume!=0.0:
                    # com.Input_Ready(Comps) make the folloing into a funcion
                    try:
                        Comps.pumps[module_number].poll()
                        print('pump {}, state LDS {}'.format(module_number, Comps.pumps[module_number].LDS.state))
                        if Comps.pumps[module_number].LDS.state == False:
                            # To do : Try 10 times before showing error box 
                            tk.messagebox.showerror("Action Required", "Please fill The vessel of Input module {}".format(module_number+1))
                            return False
                    except:
                        tk.messagebox.showerror("Information", "Input module {} is not connected".format(module_number+1))
                        print('this module does not exist')
                        return False
                    return True
            except:
                return True
        def experiment():
            tot_vol=0.0
            for i in range(len(ent_P)):
                if not user_input_check(ent_P[i], i):
                    return
            for i in range(len(ent_P)):
                try:
                    vol=float(ent_P[i].get())
                    tot_vol+=vol  
                    Comps.pumps[i].pump(vol)
                except:
                    pass
            try:
                Comps.shutter.open()
                Comps.mixer.mix()
            except:pass
            try:
                time = Comps.radiate.D2T(float(ent_I.get()))
                Comps.buffer.BLOCK(time)
            except:pass
            try:
                Comps.mixer.stop()
                Comps.shutter.close() 
            except:pass

            try:
                output_index = out_list.index(sel_output.get())
                if 0<=output_index<=4:
                    com.valve_states(Comps.valves, 0)
                    Comps.extract.set_slot(output_index+1)
                    Comps.pumps[4].pump(-(tot_vol*2+10))
                    Comps.pumps[5].pump((tot_vol*2+20))
                else:
                    com.valve_states(Comps.valves, out_list.index(sel_output.get())-4)
                    Comps.pumps[4].pump(-(tot_vol*2+10))
            except:
                print('error ouptut')
                pass
            buffer.NOTIFY('Experiment Over')
            Pbar.SET(buffer.Length())
            
       
        # buffer list
        textbox = ctk.CTkTextbox(frame2,width=300, height=200, state= 'normal')
        textbox.place(relx=0.5, rely=0, anchor="n")
        def update_buffer():
            try:
                if (controller.visible_frame==P_Auto):
                    controller.update_buffer_list(textbox)
                    Pbar.refresh()
            except:
                pass
            textbox.after(500, update_buffer)
        update_buffer()

        #camera
        label = ctk.CTkLabel(frame2, text="")
        label.place(relx = 0.5, rely = 1, anchor = 's')
        def update_cam():
            try:
                if (controller.visible_frame==P_Auto):
                    controller.get_cam_frame(label, resize = 0.6)
            except:
                pass
            label.after(50, update_cam)
        update_cam()

class Scratch():
    def __init__(self, frame, rely):
        self.rely = rely
        
        module_list = ["Input", "Output", "Mix", "Shutter", "Extract", "Delay"]
        _, combo = place_2(rely,*entry_block(frame, text="", drop_list=module_list),0.1)
        combo.configure(command=self.combo_select)
        self.combo=combo

        In_widgets = [0]*4
        Out_widgets = [0]*4
        mix_widgets = [0]*4
        shutter_widgets = [0]*4
        Ext_widgets = [0]*4
        system_widgets = [0]*4

        In_widgets[0], In_widgets[1] = entry_block(frame, "select pump: ", spin=True, from_=1, to=4)
        In_widgets[2], In_widgets[3] = entry_block(frame, "Volume (ml)")
        
        self.out_list = ["Out 1", "Out 2", "Out 3", "Out 4", "Out 5", "Out 6"]
        Out_widgets[0], Out_widgets[1] = entry_block(frame, text="Select Output", drop_list=self.out_list)
        Out_widgets[2], Out_widgets[3] = entry_block(frame, "Volume (ml)")
        
        # make drop down slow, mid , fast, and Delay (s)
        mix_list = ["Stop", "Slow", "Normal", "Fast"]
        mix_widgets[0], mix_widgets[1] = entry_block(frame, text="Speed", drop_list=mix_list)
        
        # add delay (s)
        shutter_list = ["Open", "Close", "Mid"]
        shutter_widgets[0], shutter_widgets[1] = entry_block(frame, text="mode", drop_list=shutter_list)
        
        Ext_widgets[0], Ext_widgets[1] = entry_block(frame, "select slot: ", spin=True, from_=1, to=5)
        Ext_widgets[2], Ext_widgets[3] = entry_block(frame, "Volume (ml)")
        
        system_widgets[0], system_widgets[1] = entry_block(frame, text="Block time (s)")

        self.In_widgets = In_widgets
        self.Out_widgets = Out_widgets
        self.mix_widgets = mix_widgets
        self.shutter_widgets = shutter_widgets
        self.Ext_widgets = Ext_widgets
        self.system_widgets = system_widgets
        self.all_widgets = In_widgets+Out_widgets+mix_widgets+Ext_widgets+shutter_widgets+system_widgets
        self.combo_select(combo.get())

        self.current_widgets=self.In_widgets
    
    def combo_select(self, selected):
        for w in self.all_widgets:
            try: 
                w.place_forget()
            except AttributeError: 
                pass
        if selected=="Input":     current_widgets = self.In_widgets
        elif selected=="Output":  current_widgets = self.Out_widgets
        elif selected=="Mix":     current_widgets = self.mix_widgets
        elif selected=="Shutter": current_widgets = self.shutter_widgets
        elif selected=="Extract": current_widgets = self.Ext_widgets
        elif selected=="Delay":  current_widgets = self.system_widgets
        
        self.current_widgets = current_widgets
        place_n(self.current_widgets, rely=self.rely, boundary=(0.2,1))

    def send_command(self):
        selected = self.combo.get()
        print(selected)
        if selected=="Input":     
            num = int(self.In_widgets[1].get())-1
            vol = float(self.In_widgets[3].get())
            Comps.pumps[num].pump(vol)
        elif selected=="Output":  
            state = self.out_list.index(self.Out_widgets[1].get())
            vol = float(self.Out_widgets[3].get())
            com.valve_states(Comps.valves, state)
            Comps.pumps[4].pump(-vol)
        elif selected=="Mix":  
            state = self.mix_widgets[1].get()
            match state:
                case 'Stop':
                    Comps.mixer.stop()
                case 'Slow':
                    Comps.mixer.slow()
                case 'Normal':
                    Comps.mixer.mix()
                case 'Fast':
                    Comps.mixer.fast()
                case _:
                    print('unknown state')
                    pass
        elif selected=="Shutter": 
            state = self.shutter_widgets[1].get()
            match state:
                case 'Open':
                    Comps.shutter.open()
                case 'Close':
                    Comps.shutter.close()
                case 'Mid':
                    Comps.shutter.mid()
                case _:
                    print('unknown state')
                    pass
        elif selected=="Extract": 
            state = int(self.Ext_widgets[1].get())
            vol = float(self.Ext_widgets[3].get())
            Comps.extract.set_slot(state)
            Comps.pumps[5].pump(vol)
        elif selected=="Delay":  
            time = float(self.system_widgets[1].get())
            Comps.buffer.BLOCK(time)
    
    def delete(self):
        self.combo.place_forget()
        for w in self.all_widgets:
            try: 
                w.place_forget()
            except AttributeError:
                pass
        del self

class P_Code(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self,parent)
        title = ctk.CTkLabel(self, text = "Manual", font=font_L)
        title.place(relx = 0.5, rely = 0.1, anchor = 'center')

        frame1 = Frame(self)
        frame1.place(relx= 0.6, rely = 0.55, relwidth=0.55, relheight=0.8, anchor = 'e')
        frame2 = Frame(self, fg_color = 'transparent')
        frame2.place(relx= 0.6, rely = 0.55, relwidth=0.4, relheight=0.8, anchor = 'w')
        scratch_rows = [Scratch(frame1, 1/15)]
        Pbar = ProgressBar(frame2, buffer)

        def new_row():
            rely = (len(scratch_rows)+1)/15
            scratch_rows.append(Scratch(frame1, rely))
        def start_experiment():
            for scratch_row in scratch_rows:
                scratch_row.send_command()
            Pbar.SET(buffer.Length())
        def delete_row():
            scratch_rows.pop(-1).delete()

        btn_minus = btn_img(self, text="remove step", file_name='minus.png', command=lambda: delete_row())    
        btn_start = btn(self, text="Start", width = 100, height=35, command=lambda: start_experiment(), font=font_S)
        btn_plus = btn_img(self, text="add step", file_name='plus.png', command=lambda: new_row())
        
        place_n([btn_minus, btn_start, btn_plus], 0.9, (0.05,0.6))
        # buffer list

        textbox = ctk.CTkTextbox(frame2,width=300, height=200, state= 'normal')
        textbox.place(relx=0.5, rely=0, anchor="n")
        def update_buffer():
            try:
                if (controller.visible_frame==P_Code):
                    controller.update_buffer_list(textbox)
                    Pbar.refresh()
            except:
                pass
            textbox.after(500, update_buffer)
        update_buffer()

        #camera
        label = ctk.CTkLabel(frame2, text="")
        label.place(relx = 0.5, rely = 1, anchor = 's')
        def update_cam():
            try:
                if (controller.visible_frame==P_Code):
                    controller.get_cam_frame(label, resize = 0.6)
            except:
                pass
            label.after(50, update_cam)
        update_cam()

class P_Iter(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self,parent)

        title = ctk.CTkLabel(self, text = "Iterative experiment", font=font_L)
        title.place(relx = 0.5, rely = 0.1, anchor = 'center')

        frame1 = Frame(self, text= "setup experiment")
        frame1.place(relx= 0.5, rely = 0.55, relwidth=0.45, relheight=0.8, anchor = 'e')
        frame2 = Frame(self, fg_color = 'transparent')
        frame2.place(relx= 0.5, rely = 0.55, relwidth=0.45, relheight=0.8, anchor = 'w')    

        _, ent_volA = place_2(0.2, *entry_block(frame1, "A (ml):"), 0.4)
        _, ent_stepA = place_2(0.2, *entry_block(frame1, " + it x", spin=True, from_=-20, wrap=False, increment = 0.1), 0.7)
        ent_stepA.set(0)
        _, ent_volB = place_2(0.3, *entry_block(frame1, "B (ml):"), 0.4)
        _, ent_stepB = place_2(0.3, *entry_block(frame1, " + it x", spin=True, from_=-20, wrap=False, increment = 0.1), 0.7)
        ent_stepB.set(0)
        _, ent_volC = place_2(0.4, *entry_block(frame1, "C (ml):"), 0.4)
        _, ent_stepC = place_2(0.4, *entry_block(frame1, " + it x", spin=True, from_=-20, wrap=False, increment = 0.1), 0.7)
        ent_stepC.set(0)
        _, ent_Shut= place_2(0.5, *entry_block(frame1, "Dosage (Gy):"), 0.4)
        _, ent_step_Shut = place_2(0.5, *entry_block(frame1, " + it x", spin=True, wrap=False, from_=0), 0.7)

        _, ent_count = place_2(0.6, *entry_block(frame1, "number of iterations:", spin=True, from_=1, to=10))
        
        btn1 = btn(frame1, text="Start", width = 100, height=35, command=lambda: iterate(), font=font_S)
        btn1.place(relx = 0.5, rely = 0.8, anchor = 'center')

        #progress bar
        Pbar = ProgressBar(frame2, buffer)
       
        # buffer list
        textbox = ctk.CTkTextbox(frame2,width=300, height=150, state= 'normal')
        textbox.place(relx=0.5, rely=0, anchor="n")
        def update_buffer():
            try:
                if (controller.visible_frame==P_Iter):
                    controller.update_buffer_list(textbox)
                    Pbar.refresh()
            except:
                pass
            textbox.after(500, update_buffer)
        update_buffer()

        #camera
        label = ctk.CTkLabel(frame2, text="")
        label.place(relx = 0.5, rely = 1, anchor = 's')
        def update_cam():
            try:
                if (controller.visible_frame==P_Iter):
                    controller.get_cam_frame(label, resize = 0.5)
            except:
                pass
            label.after(50, update_cam)
        update_cam()

        def iterate():
            Ra = ent_volA.get()
            Ra_step = ent_stepA.get()
            Rb = ent_volB.get()
            Rb_step = ent_stepB.get()
            Rc = ent_volC.get()
            Rc_step = ent_stepC.get()
            dosage = ent_Shut.get()
            dosage_step = ent_step_Shut.get()
            count = int(ent_count.get())

            for i in range(count):
                vol=0
                if Ra!="" and Ra_step!="":
                    vola = float(Ra) + float(Ra_step)*i
                    vol += vola
                    Comps.pumps[0].pump(vola)
                if Rb!="" and Rb_step!="":
                    volb = float(Rb) + float(Rb_step)*i
                    vol += volb
                    Comps.pumps[1].pump(volb)
                if Rc!="" and Rc_step!="":
                    volc = float(Rc) + float(Rc_step)*i
                    vol += volc
                    Comps.pumps[2].pump(volc)
                if dosage!="" and dosage_step!="":
                    try:
                        Comps.shutter.open()
                        time = Comps.radiate.D2T(float(dosage)+float(dosage_step)*i)
                        Comps.buffer.BLOCK(time)
                        Comps.shutter.close()
                    except:pass
                try:
                    com.valve_states(Comps.valves, 3)
                    Comps.pumps[4].pump(-(vol+10))
                except:pass

            Pbar.SET(buffer.Length())
            buffer.NOTIFY('Iterations Over')
      
class P_Hist(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self,parent)     

        title = ctk.CTkLabel(self, text = "Task", font=font_L)
        title.place(relx = 0.5, rely = 0.1, anchor = 'center') 

        sub = ctk.CTkLabel(self, text = "Queue", font=font_M)
        sub.place(relx = 0.2, rely = 0.1, anchor = 'center')

        sub1 = ctk.CTkLabel(self, text = "History", font=font_M)
        sub1.place(relx = 0.7, rely = 0.1, anchor = 'center')

        frame1 = Frame(self)
        frame1.place(relx= 0.95, rely = 0.55, relwidth=0.4, relheight=0.8, anchor = 'e')

        frame2 = Frame(self)
        frame2.place(relx= 0.05, rely = 0.55, relwidth=0.4, relheight=0.8, anchor = 'w')
        frame2.grid_rowconfigure(0, weight=1)  # configure grid system
        frame2.grid_columnconfigure(0, weight=1)

        scroll = ttk.Scrollbar(frame1, orient = "vertical")
        scroll.place(relx= 1, rely = 0.5, relwidth=0.03, relheight=1, anchor = 'e')

        list = tk.Listbox(frame1, bd= 3, relief = "groove", selectmode= "SINGLE", yscrollcommand = scroll.set )
        
        list.place(relx= 0, rely = 0.5, relwidth=0.97, relheight=1, anchor = 'w')
        scroll.config(command = list.yview )

        btn1 = btn(self, text="skip next", command=lambda: buffer.POP())
        btn1.place(relx = 0.5, rely = 0.4, anchor = 'center')
        btn2 = btn(self, text="skip last", command=lambda: buffer.POP_LAST())
        btn2.place(relx = 0.5, rely = 0.5, anchor = 'center')
        btn3 = btn(self, text="Clear Queue", command=lambda: buffer.RESET())
        btn3.place(relx = 0.5, rely = 0.6, anchor = 'center')

        textbox = ctk.CTkTextbox(frame2, state= 'normal')
        textbox.grid(row=0, column=0, sticky="nsew")
        def update_page():
            try:
                if (controller.visible_frame==P_Hist):
                    controller.update_buffer_list(textbox)                   
            except:
                pass
            # update history
            list.delete(0, 'end') #clear the list before updating
            time, command = com.read_detail("commands.csv")
            for x in range(len(time)):
                list.insert(0, time[x] + "   " + command[x])
            textbox.after(500, update_page)
        update_page()

class P_Monit(ctk.CTkFrame):
    def __init__(self, parent, controller):
        #monitoring page
        ctk.CTkFrame.__init__(self,parent) 

        title = ctk.CTkLabel(self, text = "Graph", font=font_L)
        title.place(relx = 0.5, rely = 0.1, anchor = 'center') 

        frame = Frame(self, fg_color='transparent')
        frame.place(relx= 0.5, rely = 0.5, relwidth=0.7, relheight=0.7, anchor = 'center')

        button1 = btn(self, text="Back to Home",command=lambda: controller.show_frame(P_Home))
        button1.place(relx = 0.2, rely = 0, anchor = 'n')

        try:
            Comps.Temp.new_graph(com.Graph(frame))
        except:
            pass

def task():
    # Communication
    # send command out of buffer
    buffer.OUT()
    # get response from current device
    Comms.READ(buffer.current_device)
    
    #------- start ----------#
    temp_list = buffer.READ()
    #for i in range(0,10):
    #    temp_list.append(random.randint(0,10))
    try:
        Current_cmd.put(temp_list[0], block=False)
    except:
        pass
    for i in range(1,5):
        try:
            Next_cmd.put(temp_list[i], block=False)
        except:
            pass
    #-------- end ----------#
    gui.after(200, task)
    time.sleep(0.01)

def sensor_update():
    #update temperature sensor
    try:
        if Comps.arduinos[0].state == False and Comps.buffer.blocked:
            Comps.arduinos[0].busy()
            Comps.Temp.poll() 
            buffer.current_device = Comps.Temp.device
            
    except:
        pass
    try:
        TEMP_send.send(Comps.Temp.get_last())
    except:
        TEMP_send.send(-1)
    gui.after(3000, sensor_update)
    time.sleep(0.01)


#---------- Webpage Commands ---------------#

#Global 
# Queues and pipes to share and communicate between threads
global web_frame, C_CMD, N_CMD, Kill_Conn, CMD_Conn, TEMP_Conn

# Grabs the latest frame and puts it onto a Queue for the webpage to read and display
def GUI_Server_Comms():
    global cam
    _, frame = cam.read() # reusing GUI cam instance
    try:
        Frames.put(frame, block=False)# puts frame on queue, only stores the last 5 frames
    except:
        pass
    if Kill_rev.poll(timeout=0.001): # polls the kill pipeline for new commands
        if Kill_rev.recv() == "kill": # if the command is kill
            print("The system has been KILLED")
            gui.Quit_application() # Quits all applications
    if rem_control.get() and CMD_rev.poll(timeout=0.001): # polls the kill pipeline for new commands
        command = CMD_rev.recv()
        print(command)
        if command == "Wash": # if the command is kill
            print("this is a Wash command")
            com.WASH(Comps,2,20)
        else:
            print("This is a process command")
            try:
                Out, A, B, C, D, Dose = command.split(',')
                Out = int(str(Out).replace("OUTPUT_",""))-1
                ent_P = []
                ent_P.append(float(A))
                ent_P.append(float(B))
                ent_P.append(float(C))
                ent_P.append(float(D))
                def Experiment(ent_P,Out, Dose):
                    tot_vol=0.0
                    for i in range(len(ent_P)):
                        try:
                            vol=ent_P[i]
                            if vol!=0.0:
                                try:
                                    Comps.pumps[i].poll()
                                except:
                                    print('this module does not exist')
                                    return -1
                                    
                                if Comps.pumps[i].LDS.state == False:
                                    # To do : Try 10 times before showing error box 
                                    print("Please fill The vessel of Input module {}".format(i+1))
                                    return -1
                                
                        except:
                            pass
                    for i in range(len(ent_P)):
                        try:
                            vol=ent_P[i]
                            tot_vol+=vol  
                            Comps.pumps[i].pump(vol)
                        except:
                            pass
                    try:
                        Comps.shutter.open()
                        Comps.mixer.mix()
                    except:pass
                    try:
                        time = Comps.radiate.D2T(float(Dose))
                        Comps.BLOCK(time)
                    except:pass
                    try:
                        Comps.mixer.stop()
                        Comps.shutter.close() 
                    except:pass

                    try:
                        output_index = Out
                        if 0<=output_index<=4:
                            com.valve_states(Comps.valves, 0)
                            Comps.extract.set_slot(output_index+1)
                            Comps.pumps[4].pump(-(tot_vol*2+10))
                            Comps.pumps[5].pump((tot_vol*2+30))
                        else:
                            com.valve_states(Comps.valves, Out-4)
                            Comps.pumps[4].pump(-(tot_vol*2+10))
                    except:
                        print('error ouptut')
                        pass
                    buffer.NOTIFY('Experiment Over')
                    return 0
                result = Experiment(ent_P, Out, Dose)
            except:
                pass
    elif CMD_rev.poll(timeout=0.001):
        CMD_rev.recv()
        #this should be a new comment for git 
    #Temp_Que.put(Comps.Temp.get_last())
    gui.after(200,GUI_Server_Comms) # executes it every 200ms 

app = Flask(__name__) #main web application

logged_in = list()
logged_in.append(['N/A','N/A'])

#main page of the website
@app.route("/", methods=['GET', 'POST']) # methods of interating and route address
def Main_page():
    global logged_in
    if not Check_Creds(request.remote_addr,logged_in,"None"):
        if request.form.get('Login') == 'Login':
            Username = request.form.get('User')
            Password = request.form.get('Pass')
            with open(os.path.join(path, 'static\\', 'credentials.csv'), newline='') as login:
                creds = list(csv.reader(login))
            for creds in creds:
                if creds[0] == Username:
                    if creds[1] == Password:
                        logged_in.append([request.remote_addr,creds[2]])
                                           
    if Check_Creds(request.remote_addr,logged_in,"None"):    
        # Reads all the current commands in the buffer and addes N/A if blank
        Next =[] # list of next 4 commands
        for i in range(0, 4):
            try: 
                Next.append(N_CMD.get(block = False)) # reads queue and adds commands to the list.
            except: 
                Next.append("N/A") # N/A if it is not available
        try: 
            Current = C_CMD.get(block = False) #Reads current command 
        except: 
            Current = "N/A"

        #To edit the webpage HTML file with the python data
        template = {
            'title': 'Arcadius Monitoring Page',
            'Current' : Current,
            'N1' : Next[0], #the next 4 commands
            'N2' : Next[1],
            'N3' : Next[2],
            'N4' : Next[3]
        }
        
        # Gets the request form the webpage about button presses
        if request.method == 'POST':
                if request.form.get('Kill') == 'Kill': # if the form item called Kill is clicked it reads the value
                    Kill_Conn.send("kill") # Sends kill command on kill pipe
                if request.form.get('Log Out') == 'Log Out':
                    print("Remove Login")
                    logged_in.remove([request.remote_addr,Op_mode(request.remote_addr)])
                    template = {
                        'address': '/',
                    }
                    return render_template('login.html', **template) #Renders webpage
                elif request.form.get('Capture') == 'Capture':
                    frame = web_frame.get()
                    file_name = str(datetime.datetime.now()).replace('.','_').replace('-','_').replace(':','_') + ".jpg"
                    cv2.imwrite(os.path.join(path, 'Captures\\', file_name), frame)
                else:
                    pass
        elif request.method == 'GET':
            pass
        return render_template('Main.html', **template) #Renders webpage
                            
    else:
        template = {
            'address': '/',
        }
        return render_template('login.html', **template) #Renders webpage
        
# generates videofeed from frame queue
def gen_frames(): 
    while True:
        try:
            frame = web_frame.get(block=False) # gets the most recent frames
            try:   
                ret, buffer = cv2.imencode('.jpg', frame) # encodes the frame and stores it in a buffer
                frame = buffer.tobytes() # converts to bytes
                yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  #Concat frame one by one and show result
            except:
                pass
        except:
            pass
           
#Renders a webpage fro pure video streaming which is linked to on main page
@app.route('/video_feed', methods=['GET', 'POST'])
def video_feed():
    global logged_in
    if not Check_Creds(request.remote_addr,logged_in,"None"):
        if request.form.get('Login') == 'Login':
            Username = request.form.get('User')
            Password = request.form.get('Pass')
            with open(os.path.join(path, 'static\\', 'login.csv'), newline='') as login:
                creds = list(csv.reader(login))
            for creds in creds:
                if creds[0] == Username:
                    if creds[1] == Password:
                        logged_in.append([request.remote_addr,creds[2]])
    if Check_Creds(request.remote_addr,logged_in,"None"):
        return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')            
    else:
        template = {
            'address': '/video_feed',
        }
        return render_template('login.html', **template) #Renders webpage
           
#Renders a webpage fro pure video streaming which is linked to on main page
@app.route('/command', methods=['GET', 'POST'])
def table():
    global logged_in
    if not Check_Creds(request.remote_addr,logged_in,"None"):
        if request.form.get('Login') == 'Login':
            Username = request.form.get('User')
            Password = request.form.get('Pass')
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static\\', 'login.csv'), newline='') as login:
                creds = list(csv.reader(login))
            for creds in creds:
                if creds[0] == Username:
                    if creds[1] == Password:
                        logged_in.append([request.remote_addr,creds[2]])
    if Check_Creds(request.remote_addr,logged_in,"None"):
        # Reads all the current commands in the buffer and addes N/A if blank
        Next =[] # list of next 4 commands
        for i in range(0, 4):
            try: 
                Next.append(N_CMD.get(block = False)) # reads queue and adds commands to the list.
            except: 
                Next.append("N/A") # N/A if it is not available
        try: 
            Current = C_CMD.get(block = False) #Reads current command 
        except: 
            Current = "N/A"
       
        try:
            temp_val = TEMP_Conn.recv()#random.randint(2400,2600)/100#T_Que.get(block = False)
        except:
            temp_val = 0

        #To edit the webpage HTML file with the python data
        template = {
            'Current' : Current,
            'N1' : Next[0], #the next 4 commands
            'N2' : Next[1],
            'N3' : Next[2],
            'N4' : Next[3],
            'temp': temp_val
        }
        return render_template('command.html', **template) #Renders webpage         
    else:
        template = {
            'address': '/command',
        }
        return render_template('login.html', **template) #Renders webpage

@app.route('/test')
def test():
    return render_template('test.html') #Renders webpage

#New control page
@app.route('/control', methods=['GET', 'POST'])
def control_page():
    global logged_in
    if not Check_Creds(request.remote_addr,logged_in,"None"):
        if request.form.get('Login') == 'Login':
            Username = request.form.get('User')
            Password = request.form.get('Pass')
            with open(os.path.join(path, 'static\\', 'credentials.csv'), newline='') as login:
                creds = list(csv.reader(login))
            for creds in creds:
                if creds[0] == Username:
                    if creds[1] == Password:
                        logged_in.append([request.remote_addr,creds[2]])

    if Check_Creds(request.remote_addr,logged_in,"None"):
        if Check_Creds(request.remote_addr,logged_in,"operator"):
            if request.method == 'POST':
                    if request.form.get('Kill') == 'Kill': # if the form item called Kill is clicked it reads the value
                        Kill_Conn.send("kill") # Sends kill command on kill pipe
                        return render_template('control.html')
                    if request.form.get('Log Out') == 'Log Out':
                        print("Remove Login")
                        logged_in.remove([request.remote_addr,Op_mode(request.remote_addr)])
                        template = {
                            'address': '/control',
                        }
                        return render_template('login.html', **template) #Renders webpage
                    elif request.form.get('Capture') == 'Capture':
                        frame = web_frame.get() 
                        file_name = str(datetime.datetime.now()).replace('.','_').replace('-','_').replace(':','_')  + ".jpg"
                        cv2.imwrite(os.path.join(path, 'Captures\\', file_name), frame)
                    elif  request.form.get('Start') == 'Start':
                        Command = (str(request.form.get('Output')) + "," + str(request.form.get('RA_mls')) + "," + str(request.form.get('RB_mls')) 
                                    + "," + str(request.form.get('RC_mls')) + "," + str(request.form.get('RD_mls')) + "," + str(request.form.get('Dosage')))
                        CMD_Conn.send(Command)
                        #CMD_Conn.send("PUMP")
                        return render_template('control.html')
                    elif  request.form.get('Wash') == 'Wash':
                        print("Wash")
                        CMD_Conn.send("Wash")
                        return render_template('control.html')
                    else:
                        pass
            elif request.method == 'GET':
                pass
            return render_template('control.html') 
        else:
            return render_template('Restricted.html')    
    else:
        template = {
            'address': '/control',
        }
        return render_template('login.html', **template) #Renders webpage
    
def Check_Creds(addr, logged_in, level):
    if level == "None":
        return any(request.remote_addr in User for User in logged_in)
    for User in logged_in:
        if User[0] == addr:
            if User[1] == level:
                return True
    return False

def Op_mode(addr):
    global logged_in
    for User in logged_in:
        if User[0] == addr:
            return User[1]
        
#---------- GUI Thread -------------#
def GUI():
    global gui, top 
    top = P_Login()
    top.mainloop()

#------- Webserver Thread ----------#
def Server(Q, L, N, K, P, T):
    global app, web_frame, C_CMD, N_CMD, Kill_Conn, CMD_Conn, TEMP_Conn
    web_frame = Q
    C_CMD = L
    N_CMD = N
    TEMP_Conn = T
    Kill_Conn = K
    CMD_Conn = P
    if __name__ == '__mp_main__':
        app.run(host='0.0.0.0', port = 80)

#Starts all the threads and pages.
if __name__ == "__main__":
    Frames = multiprocessing.Queue(5)
    Current_cmd = multiprocessing.Queue(1)
    Next_cmd = multiprocessing.Queue(4)
    TEMP_rev, TEMP_send = multiprocessing.Pipe(duplex = False)
    Kill_rev, Kill_send = multiprocessing.Pipe(duplex = False)
    CMD_rev, CMD_send = multiprocessing.Pipe(duplex = False)
    server = multiprocessing.Process(target = Server, args=(Frames, Current_cmd, Next_cmd, Kill_send, CMD_send, TEMP_rev))
    server.start()
    GUI()
    server.terminate()
    server.join()


