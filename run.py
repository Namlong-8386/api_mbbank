from flask import Flask
from flask_cors import CORS, cross_origin
from flask import request
from flask import jsonify

import os

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from keras.models import model_from_json
import base64
import time

# Khởi tạo Flask Server Backend
app = Flask(__name__)

# Apply Flask CORS
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

characters_mb = ['K', 'M', 'C', 'e', 'g', 'k', 'u', 'z', 't', '3', 'U', 'a', '5', 'A', 'y', 'H', 'q', 'Z', 'V', '7', 'Q', '2', '4', 'Y', '-', 'h', '8', 'v', '6', 'd', 'b', 'n', 'p', 'P', 'E', 'c', 'm', 'D', 'B', '9', 'N', 'G']
img_width = 320
img_height = 80

# Số lượng tối đa trong captcha ( dài nhất là 6)
max_length = 15

char_to_num_mb = layers.StringLookup(vocabulary=list(characters_mb), mask_token=None)

num_to_char_mb = layers.StringLookup(vocabulary=char_to_num_mb.get_vocabulary(), mask_token=None, invert=True)


# Đọc ảnh base64 và mã hóa
def encode_base64x(base64):
    img = tf.io.decode_base64(base64)
    img = tf.io.decode_png(img, channels=1)
    img = tf.image.convert_image_dtype(img, tf.float32)
    img = tf.image.resize(img, [img_height, img_width])
    img = tf.transpose(img, perm=[1, 0, 2])
    return {"image": img}


# Dịch từ mã máy thành chữ
def decode_batch_predictions(pred, type):
    input_len = np.ones(pred.shape[0]) * pred.shape[1]
    results = keras.backend.ctc_decode(pred, input_length=input_len, greedy=True)[0][0][:, :max_length]
    output_text = []
    #for res in results:
    results = tf.strings.reduce_join(num_to_char_mb(results)).numpy().decode("utf-8")
    output_text.append(results)
    return output_text


# load model mb
json_file_mb = open('model_mb.json', 'r')
loaded_model_json = json_file_mb.read()
json_file_mb.close()
loaded_model_mb = model_from_json(loaded_model_json)
loaded_model_mb.load_weights("model_mb.h5")

# hàm để truy cập: 127.0.0.1/run -> 127.0.0.1 là ip server
@app.route("/api/captcha/mbbank", methods=["POST"])
@cross_origin(origin='*')
def mb():
    content = request.json
    start_time = time.time()
    imgstring = content['base64']
    image_encode = encode_base64x(imgstring.replace("+", "-").replace("/", "_"))["image"]
    listImage = np.array([image_encode])
    preds = loaded_model_mb.predict(listImage)
    pred_texts = decode_batch_predictions(preds, "mb")
    captcha = pred_texts[0].replace('[UNK]', '').replace('-', '')
    response = jsonify(status = "success",captcha = captcha)

    return response


# Chạy server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port='4444')  # -> chú ý port, không để bị trùng với port chạy cái khác
