import itertools
import os
import random
import time
import uuid
import xml.etree.ElementTree

import requests
import timeout_decorator
from PIL import Image


def parse_proxy():
    proxy_file_path = os.path.join(os.path.dirname(__file__), 'proxy')
    proxy_list = []
    with open(proxy_file_path, 'r') as f:
        for line in f:
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            proxy_list.append('https://{}:{}'.format(parts[0], parts[1]))
    random.shuffle(proxy_list)
    return proxy_list


parsed_proxies = parse_proxy()
strange_errors_count = 0
total_uploads_per_session = 0


user_agents = itertools.cycle((
    # 'FPUploader',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
    'Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)',
))


def upload_file_to_fastpic(file_path, tmp_dir, proxy=None):
    """ Set proxy='' to connect without proxy. """
    global total_uploads_per_session, strange_errors_count
    print(file_path)

    if proxy is None:
        proxy = get_next_proxy()

    img = Image.open(file_path)
    width, height = img.size
    size_limit = 25*1000*1000
    if (width * height) >= size_limit:
        width_old, height_old = img.size
        while (width * height) > size_limit:
            width = int(width * 0.9)
            height = int(height * 0.9)
        new_path = os.path.join(tmp_dir, '{}.jpg'.format(uuid.uuid4()))
        img.thumbnail((width, height), Image.ANTIALIAS)
        img.save(new_path, "JPEG", quality=95)
        print('resize width and height for {}. Has {}x{}={} Mp. New {}x{}={} Mp.'.
              format(file_path, width_old, height_old, width_old*height_old/(1000*1000),
                     width, height, width*height/(1000*1000)))
        return upload_file_to_fastpic(new_path, tmp_dir, proxy)

    size = os.path.getsize(file_path)
    if size >= 10 * 1024 * 1024:
        new_path = os.path.join(tmp_dir, '{}.jpg'.format(uuid.uuid4()))
        Image.open(file_path).save(new_path, "JPEG", quality=90)
        print('resize {}. Old size {}. New size {}'.format(file_path, size, os.path.getsize(new_path)))
        return upload_file_to_fastpic(new_path, tmp_dir, proxy)

    with open(file_path, 'rb') as file:
        try:
            response = get_fastpic_response(file, proxy)
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ProxyError, requests.exceptions.ReadTimeout,
                requests.exceptions.SSLError):
            print('Possible proxy is dead. Switch to next one')
            proxy = get_next_proxy()
            return upload_file_to_fastpic(file_path, tmp_dir, proxy)
        except timeout_decorator.TimeoutError:
            print('Timeout uploading. Switch to next proxy')
            proxy = get_next_proxy()
            return upload_file_to_fastpic(file_path, tmp_dir, proxy)

        if response.status_code != 200:
            print(response)
            print(response.text)
            strange_errors_count += 1
            if strange_errors_count > 20:
                raise Exception('Some error with loading to fastpic')
            time.sleep(20)
            return upload_file_to_fastpic(file_path, tmp_dir, proxy)
        xml_tree = xml.etree.ElementTree.fromstring(response.text)
        error = xml_tree.find('error').text
        if error:
            print('No result cause error: {}'.format(error))

            if 'You are reached limit per a day uploads' in error:
                proxy = get_next_proxy()
                return upload_file_to_fastpic(file_path, tmp_dir, proxy)

            if 'Вы не загрузили файлы' in error:
                return None

            strange_errors_count += 1
            if strange_errors_count > 20:
                raise Exception('Some error with loading to fastpic')
            time.sleep(20)
            return upload_file_to_fastpic(file_path, tmp_dir, proxy)

        total_uploads_per_session += 1
        print('Total uploaded per session: {}'.format(total_uploads_per_session))

        return xml_tree.find('thumbpath').text, xml_tree.find('viewurl').text


@timeout_decorator.timeout(5 * 60, use_signals=False)
def get_fastpic_response(file, proxy):
    user_agent = next(user_agents)
    response = requests.post('https://fastpic.ru/upload?api=1',
                             headers={'User-Agent': user_agent},
                             data={
                                 'method': 'file',
                                 'check_thumb': 'no',
                                 'uploading': '1',
                             },
                             files={'file1': file},
                             proxies={'https': proxy})
    return response


def check_proxy_is_alive(proxy_str):
    try:
        response = requests.get('https://fastpic.ru', proxies={'https': proxy_str}, timeout=2)
        if response.status_code == 200:
            return True
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ProxyError, requests.exceptions.ReadTimeout,
            requests.exceptions.SSLError):
        pass
    return False


@timeout_decorator.timeout(60 * 10, use_signals=False)
def get_next_proxy():
    checked_alive_proxy = None
    for i in range(100 * len(parsed_proxies)):
        proxy_candidate = random.choice(parsed_proxies)
        proxy_is_alive = check_proxy_is_alive(proxy_candidate)
        if proxy_is_alive:
            checked_alive_proxy = proxy_candidate
            break
    if checked_alive_proxy is None:
        raise Exception("Can't connect with any proxy")
    print('Switch proxy to {}'.format(checked_alive_proxy))
    return checked_alive_proxy


if __name__ == '__main__':
    print(get_next_proxy())
    print(get_next_proxy())
    print(get_next_proxy())

    print()
    for p in parse_proxy():
        print(p, check_proxy_is_alive(p))

