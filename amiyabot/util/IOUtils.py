import os
import re
import zipfile

from typing import Optional, List


def create_dir(path: str, is_file: bool = False):
    if is_file:
        path = os.path.dirname(path)

    if path and not os.path.exists(path):
        os.makedirs(path)

    return path


def support_gbk_zip(zip_file: zipfile.ZipFile):
    name_to_info = zip_file.NameToInfo
    for name, info in name_to_info.copy().items():
        real_name = name.encode('cp437').decode('gbk')
        if real_name != name:
            info.filename = real_name
            del name_to_info[name]
            name_to_info[real_name] = info

    return zip_file


def extract_zip(file: str, dest: str, overwrite: bool = False, ignore: Optional[List[re.Pattern]] = None):
    create_dir(dest)
    with zipfile.ZipFile(file) as pack:
        for pack_file in support_gbk_zip(pack).namelist():
            dest_file = os.path.join(dest, pack_file)
            if ignore:
                for reg in ignore:
                    if re.search(reg, dest_file):
                        continue

            if os.path.exists(dest_file) and not overwrite:
                continue
            pack.extract(pack_file, dest)
