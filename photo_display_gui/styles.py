import tkinter.ttk as ttk

class _StyleGenerator:
    def generate(self):
        styles = ttk.Style()
        styles.configure("DisplayWindow.TFrame", background="black")
        styles.configure("Image.DisplayWindow.TLabel", background="black")
        styles.configure("TitleBar.TFrame", background="grey")
        styles.configure("TitleBar.TLabel", background="grey", foreground="white")

STYLES = _StyleGenerator()
