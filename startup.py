import subprocess
from glob import glob
import os
import argparse
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument('url', type=str, help='url to check')
args = parser.parse_args()

url = args.url
parsed_url = urlparse(url)
prefix = (parsed_url.netloc + parsed_url.path).replace('/', '_')

print("[INFO] Getting Screenshots...")
subprocess.run(["webscreenshot", url, '-v'])
os.replace(glob('screenshots/http*.png')[0], f'screenshots/{prefix}_original.png')
print("[INFO] Startup Completed")
