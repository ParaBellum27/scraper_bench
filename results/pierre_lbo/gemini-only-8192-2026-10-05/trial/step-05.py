import os

print("Files in workspace:", os.listdir("."))
if os.path.exists("inputs"):
    print("Files in inputs:", os.listdir("inputs"))
