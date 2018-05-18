# fastpic


## Description


These scripts help to prepare and upload pictures to fastpic image-hosting.

Main script is called **process_images.py**. It helps to automatize following actions:

1. Prepare images miniatures. If there is video file in folder, script will generate screenlist and some full-size frames.

2. Get some random images. Collect cover images.

3. Upload images from n.1 and n.2 to fastpic. To increase daily limit, proxy are used.

4. Organize links from n.3 to `[spoiler]` tags (according folders names).

5. Write result to file. If there are too much lines (for forum message), file will be separated to parts.


There are some additional scripts:

1. **unpack_zip.py** - extracts each archive in separate folder.

2. **upload\_from\_folder.py** - uploads images from folder to fastpic.


## Usage


To run main script (**process_images.py**), put folders to process into **_root\_folders\_set** variable.


## System requirements


* Linux (it is possible to fix some OS specific calls to run script on Windows, but it is not interesting for me)

* programs:
    * Python 3
    * ImageMagick (_montage_ is part of ImageMagick)
    * ffmpeg
    * unzip

* Python 3 packages:
    * Pillow
    * joblib
    * requests
    * timeout_decorator

