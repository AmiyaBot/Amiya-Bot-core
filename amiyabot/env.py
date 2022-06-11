import os

if not os.path.exists('log'):
    os.makedirs('log')

os.environ['QQBOT_LOG_PATH'] = os.path.join(os.getcwd(), 'log', '%(name)s.log')
os.environ['QQBOT_LOG_PRINT_FORMAT'] = '%(asctime)s [%(levelname)s] %(message)s'
