import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import os
from gui.app import ZooApp
from data.data_loader import load_animals
from data.predefined_loader import load_predefined_projects

def main():

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    animals_path = os.path.join(BASE_DIR, "data", "Animals.xlsx")
    predefined_path = os.path.join(BASE_DIR, "data", "Predefined projects.xlsx")

    # Data loading happens before any window exists, so a bad Excel file
    # used to crash with a console traceback and no visible window at all
    # (invisible in a windowed/packaged build). Show it in a message box
    # instead.
    try:
        animals = load_animals(animals_path)
        predefined = load_predefined_projects(predefined_path)
    except Exception as e:
        error_root = tk.Tk()
        error_root.withdraw()
        messagebox.showerror("Zoo Generator - failed to load data", str(e))
        error_root.destroy()
        return

    root = ctk.CTk()
    root.geometry("1800x900")
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ZooApp(root, animals, predefined)
    root.mainloop()

if __name__ == "__main__":
    main()