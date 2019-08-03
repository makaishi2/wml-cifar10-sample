#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib3, requests, json
import os
from cfenv import AppEnv
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, request, render_template
from werkzeug import secure_filename
from PIL import Image, ImageOps
import numpy as np

# 認証情報の読み取り (.env または IBM Cloud上のバインド)
env = AppEnv()
pm20 = env.get_service(label='pm-20')
if pm20 is None:
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    wml_credentials = {
        "url": os.environ.get("WML_URL"),
        "apikey": os.environ.get("WML_APIKEY"),
        "instance_id": os.environ.get("WML_INSTANCE_ID"),
    }
else:
    wml_credentials = pm20.credentials

scoring_url = os.environ.get("SCORING_URL")

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.urandom(24)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/')
def top():
    name = "Top"
    return render_template('wml-sample.html', title='CIFAR10 Sample Web', name=name)

# 「予測」ボタンが押された時の処理
@app.route('/predict', methods=['POST'])
def predict():
    print('/predict')
    image = request.files['image']
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        imagefile = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(imagefile)
        img = Image.open(imagefile)
        img_resize = img.resize((32, 32))
        ftitle, fext = os.path.splitext(imagefile)
        img_resize.save(ftitle + '_sam' + fext)
        im = np.array(img_resize)
        print( 'shape1: ', im.shape)
        im_data = np.uint8(im)
        im_data2 = im_data[:,:,:3]
        print( 'shape2: ', im_data2.shape)
        im_data3 = im_data2.tolist()
        print(im_data3)

    # トークン取得
    apikey = wml_credentials["apikey"]
    # Get an IAM token from IBM Cloud
    url     = "https://iam.bluemix.net/oidc/token"
    headers = { "Content-Type" : "application/x-www-form-urlencoded" }
    data    = "apikey=" + apikey + "&grant_type=urn:ibm:params:oauth:grant-type:apikey"
    IBM_cloud_IAM_uid = "bx"
    IBM_cloud_IAM_pwd = "bx"
    response  = requests.post( url, headers=headers, data=data, 
        auth=( IBM_cloud_IAM_uid, IBM_cloud_IAM_pwd ) )
    iam_token = response.json()["access_token"]
    print('iam_token = ', iam_token)
    
    # API呼出し用ヘッダ
    ml_instance_id = wml_credentials["instance_id"]
    header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + iam_token, 
      'ML-Instance-ID': ml_instance_id}
    payload_scoring = {"values": [im_data3]}

    # API呼出し
    response_scoring = requests.post(scoring_url, json=payload_scoring, headers=header)
    res = json.loads(response_scoring.text)
    print(json.dumps(res, indent=2))
    res_list = res['values'][0][2]
    res_list2 = [round(v, 3) for v in res_list]
    res_class = res['values'][0][1]
    print("res1 is", res_class)
#    print(json.dumps(ret0, indent=2))
    return json.dumps(res_list2)

@app.route('/favicon.ico')
def favicon():
   return ""

port = os.getenv('VCAP_APP_PORT', '8000')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(port), debug=True)
