import os

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERNAME = os.getenv('USER', 'unknown_user')
STATIC_DIR = 'static'
TMP_DIR = os.path.join(STATIC_DIR, USERNAME + '_tmp')