import datetime
import os
import random
import shutil
import subprocess
import tempfile

from joblib import Parallel, delayed
from PIL import Image
from fastpic_upload import upload_file_to_fastpic


_n_jobs_for_resize = 5
_n_jobs_for_montage = 3
_n_jobs_for_upload = 5
_n_full_size_in_folder = 3
_video_out_in_same_folder = False

_root_folders_set = (
    '/path/to/root/folder',
)
_skip_out_generation = (
    '',
)
_cover_indicators = ('cover.', '_lg.jpg', '- video.jpg')
_cover_key = '_covers'
_out_indicators = (' out.jpg', 'SLICKSLICED_', 'ContactSheet')
_video_indicators = (' - video', 'Videos')


def resize_one_file(file_path, dir_for_resized):
    try:
        if file_path.split('.')[-1].lower() not in ('jpg', 'jpeg', 'bmp', 'png'):
            return None
        new_path = os.path.join(dir_for_resized, os.path.split(file_path)[-1])
        img = Image.open(file_path)
        width, height = img.size
        size_limit = 200 * 200
        if (width * height) >= size_limit:
            while (width * height) > size_limit:
                width = int(width * 0.9)
                height = int(height * 0.9)
            img.thumbnail((width, height), Image.ANTIALIAS)
            img.save(new_path, "JPEG", quality=100)
        else:
            shutil.copy(file_path, new_path)
        return new_path
    except Exception as ex:
        print('Problem with {}'.format(file_path))
        print(ex)
        return None


def resize_root(root_folder, root_folder_resized):
    for root, dirs, files in os.walk(root_folder):
        dir_for_resized = root.replace(root_folder, root_folder_resized)
        os.makedirs(dir_for_resized, exist_ok=True)
        print('resize', root)
        Parallel(n_jobs=_n_jobs_for_resize, backend='threading')(
            delayed(resize_one_file)(os.path.join(root, file), dir_for_resized) for file in files)


def call_montage_one(working_dir, output_title, output_path):
    subprocess.call('''montage -label '%f' * -tile 6x -shadow -geometry '250x250+5+5' -title "{}" "{}"'''
                    .format(output_title, output_path), cwd=working_dir, shell=True)
    print(output_path)


def call_montage(root_folder, root_for_montage_out):
    montage_tasks = []
    for root, dirs, files in os.walk(root_folder):
        if len(files) < 10:
            continue
        output_title = os.path.split(root)[-1]
        output_file_name = '{}{}'.format(os.path.split(root)[-1], _out_indicators[0])
        output_path = (os.path.join(root, output_file_name)).replace(root_folder, root_for_montage_out)
        montage_tasks.append((root, output_title, output_path))

    Parallel(n_jobs=_n_jobs_for_montage, backend='threading')(
        delayed(call_montage_one)(*montage_task) for montage_task in sorted(montage_tasks, key=lambda x: x[0]))


def file_is_cover(file_name, folder_path):
    if any(cover_indicator in file_name.lower() for cover_indicator in _cover_indicators):
        return True
    if '{}.jpg'.format(os.path.split(folder_path)[-1]) == file_name:
        return True
    return False


def prepare_pics_to_process(root_folder):
    result = {}
    for root, dirs, files in os.walk(root_folder):
        files_to_process = set()
        for i in range(0, 40):
            if len(files_to_process) >= _n_full_size_in_folder:
                break
            if not len(files):
                break
            file = files[random.randrange(len(files))]
            if any(out_indicator in file for out_indicator in _out_indicators):
                continue
            if file.split('.')[-1].lower() not in ('jpg', 'jpeg', 'bmp', 'png'):
                continue
            if file_is_cover(file, root):
                continue
            files_to_process.add(file)

        if not len(files_to_process):
            continue

        result_key = root.replace(root_folder, '').lstrip('/')
        result[result_key] = []

        for file in sorted(files_to_process):
            result[result_key].append(os.path.join(root, file))

        if any(video_indicator in root for video_indicator in _video_indicators):
            result[result_key] = []

        for file in sorted(files):
            if file.split('.')[-1].lower() not in ('jpg', 'jpeg', 'bmp', 'png'):
                continue
            file_path = os.path.join(root, file)
            if any(out_indicator in file for out_indicator in _out_indicators):
                result[result_key].append(file_path)
                continue
            if file_is_cover(file, root):
                if _cover_key not in result:
                    result[_cover_key] = []
                result[_cover_key].append(file_path)
                result[result_key].insert(0, file_path)
                continue
            if any(video_indicator in root for video_indicator in _video_indicators):
                result[result_key].append(file_path)
    return result


