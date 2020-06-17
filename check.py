import argparse
import logging as log
import mimetypes
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from urllib.parse import urlparse

import cv2
import numpy as np
import pytz
import requests
from skimage.measure import compare_ssim

parser = argparse.ArgumentParser()
parser.add_argument('url', type=str, help='url to check')
parser.add_argument('sender', type=str, help='sender email')
parser.add_argument('password', type=str, help='email password')
parser.add_argument('recipients', type=str, nargs='+', help='Recipient List')
parser.add_argument('--server-url', type=str, default='smtp.mail.yahoo.com')
parser.add_argument('--port', type=int, default=465)
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-l', '--log', type=str, default='log.txt')
parser.add_argument('--time-zone', type=str, default='America/Los_Angeles')
args = parser.parse_args()

if args.verbose:
    log.basicConfig(format="[%(levelname)s] %(message)s", level=log.DEBUG)
else:
    log.basicConfig(format="[%(levelname)s] %(message)s")

url = args.url
parsed_url = urlparse(url)
prefix = (parsed_url.netloc + parsed_url.path).replace('/', '_')

sender = args.sender
server_url = args.server_url
port = args.port
password = args.password
recipient_list = args.recipients

tz = pytz.timezone(args.time_zone)
time = datetime.now(tz).strftime('%Y-%m-%d %H:%M')


def non_max_suppression_slow(boxes, overlap_thresh):
    if len(boxes) == 0:
        return []
    pick = []

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)

    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        suppress = [last]

        for pos in range(0, last):
            j = idxs[pos]

            xx1 = max(x1[i], x1[j])
            yy1 = max(y1[i], y1[j])
            xx2 = min(x2[i], x2[j])
            yy2 = min(y2[i], y2[j])

            w = max(0, xx2 - xx1 + 1)
            h = max(0, yy2 - yy1 + 1)
            overlap = float(w * h) / area[j]
            if overlap > overlap_thresh:
                suppress.append(pos)

        idxs = np.delete(idxs, suppress)

    return boxes[pick]


def get_diff():
    before = cv2.imread(f'screenshots/{prefix}_original.png')
    after = cv2.imread(f'screenshots/{prefix}_tmp.png')

    # Convert images to grayscale
    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    (score, diff) = compare_ssim(before_gray, after_gray, full=True)
    log.info(f"Image similarity: {score}")

    diff = (diff * 255).astype("uint8")

    thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[0] if len(contours) == 2 else contours[1]

    bounding_boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area > 00:
            x, y, w, h = cv2.boundingRect(c)
            bounding_boxes.append([x, y, x + w, y + h])

    bounding_boxes = np.array(bounding_boxes)
    pick = non_max_suppression_slow(bounding_boxes, 0.1)
    for (x, y, w, h) in pick:
        cv2.rectangle(after, (x, y), (w, h), (36, 255, 12), 2)

    # cv2.imshow('before', before)
    # cv2.imshow('after', after)
    # cv2.waitKey(0)
    output = np.concatenate((before, after), axis=1)
    return score, output


def send_notification():
    print(f"[INFO] {len(recipient_list)} emails need to be sent")
    print("[INFO] Drafting Email...")
    msg = EmailMessage()
    msg['Subject'] = parsed_url.netloc + " change"
    msg['From'] = f'Anshul Gupta <{sender}>'
    msg['Bcc'] = ', '.join(recipient_list)
    msg.set_content(f'There have been changes at {parsed_url.netloc + parsed_url.path}')
    image_cid = make_msgid(domain='example.com')
    msg.add_alternative("""\
    <html>
        <body>
            <p>There have been changes at:<br>
            {url}
            </p>
            <img src="cid:{image_cid}">
        </body>
    </html>
    """.format(image_cid=image_cid[1:-1], url=parsed_url.netloc + parsed_url.path), subtype='html')
    with open('screenshots/compare.png', 'rb') as img:
        maintype, subtype = mimetypes.guess_type(img.name)[0].split('/')
        msg.get_payload()[1].add_related(img.read(), maintype=maintype, subtype=subtype, cid=image_cid)

    print("[INFO] Connecting to Server...")
    server = smtplib.SMTP_SSL(server_url, port, timeout=10)
    server.ehlo()
    server.login(sender, password)
    print("[INFO] Sending email...")
    server.sendmail(sender, recipient_list, msg.as_string())
    server.quit()


log.info("Getting Screenshots...")
# child = subprocess.Popen(["webscreenshot", url, '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# while child.poll() is None:
#     txt = child.stdout.readline().replace(b'\r\n', b'').decode(sys.stdout.encoding)
#     if txt:
#         log.info(txt)
#
# os.replace(glob('screenshots/http*.png')[0], f'screenshots/{prefix}_tmp.png')
response = requests.get("https://render-tron.appspot.com/screenshot/" + url, stream=True)

if response.status_code == 200:
    with open(f'screenshots/{prefix}_tmp.png', 'wb') as file:
        for chunk in response:
            file.write(chunk)

log.info("Screenshots Taken")

log.info("Finding Differences...")
similarity, out = get_diff()
if similarity == 1:
    log.info("\n[INFO] No Differences Found")
    os.remove(f'screenshots/{prefix}_tmp.png')
    with open(args.log, 'a') as log_file:
        log_file.write(f"Checked {prefix.replace('_', '/')} on {time}: No differences found\n")
    exit()

log.info("Saving Image...")
out = cv2.resize(out, (0, 0), fx=0.75, fy=0.75)
cv2.imwrite(f'screenshots/{prefix}_compare.png', out)
# cv2.imshow('output', out)
# cv2.waitKey(0)

log.info("Sending Notifications...")
send_notification()
log.info("Notifications Sent")

log.info("Rewriting original.png...")
os.replace(f'screenshots/{prefix}_tmp.png', f'screenshots/{prefix}_original.png')

log.info("Cleaning up...")
os.remove(f'screenshots/{prefix}_compare.png')
with open(args.log, 'a') as log_file:
    log_file.write(f"Checked {prefix.replace('_', '/')} on {time}: Differences found, Notifications sent\n")
