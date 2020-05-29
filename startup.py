import subprocess
from glob import glob
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('url', type=str, help='url to check')
args = parser.parse_args()

url = args.url

print("[INFO] Getting Screenshots...")
subprocess.run(["webscreenshot", url, '-v'])
os.replace(glob('screenshots/http*.png')[0], 'screenshots/original.png')
print("[INFO] Startup Completed")
