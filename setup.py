import os
import json
import setuptools

from urllib import request


def ver_num(_v):
    num = int(_v.replace('.', ''))
    if num < 1000:
        num *= 10
    return num


pypi = json.loads(request.urlopen('https://pypi.python.org/pypi/amiyabot/json').read())
v_list = {ver_num(v): v for v in pypi['releases'].keys()}
s_list = sorted(v_list)
latest = v_list[s_list[-1]]

print(f'latest: {latest}')

latest = latest.split('.')
latest[-1] = str(int(latest[-1]) + 1)

new_version = '.'.join(latest)
release_new = input(f'new?: {new_version} (Y/n)')

if not (not release_new or release_new.lower() == 'y'):
    new_version = ''

with open('README.md', mode='r', encoding='utf-8') as md:
    description = md.read()

with open('requirements.txt', mode='r', encoding='utf-8') as req:
    requirements = sorted(req.read().strip('\n').split('\n'))

with open('requirements.txt', mode='w', encoding='utf-8') as req:
    req.write('\n'.join(requirements))

data_files = []
for root, dirs, files in os.walk('amiyabot/_assets'):
    for item in files:
        data_files.append(os.path.join(root, item))

setuptools.setup(
    name='amiyabot',
    version=new_version or input('version: '),
    author='vivien8261',
    author_email='826197021@qq.com',
    url='https://www.amiyabot.com',
    license='MIT Licence',
    description='简洁高效的异步 Python QQ 频道机器人框架',
    long_description=description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(include=['amiyabot', 'amiyabot.*']),
    data_files=[('amiyabot', data_files)],
    include_package_data=True,
    python_requires='>=3.7',
    install_requires=requirements
)

# python setup.py bdist_wheel
