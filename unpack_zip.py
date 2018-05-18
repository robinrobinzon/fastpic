import os
import subprocess

_root_folder = '/path/to/root/folder'


""" This script will extract each zip archive in separate folder. """


def extract_zip(root_folder):
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            file_name, file_extension = file.rsplit('.', 1)
            if 'zip' != file_extension:
                continue
            file_path = os.path.join(root, file)
            print(file_path)
            subprocess.call('''unzip -u -d "{}" "{}"'''.format(file_name, file_path), cwd=root, shell=True,
                            stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    extract_zip(_root_folder)

