import os
import subprocess

root_folder = '/path/to/root/folder'


""" This script will extract each archive in separate folder. """


folders_to_process = []
for root, dirs, files in os.walk(root_folder):
    for folder in dirs:
        folders_to_process.append(os.path.join(root, folder))

for folder in sorted(folders_to_process):
    print(folder)
    subprocess.call('''for f in *.zip; do unzip -d "${f%*.zip}" "$f"; done''', cwd=folder, shell=True)

