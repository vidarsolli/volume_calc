import getopt
from datetime import datetime
import time
import json
import zmq
#import tkinter
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from os import path
import shutil

processes = ([])
xref = ([])
context = None
description = None

gui = []
gui_config = {
    "conf_var": [
        "xp_centre",
        "yp_centre",
        "z_centre",
        "x_rot",
        "x_offset",
        "y_offset",
        "z_offset",
        "x_res",
        "y_res",
        "xp_dist",
        "yp_dist",
        "threshold_thresh",
        "threshold_max",
        "box_min_area"
    ],
    "label": [
        "X centre (px)",
        "Y centre (px)",
        "Dist to conveyor (m)",
        "Angle betw. UX X and Camera X",
        "X offset (m)",
        "Y offset (m)",
        "Z offset (m)",
        "X resolution (m)",
        "Y resolution (m",
        "X marked dist (px)",
        "Y marker dist (px)",
        "Threshold tresh",
        "Threshold max value",
        "Box min area (px)",
        ],
    "type": [
        "int",
        "int",
        "float",
        "float",
        "float",
        "float",
        "float",
        "float",
        "float",
        "int",
        "int",
        "int",
        "int",
        "int"
        ]
}

def save_parameters():
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
    with open(timestamp+".json", mode="w") as jsonFile:
        json.dump(cp, jsonFile, indent=4)

def update_parameters(*args):
    cp.pop("process_chain")
    process_chain = []
    for i in range(6):
        if str(process[i].get()) != "None":
            process_chain.append(str(process[i].get()))
    cp["process_chain"] = process_chain
    cp["max_depth"] = float(str(max_depth.get()))
    cp["min_depth"] = float(str(min_depth.get()))
    if int(depth_filter.get()) == 0:
        cp["depth_filter"] = "False"
    else:
        cp["depth_filter"] = "True"
    cp["canny_thresh1"] = int(str(canny_thresh1.get()))
    cp["canny_thresh2"] = int(str(canny_thresh2.get()))
    cp["blur_kernel_size"] = int(str(blur_kernel_size.get()))
    if int(best_fit.get()) == 0:
        cp["bounding_rect_best_fit"] = "False"
    else:
        cp["bounding_rect_best_fit"] = "True"
    cp["hough_pix_accuracy"] = int(str(pix_accuracy.get()))
    cp["hough_ang_accuracy"] = int(str(ang_accuracy.get()))
    cp["hough_min_length"] = int(str(min_length.get()))

    for var in gui:
        if var["type"] == "int":
            cp[var["conf_var"]] = int(str(var["var"].get()))
        if var["type"] == "float":
            cp[var["conf_var"]] = float(str(var["var"].get()))

    with open("config.json", mode="w") as jsonFile:
        json.dump(cp, jsonFile, indent=4)

    sock.send_pyobj("UPDATE")

def update_depth_filter():
    pass

def update_best_fit():
    pass

def select_process1(event):
    process[0].set(process_lbox[0].selection_get())
def select_process2(event):
    process[1].set(process_lbox[1].selection_get())
def select_process3(event):
    process[2].set(process_lbox[2].selection_get())
def select_process4(event):
    process[3].set(process_lbox[3].selection_get())
def select_process5(event):
    process[4].set(process_lbox[4].selection_get())
def select_process6(event):
    process[5].set(process_lbox[5].selection_get())


try:
    myOpts, args = getopt.getopt(sys.argv[1:], "i:")
except getopt.GetoptError as e:
    print(str(e))
    print("Usage: %s -i <path to base config file>" % sys.argv[0])
    sys.exit(2)
config_file = "config.json"
for o, a in myOpts:
    if o == '-i':
        config_file = a

print("Selected config file: ",config_file )

# Ooen the config file
with open(config_file) as file:
    cp = json.load(file)

sock = zmq.Context().socket(zmq.PUB)
sock.bind("tcp://127.0.0.1:60001")

root = Tk()
root.title("Image control")


mainframe = Frame(root, bd=6)
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Define all Widgets

processes = StringVar(value=cp["possible_processes"])

process_lbox = []
process_label = []
selected_process_label = []
for i in range(6):
    process_label.append(Label(mainframe, text="Process"+str(i+1)))
    process_lbox.append(Listbox(mainframe, listvariable=processes, height=1))
    selected_process_label.append(Label(mainframe, text="-"))

max_depth_label = Label(mainframe, text="Max depth")
max_depth = StringVar()
max_depth_entry = Entry(mainframe, textvariable=max_depth)
max_depth.set(str(cp["max_depth"]))
min_depth_label = Label(mainframe, text="Min depth")
min_depth = StringVar()
min_depth_entry = Entry(mainframe, textvariable=min_depth)
min_depth.set(str(cp["min_depth"]))
depth_filter = IntVar()
depth_filter.set(cp["depth_filter"] == "True")
depth_filter_cb = Checkbutton(mainframe, text="Depth filter", variable=depth_filter, command=update_depth_filter)

canny_thresh1_label = Label(mainframe, text="Canny Thresh1")
canny_thresh1 = StringVar()
canny_thresh1.set(str(cp["canny_thresh1"]))
canny_thresh1_entry = Entry(mainframe, textvariable=canny_thresh1)
canny_thresh2_label = Label(mainframe, text="Canny Thresh2")
canny_thresh2 = StringVar()
canny_thresh2.set(str(cp["canny_thresh2"]))
canny_thresh2_entry = Entry(mainframe, textvariable=canny_thresh2)

