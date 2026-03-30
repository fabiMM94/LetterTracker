import pandas as pd

import tkinter as tk
from tkinter import ttk
import pandas as pd


import dtale


if __name__ == "__main__":
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    d = dtale.show(df)
    d.open_browser()
