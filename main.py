import sys
import os
import tkinter as tk

# Add src/ to path so gui.py can find its imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ui'))

from gui import CompilerInterface


def main():
    root = tk.Tk()
    CompilerInterface(root)
    root.mainloop()


if __name__ == '__main__':
    main()
