import argparse
from urllib.parse import urlparse

import requests

parser = argparse.ArgumentParser()
parser.add_argument('url', type=str, help='url to check')
args = parser.parse_args()

url = args.url
parsed_url = urlparse(url)
prefix = (parsed_url.netloc + parsed_url.path).replace('/', '_')

print("[INFO] Getting Screenshots...")
# subprocess.run(["webscreenshot", url, '-v'])
# os.replace(glob('screenshots/http*.png')[0], f'screenshots/{prefix}_original.png')

response = requests.get("https://render-tron.appspot.com/screenshot/" + url, stream=True)

if response.status_code == 200:
    with open(f'screenshots/{prefix}_original.png', 'wb') as file:
        for chunk in response:
            file.write(chunk)

print("[INFO] Startup Completed")