def process_pic_array(result_key, pic_array, tmp_dir):
    sub_result = []
    for file_path in pic_array:
        res = upload_file_to_fastpic(file_path, tmp_dir)
        if res is None:
            continue
        pic_url, pic_link = res
        print(pic_url)
        if not pic_url:
            continue
        sub_result.append((pic_url, pic_link))
    return result_key, sub_result


def upload_to_fastpic_parallel(pics_to_upload):
    total_for_upload = 0
    for key in pics_to_upload:
        total_for_upload += len(pics_to_upload[key])
    print('Need upload {} photo'.format(total_for_upload))

    result = {}
    tmp_dir = tempfile.mkdtemp()
    try:
        sub_results = Parallel(n_jobs=_n_jobs_for_upload, backend='threading')(
            delayed(process_pic_array)(key, pics_to_upload[key], tmp_dir) for key in sorted(pics_to_upload))

        for sub_result in sub_results:
            result[sub_result[0]] = sub_result[1]
    finally:
        shutil.rmtree(tmp_dir)
    return result


def print_result_to_file(result, result_file_path):
    with open(result_file_path, 'w', encoding='utf8', newline='') as codes_file:
        if _cover_key in result:
            covers = result.pop(_cover_key)
            codes_file.write('[spoiler="Covers"]')
            codes_file.write(os.linesep)
            for url, link in covers:
                codes_file.write('[url={}][img]{}[/img][/url]'.format(link, url))
            codes_file.write(os.linesep)
            codes_file.write('[/spoiler]')

        codes_file.write('[spoiler="Скриншоты"]')
        codes_file.write(os.linesep)
        for result_key in sorted(result):
            codes_file.write('[spoiler="{}"]'.format(result_key))
            codes_file.write(os.linesep)
            for url, link in result[result_key]:
                codes_file.write('[url={}][img]{}[/img][/url]'.format(link, url))
            codes_file.write(os.linesep)
            codes_file.write('[/spoiler]')
            codes_file.write(os.linesep)
        codes_file.write('[/spoiler]')


def collect_lines(result):
    lines = []
    for result_key in sorted(result):
        line = ''
        line += '[spoiler="{}"]'.format(result_key)
        for url, link in result[result_key]:
            line += '[url={}][img]{}[/img][/url]'.format(link, url)
        line += '[/spoiler]'
        lines.append(line)
    return lines


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def print_result_to_file_with_parts(result, result_file_path):
    lines = collect_lines(result)
    current_file = 0
    for lines_set in batch(lines, 150):
        current_file += 1
        file_path = '{}_part_{}.txt'.format(result_file_path.rsplit('.', 1)[0], current_file)
        with open(file_path, 'w', encoding='utf8', newline='') as codes_file:
            codes_file.write('[spoiler="Скриншоты часть {}"]'.format(current_file))
            codes_file.write(os.linesep)
            for line in lines_set:
                codes_file.write(line)
                codes_file.write(os.linesep)
            codes_file.write(os.linesep)
            codes_file.write('[/spoiler]')


def prepare_video_out(root_folder):
    for root, dirs, files in os.walk(root_folder):
        for file in sorted(files):
            if file.split('.')[-1].lower() not in ('mkv', 'avi', 'mov', 'wmv'):
                continue
            file_path = os.path.join(root, file)

            if _video_out_in_same_folder:
                working_dir = root
            else:
                working_dir = '{}_screens'.format(file_path)
                os.makedirs(working_dir, exist_ok=True)

            print(file_path, 'frames')
            subprocess.call('''ffmpeg -i "{}" -vf fps=1/{} frame%04d.jpg -hide_banner '''
                            .format(file_path, random.randint(50, 70)), cwd=working_dir, shell=True,
                            stderr=subprocess.DEVNULL)

            print(file_path, 'screens')
            slickslice_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slickslice-0.9.sh')
            subprocess.call('''{} -x "{}"'''.format(slickslice_path, file_path), cwd=working_dir, shell=True,
                            stdout=subprocess.DEVNULL)


def main():
    for root_folder in _root_folders_set:
        if root_folder not in _skip_out_generation:
            root_folder_resized = '{}_resized'.format(root_folder)
            resize_root(root_folder, root_folder_resized)
            call_montage(root_folder_resized, root_folder)
            shutil.rmtree(root_folder_resized)

            prepare_video_out(root_folder)

        pics_to_upload = prepare_pics_to_process(root_folder)
        result = upload_to_fastpic_parallel(pics_to_upload)
        print_result_to_file(result, os.path.join(root_folder, 'result_codes.txt'))
        print_result_to_file_with_parts(result, os.path.join(root_folder, 'result_codes.txt'))


if __name__ == '__main__':
    started = datetime.datetime.now()
    print(started, 'started')
    main()
    finished = datetime.datetime.now()
    print(finished, 'all done in', finished - started)


