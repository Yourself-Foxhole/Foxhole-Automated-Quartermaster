import io
import os
import functools
import itertools

import cv2
from tesserocr import PyTessBaseAPI, PSM, OEM
import numpy as np

from PIL import Image, ImageOps
import flask


tesserocr = PyTessBaseAPI(path='/usr/share/tesseract-ocr/5/tessdata', psm=PSM.SINGLE_BLOCK, oem=OEM.LSTM_ONLY)

def ocr(img, only_text=False, debug=False):
    img = ImageOps.invert(Image.fromarray(img).convert('L'))
    img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)

    tesserocr.SetImage(img)
    text = tesserocr.GetUTF8Text().strip()
    
    if only_text:
        return text

    if debug:
        print(text)

    if 'k+' in text:
        text = text.replace('A', '4')
        text = text[:-2] + '000'

    if not text.isdigit():
        print('recognized non-digits:', text)
        tesserocr.SetVariable("tessedit_char_whitelist", "0123456789")
        tesserocr.SetImage(img)
        text = tesserocr.GetUTF8Text().strip()
        tesserocr.SetVariable("tessedit_char_whitelist", "")
        print('tried again:', text)

        if not text.isdigit():
            return 0  # problems with shirts and msupps

    return int(text)

@functools.cache
def get_icons(size=64):
    vectors = []
    names = []

    directory = 'web/icons/'

    for filename in os.listdir(directory):
        names.append(filename[:-4])
        img = cv2.imread(directory + filename)
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
        vectors.append(img.reshape(-1))

    vectors = np.stack(vectors).astype(np.float32)
    
    return vectors, names


def find_counts(img):
    """Returns counts and stockpile name"""
    img = cv2.copyMakeBorder(
        img,
        top=1,
        bottom=1,
        left=1,
        right=1,
        borderType=cv2.BORDER_CONSTANT,
        value=[255, 255, 255]
    )

    shiftleft = img[1:,:-1,:]
    shiftup = img[:-1,1:,:]
    crop = img[1:,1:,:]

    mask = (crop[:,:] == 98).all(axis=2) & (shiftleft[:,:] < 50).all(axis=2) & (shiftup[:,:] < 50).all(axis=2)

    counts = {}
    stockpile = None

    for x, y in zip(*np.where(mask)):
        w = 0
        while (crop[x, y + w] == 98).all():
            w += 1

        h = 0
        while (crop[x + h, y] == 98).all():
            h += 1

        #print(w, h, x, y)

        offset = {
            21: 29,
            22: 29, 
            23: 31,
            26: 37,
            27: 37,
            28: 39,
            29: 39,
            30: 41,
            32: 44
        }

        if h not in offset or y < offset[h] or abs(w/h - 42/32) > 0.02:
            continue

        iconbox = crop[x:x+h, y-offset[h]:y-offset[h]+h]

        vectors, names = get_icons(h)

        sums = np.square(vectors - iconbox.reshape(-1)).mean(axis=1)
        idx = sums.argmin()

        if sums[idx] < 5000:  # <- to be tuned
            textbox = crop[x:x+h, y:y+w]
            count = ocr(textbox)
            
            name = names[idx]         
            counts[name] = count

            print(names[idx], count, '---' , int(sums[idx]),)

            if name == 'SoldierSupplies-crated':
                _x = x - 1
                _y = y
                while (crop[_x, _y] < 50).all():
                    _y += 1
                stockpilebox = img[x-h-5:x-8, y+2*w:_y-38]
                stockpile = 'Public'
                if (stockpilebox > 200).any():
                    recognized = ocr(stockpilebox, only_text=True)
                    if recognized:
                        stockpile = recognized
        
    return counts, stockpile

app = flask.Flask(__name__, static_folder='web', static_url_path='')

@app.route('/')
def serve_root():
    return flask.send_from_directory('web', 'index.html')

@app.route("/recognize", methods=['POST'])
def recognize():
    if 'file' not in flask.request.files:
        return flask.jsonify({'error': 'No file part'}), 400
    
    file = flask.request.files['file']
    
    if file.filename == '':
        return flask.jsonify({'error': 'no file uploaded'}), 400
    
    img = np.asarray(Image.open(io.BytesIO(file.read())))[:,:,:3]
    counts, stockpile = find_counts(img)
    
    return flask.jsonify({'counts': counts, 'stockpile': stockpile}), 200


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8080)
