import tkinter.ttk as ttk

class _StyleGenerator:
    def generate(self):
        styles = ttk.Style()
        styles.configure("TFrame", background="#64676E")
        styles.configure("TLabel", background="#64676E")
        styles.configure("TButton", background="#2E3033", foreground="white")
        styles.configure("DisplayWindow.TFrame", background="#000000")
        styles.configure("Image.DisplayWindow.TLabel", background="#000000")
        styles.configure("TitleBar.TFrame", background="#2E3033")
        styles.configure("TitleBar.TLabel", background="#2E3033", foreground="white")
        styles.configure("TitleBar.TButton", background="#64676E", foreground="white")
        styles.configure("TButton", font="DefaultFont")

STYLES = _StyleGenerator()
