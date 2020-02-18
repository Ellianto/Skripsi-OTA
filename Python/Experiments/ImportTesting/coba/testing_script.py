from pathlib import Path

def show_main_dir():
    return Path(__file__).parent.parent.absolute()

def show_file():
    return __file__

def show_globals():
    return globals()
