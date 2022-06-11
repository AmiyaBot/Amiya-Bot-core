import setuptools

with open('README.md', 'r', encoding='utf-8') as md:
    description = md.read()

setuptools.setup(
    name='amiyabot',
    version='1.0.5',
    author='vivien8261',
    author_email='826197021@qq.com',
    url='https://gitee.com/vivien8261/amiya-bot-core',
    license='MIT Licence',
    description='快速构建 QQ 频道机器人',
    long_description=description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(include=['amiyabot', 'amiyabot.*']),
    data_files=[('amiyabot', ['amiyabot/assets/font/HarmonyOS_Sans_SC.ttf'])],
    include_package_data=True,
    python_requires='>=3.7',
    install_requires=[
        'pillow~=9.1.1',
        'aiohttp~=3.7.4.post0',
        'jieba~=0.42.1',
        'peewee~=3.14.10',
        'playwright~=1.22.0',
        'pymysql~=1.0.2',
        'pyyaml~=6.0',
        'qq-bot~=0.8.5',
        'requests~=2.27.1',
        'zhon~=1.1.5'
    ]
)
