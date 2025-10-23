import os
import uuid
import sys


DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DIR)
USERNAME = os.getenv('USER', 'unknown_user')
STATIC_DIR = 'static'
uuid_str = str(uuid.uuid4())
TMP_DIR = os.path.join(DIR, STATIC_DIR, USERNAME + '_' + uuid_str + '_tmp')