blur_kernel_size_label = Label(mainframe, text="Blur kernel size")
blur_kernel_size = StringVar()
blur_kernel_size.set(str(cp["blur_kernel_size"]))
blur_kernel_size_entry = Entry(mainframe, textvariable=blur_kernel_size)

best_fit = IntVar()
best_fit.set(cp["bounding_rect_best_fit"] == "True")
best_fit_cb = Checkbutton(mainframe, text="Bounding rect best fit", variable=best_fit, command=update_best_fit)

pix_accuracy_label = Label(mainframe, text="Hough pix accuracy")
pix_accuracy = StringVar()
pix_accuracy.set(str(cp["hough_pix_accuracy"]))
pix_accuracy_entry = Entry(mainframe, textvariable=pix_accuracy)
ang_accuracy_label = Label(mainframe, text="Hough ang accuracy")
ang_accuracy = StringVar()
ang_accuracy.set(str(cp["hough_ang_accuracy"]))
ang_accuracy_entry = Entry(mainframe, textvariable=ang_accuracy)
min_length_label = Label(mainframe, text="Hough min length")
min_length = StringVar()
min_length.set(str(cp["hough_min_length"]))
min_length_entry = Entry(mainframe, textvariable=min_length)

first_row = 12
for i in range(len(gui_config["conf_var"])):
    tmp = {}
    tmp["conf_var"] = gui_config["conf_var"][i]
    tmp["type"] = gui_config["type"][i]
    tmp["var"] = StringVar()
    tmp["label"] = Label(mainframe, text=gui_config["label"][i])
    tmp["var"].set(str(cp[gui_config["conf_var"][i]]))
    tmp["entry"] = Entry(mainframe, textvariable=tmp["var"])
    tmp["label"].grid(column=1+i%2*3, row=first_row+int(i/2), columnspan=1, sticky=W, pady=5, padx=5)
    tmp["entry"].grid(column=2+i%2*3, row=first_row+int(i/2), columnspan=1, sticky=W, pady=5, padx=5)
    gui.append(tmp)

update_button = Button(mainframe, text="Update", command=update_parameters)
save_button = Button(mainframe, text="Save", command=save_parameters)


# Position all Widgets
for i in range(6):
    process_label[i].grid(column=1, row=i+2, sticky=W, pady=5, padx=5)
    process_lbox[i].grid(column=2, row=i+2, columnspan=1, sticky=W, pady=5, padx=5)
    selected_process_label[i].grid(column=3, row=i+2, columnspan=1, sticky=W, pady=5, padx=5)

max_depth_label.grid(column=4, row=2, columnspan=1, sticky=W, pady=5, padx=5)
max_depth_entry.grid(column=5, row=2, columnspan=1, sticky=W, pady=5, padx=5)
min_depth_label.grid(column=4, row=3, columnspan=1, sticky=W, pady=5, padx=5)
min_depth_entry.grid(column=5, row=3, columnspan=1, sticky=W, pady=5, padx=5)
depth_filter_cb.grid(column=4, row=4, columnspan=1, sticky=W, pady=5, padx=5)

canny_thresh1_label.grid(column=4, row=5, columnspan=1, sticky=W, pady=5, padx=5)
canny_thresh1_entry.grid(column=5, row=5, columnspan=1, sticky=W, pady=5, padx=5)
canny_thresh2_label.grid(column=4, row=6, columnspan=1, sticky=W, pady=5, padx=5)
canny_thresh2_entry.grid(column=5, row=6, columnspan=1, sticky=W, pady=5, padx=5)


blur_kernel_size_label.grid(column=4, row=7, columnspan=1, sticky=W, pady=5, padx=5)
blur_kernel_size_entry.grid(column=5, row=7, columnspan=1, sticky=W, pady=5, padx=5)

best_fit_cb.grid(column=1, row=8, columnspan=1, sticky=W, pady=5, padx=5)

pix_accuracy_label.grid(column=1, row=9, columnspan=1, sticky=W, pady=5, padx=5)
pix_accuracy_entry.grid(column=2, row=9, columnspan=1, sticky=W, pady=5, padx=5)
ang_accuracy_label.grid(column=1, row=10, columnspan=1, sticky=W, pady=5, padx=5)
ang_accuracy_entry.grid(column=2, row=10, columnspan=1, sticky=W, pady=5, padx=5)
min_length_label.grid(column=1, row=11, columnspan=1, sticky=W, pady=5, padx=5)
min_length_entry.grid(column=2, row=11, columnspan=1, sticky=W, pady=5, padx=5)


update_button.grid(column=1, row=20, columnspan=1, sticky=W, pady=5, padx=5)
save_button.grid(column=7, row=20, columnspan=1, sticky=W, pady=5, padx=5)

process = []
for i in range(6):
    process.append(StringVar())
    if len(cp["process_chain"])>i:
        process[i].set(cp["process_chain"][i])
    else:
        process[i].set("None")
    selected_process_label[i]['textvariable'] = process[i]

process_lbox[0].bind('<Double-1>', select_process1)
process_lbox[1].bind('<Double-1>', select_process2)
process_lbox[2].bind('<Double-1>', select_process3)
process_lbox[3].bind('<Double-1>', select_process4)
process_lbox[4].bind('<Double-1>', select_process5)
process_lbox[5].bind('<Double-1>', select_process6)

root.mainloop()