"""
Test to check whether file imports are working

"""
import pandas as pd
import sys
from pathlib import Path

# Make sure the post dir is on Python's path
sys.path.append(str(Path(".").resolve()))
file_path = sys.path.append(str(Path(".").resolve()))
from src.modular_script_Quarto import dataframe_info
print(file_path)

def empty_function():
    print("Hellow")
    return