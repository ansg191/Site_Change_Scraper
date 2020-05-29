import subprocess
from glob import glob
import os

# url = "https://www.dmv.ca.gov/portal/dmv/dmv/appointments"
url = '127.0.0.1'

print("[INFO] Getting Screenshots...")
subprocess.run(["webscreenshot", url, '-v'])
os.replace(glob('screenshots/http*.png')[0], 'screenshots/original.png')
print("[INFO] Startup Completed")
