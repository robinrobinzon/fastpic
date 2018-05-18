import datetime
import os
import shutil
import tempfile

from joblib import Parallel, delayed
from fastpic_upload import upload_file_to_fastpic


_n_jobs_for_upload = 20

_root_folders_set = (
    '/path/to/folder',
)
_spoiler_for_each_file = True


def process_one_pic(result_key, pic_path, tmp_dir):
    pic_url, pic_link = upload_file_to_fastpic(pic_path, tmp_dir)
    print(pic_url)
    return result_key, (pic_url, pic_link)


def upload_from_folder(folder_path):
    pics_to_upload = {}

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.split('.')[-1] not in ('jpg', 'jpeg', 'bmp', 'png'):
                continue
            file_path = os.path.join(root, file)
            pics_to_upload[file] = file_path

    print(pics_to_upload)
    print('Need upload {} photo'.format(len(pics_to_upload)))

    result = {}
    tmp_dir = tempfile.mkdtemp()
    try:
        sub_results = Parallel(n_jobs=_n_jobs_for_upload, backend='threading')(
            delayed(process_one_pic)(key, pics_to_upload[key], tmp_dir) for key in sorted(pics_to_upload))

        for sub_result in sub_results:
            result[sub_result[0]] = sub_result[1]
    finally:
        shutil.rmtree(tmp_dir)
    return result


def print_result_to_file(result, result_file_path):
    with open(result_file_path, 'w', encoding='utf8', newline='') as codes_file:
        codes_file.write('[spoiler="Скриншоты"]')
        codes_file.write(os.linesep)
        codes_file.write(os.linesep)
        for result_key in sorted(result):
            if _spoiler_for_each_file:
                codes_file.write('[spoiler="{}"]'.format(result_key))
                codes_file.write(os.linesep)
            url, link = result[result_key]
            codes_file.write('[url={}][img]{}[/img][/url]'.format(link, url))
            if _spoiler_for_each_file:
                codes_file.write(os.linesep)
                codes_file.write('[/spoiler]')
                codes_file.write(os.linesep)
        codes_file.write(os.linesep)
        codes_file.write('[/spoiler]')


def main():
    for root_folder in _root_folders_set:
        result = upload_from_folder(root_folder)
        print_result_to_file(result, os.path.join(root_folder, 'result_codes.txt'))


if __name__ == '__main__':
    started = datetime.datetime.now()
    print(started, 'started')
    main()
    finished = datetime.datetime.now()
    print(finished, 'all done in', finished - started)


