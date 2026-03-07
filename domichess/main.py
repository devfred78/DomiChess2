# domichess/main.py

import multiprocessing
from domichess.ui.main_window import MainWindow

def main():
    """
    Main function to run the DomiChess application.
    """
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    # This is crucial for multiprocessing to work correctly when frozen by PyInstaller.
    # It prevents child processes from re-executing the main application code.
    multiprocessing.freeze_support()
    main()
