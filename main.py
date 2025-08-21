# main.py

import sys
import os
# Import the FGDApplication class from fgd_gui.py
from fgd_gui import FGDApplication

def resource_path(relative_path):
  if hasattr(sys, '_MEIPASS'):
      base_path = sys._MEIPASS
  else:
      base_path = os.path.abspath(".")

  return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    # Create an instance of the FGDApplication and run its main loop
    app = FGDApplication()
    app.iconbitmap(resource_path("icon.ico"))
    app.mainloop()