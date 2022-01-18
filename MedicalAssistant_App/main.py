#coding=utf-8

from flask import Flask,request, abort, render_template, Response,jsonify
from flask_cors import CORS, cross_origin
# app = Flask(__name__)
from addresstoGeocodev2 import *
from linebot.models import *
import re
from linebot import  LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from urllib.parse import parse_qsl
import string
from visualition import drawpic
import json
import mysql.connector
from datetime import datetime, timedelta, timezone
import sys
from logging import error
from mysql.connector import connection
import mysql.connector
from mysql.connector import Error
from datetime import date

import random
import time
# from faker import Faker

from plotly.subplots import make_subplots
import plotly.graph_objects as go
from plotly.offline import init_notebook_mode, plot_mpl
import plotly.express as px
import pandas as pd
from PIL import Image

import configparser

from google.cloud import storage

app = Flask(__name__)
CORS(app)

config = configparser.ConfigParser()
config.read('config.ini')
vmurl='http://35.202.193.99'


# Message api - Channel access token
line_bot_api = LineBotApi(config.get('line-bot', 'channel_access_token'))
# Message api - Channel secret
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))
# 基本資料
liffid = config.get('line-bot', 'liff_home')
# 生理資訊
liffida = config.get('line-bot', 'liff_health')
ngrokpath = config.get('line-bot', 'end_point')
is_no_user_test = False # True 為 未註冊用戶，False 為 正常狀況
is_last_bert = False

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    print('callback', body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@app.route("/photo/<imageId>.png")
def get_frame(imageId):
    # //去对应的文件夹找到对应名字的图片
    with open('./static/{}.png'.format(imageId), 'rb') as f:
        image = f.read()
        # //返回给用户
        resp = Response(image, mimetype="image/png")
        return resp


@handler.add(MessageEvent, message=ImageMessage)
def handle_pic(event):
    print(event)
    # 處理照片
    if event.message.type == 'image':
        # 設定圖片命名
        image_content = line_bot_api.get_message_content(event.message.id)
        image_name = event.message.id
        path = "./static/" + image_name + ".png"
        # 下載圖片檔
        with open(path, 'wb') as fd:
            for chunk in image_content.iter_content():
                fd.write(chunk)
                #linebot回傳圖片給user

        #指定圖片網址
        print('原 path', path)
        print('原 path[1::]', path[1::])
        url = ngrokpath + path[1::]

        # 添加 GCP 憑證
        YOUR_SERVICE = config.get('gcp', 'json_url')
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = YOUR_SERVICE

        # 雲端上傳
        YOUR_BUCKET = 'tfi101linebot'
        YOUR_PIC = path
        BUCKER_URL = 'static/' + image_name + '.png'
        print('BUCKER_URL', BUCKER_URL)

        upload_blob(YOUR_BUCKET, YOUR_PIC, BUCKER_URL)

        # print(url)
        #呼叫方法
        print("讀取模型中..." + url)
        storage_client = storage.Client()
        bucket = storage_client.bucket(YOUR_BUCKET)
        blob = bucket.get_blob(BUCKER_URL)

        # 傳入資源網址，並預測取得結果
        print('public url', blob.public_url)
        #result = predict(blob.public_url)
	result = requests.get(vmurl +':7777/'+ blob.public.url.split('//')[1])
        print("預測結果是" + result)

        line_id = event.source.user_id
        setChatSQL(line_id, event.message.id, 2, path[1::], result)
        #輸出結果
        # print(result)
        # image_message = ImageSendMessage(
        #     original_content_url=path,  #### 靜態檔案的url
        #     preview_image_url=path
        # )
        # 使用replyAPI回傳
        # line_bot_api.reply_message(event.reply_token, image_message)0
        # line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！'))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))
        return result

#LIFF靜態頁面pip install --upgrade pip
@app.route('/page')
def page():
	return render_template('index.html', liffid = liffid)


#LIFF靜態頁面pip install --upgrade pip
@app.route('/physical')
def physical():
	return render_template('health.html', liffid = liffida)


@app.route('/success')
def submitSuccess():
	return render_template('submit-success.html')

@app.route('/after')
def after():
    return render_template('after.html')

@app.route('/healthChart')
def healthChart():
    chart_liffid = config.get('line-bot', 'liff_chart')
    print(chart_liffid)
    return render_template('healthChart.html', liffid=chart_liffid, ngrokpath=ngrokpath)

@app.route('/doctor/', methods=['GET'])
def doctor():
    return render_template('doctor.html')

@handler.add(MessageEvent, message=LocationMessage)
def handle_message(event):
    class_name_list = ['口腔顎面外科', '不分科', '內科', '牙科', '牙髓病科', '外科', '皮膚科', '耳鼻喉科', '兒科', '兒童牙科',
                       '放射診斷科', '放射腫瘤科', '泌尿科', '急診醫學科', '家醫科', '核子醫學科', '神經外科', '神經科', '骨科',
                       '婦產科', '眼科', '麻醉科', '復健科', '解剖病理科', '精神科', '齒顎矯正科', '整形外科', '臨床病理科',
                       '職業醫學科', '口腔病理科', '中醫一般科', '放射線科', '病理科', '復形牙科', '家庭牙醫科', '牙周病科',
                       '復補綴牙科']

    # 往前推兩則訊息是「我想進一步了解我的症狀」
    is_last_two_bert = False
    source_event = event

    print('location message', event)
    print('source', dir(source_event.source))
    # source 看到的是 userId，但取得名稱是 user_id
    print('source user id', source_event.source.user_id)
    line_id = source_event.source.user_id

    lastTwoSentence = getLastTwoSentence(line_id)
    print(lastTwoSentence)

    if (len(lastTwoSentence) == 2):
        print('往前兩個是 我想進一步了解我的症狀', lastTwoSentence[1][0] == '我想進一步了解我的症狀')
        is_last_two_bert = lastTwoSentence[1][0] == '我想進一步了解我的症狀'

    print('上一個是 bert 相關科目名稱', is_last_two_bert)
    if is_last_two_bert:
        class_name = getLastClassName(line_id)[0][0]
        content = getTargetClass(event.message.latitude, event.message.longitude, class_name)
        # line_bot_api.reply_message(event.reply_token, TextSendMessage(text='已接收到科別排序'))
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text='為您推薦具有高評價的醫院', contents=content))
    else:
        content = get_latitude_longtitude(event.message.latitude, event.message.longitude)
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text='為您推薦最近的醫院', contents=content))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
            print('source handle')
            mtext = event.message.text
            # *：註冊完成 // #：生理資訊輸入完成 //
            symtext = ['*', '#', '圖']
            symtext2 = ["開始使用本服務", "我想進一步了解我的症狀", "我想了解我的皮膚情形", "很抱歉，無法提供後續服務", "systemcall"]
            if mtext[:1] in symtext or mtext in symtext2:
                if mtext[:1] == '*' and len(mtext) > 1:
                    print('註冊完成內容', mtext)
                    info = mtext.split('/')
                    line_id = info[0].replace("*", "")
                    print('取得 line id', line_id)
                    print('取得姓名', info[1])
                    print('取得身分證', info[2])
                    print('取得生日', info[3])
                    print('取得地址', info[4])
                    setInfoSQL(line_id, info[1], info[4], info[3])
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        text="恭喜完成基本資料認證，可以開始使用本服務囉！\n●皮膚圖像查詢\n●文字症狀查詢\n\n請點選下方「選單」"))
                        # text="恭喜完成基本資料認證，請點選下方「生理資訊輸入」按鈕以進行基本資料輸入"))

                elif mtext[:1] == '#' and len(mtext) > 1:

                    print('生理資訊輸入完成', mtext)
                    info = mtext.split('/')
                    line_id = info[0].replace("#", "")
                    print('取得 line id', line_id)
                    print('取得身高', info[1])
                    print('取得體重', info[2])
                    print('取得收縮壓 - 高', info[3])
                    print('取得舒張壓 - 低', info[4])
                    print('取得血氧', info[5])
                    print('取得血糖', info[6])

                    if is_no_user_test:
                        line_id = 'fagg245wrr'

                    print('讀取個人 line_id 資料 前')
                    hasUse = isExistUser(line_id)
                    print('讀取個人 line_id 資料 後')

                    if hasUse:
                        setHealthSQL(line_id, event.message.id, info[1], info[2], info[3], info[4], info[5], info[6])
                        print('完成寫入生理資料資料庫')
                        createHealtImage(line_id)

                    replyText = "為您紀錄生理資訊內容如下\n"
                    if info[1]:
                        replyText = replyText + f'\n身高：{info[1]} 公分'
                    if info[2]:
                        replyText = replyText + f'\n體重：{info[2]} 公斤'
                    if info[5]:
                        replyText = replyText + f'\n血氧：{info[5]} %'
                    if info[6]:
                        replyText = replyText + f'\n血糖：{info[6]} mg/dL'
                    if info[3]:
                        replyText = replyText + f'\n收縮壓 - 高：{info[3]} mmHg'
                    if info[4]:
                        replyText = replyText + f'\n舒張壓 - 低：{info[4]} mmHg'
                    if (not hasUse):
                        replyText = replyText + f'\n\n敬愛的用戶您好，以上資訊僅於手機保留，若想數位化紀錄，並協同醫生查閱，歡迎您的加入。'

                    # line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    #     text=replyText))

                    path = "./photo/" + line_id + ".png"
                    url = ngrokpath + path[1::]

                    tiny_path = "./photo/" + line_id + "_tiny.png"
                    tiny_url = ngrokpath + tiny_path[1::]

                    print(url)
                    image_message = ImageSendMessage(
                        original_content_url=url,  #### 靜態檔案的url
                        preview_image_url=tiny_url)
                    print(image_message)
                    line_bot_api.reply_message(event.reply_token, [TextSendMessage(
                        text=replyText), image_message])

                elif mtext == 'systemcall':
                    createHealthInfo(event.source.user_id)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="生成過往14日生理資訊已完成！"))

                elif mtext[:1] == '圖' and len(mtext) > 1:
                    line_id = event.source.user_id
                    if is_no_user_test:
                        line_id = 'fagg245wrr'

                    hasUse = isExistUser(line_id)

                    if hasUse:
                        createHealtImage(line_id)

                        path = "./static/" + line_id + ".png"
                        url = ngrokpath + path[1::]
                        print(url)
                        image_message = ImageSendMessage(
                            original_content_url=url,  #### 靜態檔案的url
                            preview_image_url=url)
                        print(image_message)
                        line_bot_api.reply_message(event.reply_token, image_message)
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="啟用生理資訊紀錄，歡迎加入我們！"))

                    # lineid = "'ytw00QqxJ3o3KMGUwyE7fF5WFnbxtz4H'"
                    # messageid = event.message.id
                    # drawpic(lineid, messageid)
                    # path = "./static/" + messageid + ".png"
                    # url = "http://10.2.14.62:5004/" + path[1::]
                    # print(url)
                    # image_message = ImageSendMessage(
                    #     original_content_url=path,  #### 靜態檔案的url
                    #     preview_image_url=path)
                    # print(image_message)
                    # line_bot_api.reply_message(event.reply_token, image_message)

                elif event.message.text == "開始使用本服務":
                    line_id = event.source.user_id
                    if is_no_user_test:
                        line_id = 'fagg245wrr'

                    hasUse = isExistUser(line_id)

                    if hasUse:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(
                            text='您以為 VIP 會員\n可隨時使用本服務'))
                    else:
                        Confirm_template = TemplateSendMessage(
                            alt_text='目錄 template',
                            template=ConfirmTemplate(
                                title='這是ConfirmTemplate',
                                text='本AI 醫療服務由醫療助理團隊提供，在我開始查詢之前，需要請你先詳細閱讀並同意服務條款。',
                                actions=[
                                    URITemplateAction(  #開啟網頁
                                        label='同意',
                                        uri='https://liff.line.me/'+config.get('line-bot', 'liff_home')
                                    ),
                                    MessageTemplateAction(
                                        label='不同意',
                                        text='很抱歉，無法提供後續服務'
                                    )
                                ]
                            )
                        )
                        line_bot_api.reply_message(event.reply_token, Confirm_template)

                elif event.message.text == "很抱歉，無法提供後續服務":
                    return None

                elif "我想進一步了解我的症狀" in event.message.text:
                    # symptomtime=datetime.datetime.now()
                    # if datetime.datetime.timestamp(symptomtime)-datetime.datetime.timestamp(entertime)>20:
                    line_id = event.source.user_id
                    setChatSQL(line_id, event.message.id, 0, event.message.text, '')
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您好，請輸入病徵，解析後將為您提供相關訊息"))
                    # elif datetime.datetime.timestamp(symptomtime)-datetime.datetime.timestamp(entertime)<20:
                    # line_bot_api.reply_message(event.reply_token,TextSendMessage(text="請輸入完整資訊"))

                elif "我想了解我的皮膚情形" in event.message.text:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您好，請上傳圖片，解析後將為您提供相關訊息",
                                                                                  quick_reply=QuickReply(
                                                                                        items=[
                                                                                                QuickReplyButton(
                                                                                                    action=CameraAction(label="請拍照")
                                                                                                ),
                                                                                                QuickReplyButton(
                                                                                                    action=CameraRollAction(label="或開啟相簿上傳照片")
                                                                                                )
                                                                                            ]
                                                                                  )))

            elif len(event.message.text) != 0:
                is_last_one_bert = False
                is_last_two_bert = False

                line_id = event.source.user_id
                lastTwoSentence = getLastTwoSentence(line_id)
                print(lastTwoSentence)

                if (len(lastTwoSentence) == 1):
                    is_last_one_bert = lastTwoSentence[0][0] == '我想進一步了解我的症狀'

                if (len(lastTwoSentence) == 2):
                    is_last_one_bert = lastTwoSentence[0][0] == '我想進一步了解我的症狀'
                    is_last_two_bert = lastTwoSentence[1][0] == '我想進一步了解我的症狀'

                if is_last_one_bert:
                    pretext = requests.get(vmurl +':6666/'+ mtext)
			
                    setChatSQL(line_id, event.message.id, 1, event.message.text, pretext)
                    line_bot_api.reply_message(event.reply_token, [TextSendMessage(text="傳送地圖(Location)會得到附近星數最高且評論最多的醫院"), TextSendMessage(text=pretext, quick_reply=QuickReply(
                                                                                        items=[
                                                                                                QuickReplyButton(
                                                                                                    action=LocationAction(label="選取位置")
                                                                                                )
                                                                                            ]
                                                                                  ))])
                else:
                    setChatSQL(line_id, event.message.id, 0, event.message.text, '')
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text='敬愛的用戶您好，AI聊天尚未生成，請別期待，沒有要開發。'))

            return ("ok")

        #
        #     line_bot_api.reply_message(event.reply_token, TextSendMessage(text="我不太明白您的意思，請重新敘述"))

# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     print('* / #')
#     mtext = event.message.text
#     if mtext[:1] == '*' and len(mtext) > 1:
#          manageForm(event, mtext)
#     elif mtext[:1] == '#' and len(mtext) > 1:
#          manageHealth(event, mtext)
#     return

# 取得 LINE 的用戶
@app.route("/getUser", methods=['GET'])
def getuser():
    newData = []
    for row in returnSQL('select lineId, twname from user'):
        newData.append({'lineId': row[0], 'twname': row[1]})
    return jsonify(newData)

# 取得 用戶的健康
@app.route("/getHealth/<line_id>", methods=['GET'])
def getHealth(line_id):
    newData = []

    health_list = returnSQL("select recordtime, age, height, weight, bmi, bp_high,bp_low, bs, os from healthinfo where lineid = '%s';" % line_id)
    print('health list', health_list)

    for row in health_list:
        newData.append({'recordtime': row[0], 'age': row[1], 'height': float(row[2]), 'weight': float(row[3]), 'bmi': float(row[4]), 'bp_high': float(row[5]), 'bp_low': float(row[6]), 'bs': float(row[7]), 'bo': float(row[8])})

    return jsonify(newData)


# 接收 用戶的判斷科別和皮膚判別，兩周內，限制兩筆
@app.route("/getDetection/<line_id>", methods=['GET'])
def getDetection(line_id):

    classData = []
    skinData = []

    class_result = returnSQL("select content, reply, recordtime from chat_log where lineid = '%s' and type = 1 order by recordtime desc limit 1;" % line_id)

    skin_result = returnSQL("select content, reply, recordtime from chat_log where lineid = '%s' and type = 2 order by recordtime desc limit 1;" % line_id)

    for row in class_result:
        classData.append({'content': row[0], 'reply': row[1], 'recordtime': row[2]})

    for row in skin_result:
        skinData.append({'content': row[0], 'reply': row[1], 'recordtime': row[2]})

    class_skin_data = {'class': classData, 'skin': skinData}

    return jsonify(class_skin_data)


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )

def createHealthInfo(line_id):
    date_count = 13
    while (date_count >= 0):
        print('生成開始')
        record_date = datetime.today().date() - timedelta(days=date_count)
        date_count -= 1

        watchid = str(int(random.uniform(0, 100000)))
        Height = round(random.uniform(150.0, 190.0), 1)
        Weight = round(random.uniform(42.0, 100.0), 1)
        BP = (round(random.uniform(75.0, 100.0), 1)) + round(random.normalvariate(5, 5), 1)
        BP_high = (BP + 30 + round(random.normalvariate(0, 5), 1))
        BP_low = BP
        BS = round(random.uniform(60.0, 100.0), 1)
        OS = (round(random.uniform(94.0, 97.0), 1)) + round(random.normalvariate(0, 2), 1)
        setHealthSQLWithTime(line_id, watchid, Height, Weight, BP_high, BP_low, OS, BS, record_date)
        print('生成結束')

# def createinfo(lineid, messageid, i):
#     """確認db, 並創建100筆資料, 需輸入lineid, messageid, i=次數"""
#
#     connection = connect_db()
#     cursor = connection.cursor()
#
#     try:
#         # 顯示用戶的資料筆數
#         sql = "SELECT COUNT(*) FROM user WHERE lineid =" + lineid + ";"
#         print("sql:" + sql)
#         cursor.execute(sql)
#         record = cursor.fetchone()
#         print("用戶的資料數：", record[0])
#
#         if record[0] == 0:
#             # 新增資料
#             print("建立新的使用者...新增資料中")
#             sql = "INSERT INTO user (lineid, username, twname, sex, address, mail, birthdate) VALUES (%s, %s, %s, %s, %s, %s, %s);"
#             # print("sql:" + sql)
#             user = faker.simple_profile()
#             new_data = (lineid, messageid, user['name'], user['sex'], user['address'], user['mail'], user['birthdate'])
#             print(new_data)
#             yn = input("確認資料(Y/N)")
#             if yn == "Y":
#                 cursor.execute(sql, new_data)
#                 connection.commit()
#                 print("使用者資料建立完成!")
#             else:
#                 print("重來吧...")
#         else:
#             for a in range(i):
#                 print("開始建立第", a, "筆資料")
#                 time.sleep(1)
#
#                 watchid = "asus" + messageid + str(int(random.uniform(0, 100000)))
#                 BP = (round(random.uniform(75.0, 100.0), 1)) + round(random.normalvariate(5, 5), 1)
#                 BP_high = (BP + 30 + round(random.normalvariate(0, 5), 1))
#                 BP_low = BP
#                 BS = round(random.normalvariate(96, 0.8), 1)
#                 OS = (round(random.uniform(97.0, 98.0), 1)) + round(random.normalvariate(0, 2), 1)
#                 gentime = datetime.datetime.now()
#
#                 sql = "INSERT INTO healthinfo (lineid, watch_messageid, bp_high, bp_low, bs, recordtime, os) VALUES (%s, %s, %s, %s, %s, %s, %s);"
#                 print("sql:" + sql)
#                 new_data = (lineid, watchid, BP_high, BP_low, BS, gentime, OS)
#                 print("data: ", new_data)
#                 cursor.execute(sql, new_data)
#
#                 # 確認資料有存入資料庫
#                 connection.commit()
#                 sql = "select count(*) from healthinfo where lineid = " + lineid + ";"
#                 print("sql:" + sql)
#                 cursor.execute(sql)
#                 record = cursor.fetchone()
#                 print("目前用戶的資料數：", record[0])

def excuteSQL(sql_text):
    """
    執行 SQL 不回傳
    :param sql_text: 主要為 新增/修改/刪除
    """
    connection = mysql.connector.connect(host=config.get('mysql', 'host'),
                                         database='healthrobot',
                                         user=config.get('mysql', 'user_name'),
                                         password=config.get('mysql', 'pd')
                                         )
    mycursor = connection.cursor()
    mycursor.execute(sql_text)
    connection.commit()
    mycursor.close()
    connection.close()

def returnSQL(sql_text):
    """
    取得 SQL 資料
    :param sql_text: 主要為 讀取
    :return: 回傳值
    """
    print('return sql text', sql_text)
    connection = mysql.connector.connect(host=config.get('mysql', 'host'),
                                         database='healthrobot',
                                         user=config.get('mysql', 'user_name'),
                                         password=config.get('mysql', 'pd')
                                         )
    mycursor = connection.cursor()
    try:
        try:
            mycursor.execute(sql_text)
        except:
            exception_type, exception, exc_tb = sys.exc_info()
            print(exception)
            return None

        result = mycursor.fetchall()
        return result
    finally:
        mycursor.close()
        connection.close()

def getUserName(line_id):
    """
    取得用戶的姓名
    :return: 姓名
    """
    exist_result = returnSQL("select twname from user where lineid = '%s';" % line_id)
    return exist_result

def getPH(line_id):
    """
    取得用戶的最後14天的血壓(高的)
    :return: 最後14天的血壓(高的)
    """
    exist_result = returnSQL("select bp_high, recordtime from healthinfo where lineid = '%s' and recordtime between DATE_SUB(CURDATE(), INTERVAL 14 DAY) AND NOW() order by recordtime desc;" % line_id)
    return exist_result

def getPL(line_id):
    """
    取得用戶的最後14天的血壓(低的)
    :return: 最後14天的血壓(低的)
    """
    exist_result = returnSQL("select bp_low, recordtime from healthinfo where lineid = '%s' and recordtime between DATE_SUB(CURDATE(), INTERVAL 14 DAY) AND NOW() order by recordtime desc;" % line_id)
    return exist_result

def getBO(line_id):
    """
    取得用戶的最後14天的血氧
    :return: 最後14天的血氧
    """
    exist_result = returnSQL("select os, recordtime from healthinfo where lineid = '%s' and recordtime between DATE_SUB(CURDATE(), INTERVAL 14 DAY) AND NOW() order by recordtime desc;" % line_id)
    return exist_result

def getBS(line_id):
    """
    取得用戶的最後14天的血糖
    :return: 最後14天的血糖
    """
    exist_result = returnSQL("select bs, recordtime from healthinfo where lineid = '%s' and recordtime between DATE_SUB(CURDATE(), INTERVAL 14 DAY) AND NOW() order by recordtime desc;" % line_id)
    return exist_result

def getLastWeight(line_id):
    """
    取得用戶的最後體重
    :return: 最後體重
    """
    exist_result = returnSQL("select weight from healthinfo where lineid = '%s' order by recordtime desc limit 1;" % line_id)
    return exist_result

def getLastHeight(line_id):
    """
    取得用戶的最後身高
    :return: 最後身高
    """
    exist_result = returnSQL("select height from healthinfo where lineid = '%s' order by recordtime desc limit 1;" % line_id)
    return exist_result

def getLastOneSkin(line_id):
    """
    取得用戶的最後兩個皮膚測量結果
    :return: 最後兩個皮膚測量結果
    """
    exist_result = returnSQL("select content, reply, recordtime from chat_log where lineid = '%s' and type = 2 order by recordtime desc limit 1;" % line_id)
    return exist_result

def getLastOneClass(line_id):
    """
    取得用戶的最後兩個診斷科別
    :return: 最後兩個診斷科別結果
    """
    exist_result = returnSQL("select content, reply, recordtime from chat_log where lineid = '%s' and type = 1 order by recordtime desc limit 1;" % line_id)
    return exist_result

def getLastClassName(line_id):
    """
    取得用戶上一筆判別科別
    :return: 單筆科別資料
    """
    exist_result = returnSQL("select reply from chat_log where lineid = '%s' order by recordtime desc limit 1;" % line_id)
    return exist_result

def getLastTwoSentence(line_id):
    """
    取得用戶的最後兩個句子
    :return: 最後兩個句子
    """
    exist_result = returnSQL("select content from chat_log where lineid = '%s' order by recordtime desc limit 2;" % line_id)
    return exist_result

def setChatSQL(line_id, messageid, type, content, reply):
    """
    記錄每筆文字訊息
    :param line_id: 使用者ID
    :param messageid: 訊息ID
    :param type:  0-一般訊息 1-科別辨識 2-皮膚辨識
    :param content: 使用者傳送進來的訊息
    :param reply: 系統回傳訊息
    :return:
    """
    try:
        print('line id', line_id)
        print('message id', messageid)
        print('type', type)
        print('content', content)
        print('reply', reply)

        record_time = datetime.now()
        print('record_time', record_time)
        excuteSQL("INSERT INTO chat_log(lineid, messageid, recordtime, type, content, reply) VALUES ('%s', '%s', '%s', '%s', '%s', '%s');" % (line_id, messageid, record_time, type, content, reply))
    except:
        exception_type, exception, exc_tb = sys.exc_info()
        print(exception)
        abort(400)

def setInfoSQL(line_id, tw_name, address, birthdate):
    try:
        excuteSQL("INSERT INTO user(lineid, twname, address, birthdate) VALUES ('%s', '%s', '%s', '%s');" % (line_id, tw_name, address, birthdate))
    except:
        exception_type, exception, exc_tb = sys.exc_info()
        print(exception)
        abort(400)

def isExistUser(line_id):
    """
    確認用戶是否存在資料庫
    :return: True/False
    """
    try:
        exist_result = returnSQL("select birthdate from user where lineid = '%s';" % line_id)
        print('exist result', exist_result)
    except:
        exception_type, exception, exc_tb = sys.exc_info()
        print(exception)
        abort(400)

    return len(exist_result) != 0

def getBMI(weight, height):
    return round(int(weight)/((int(height)/100) ** 2), 1)

def setHealthSQL(line_id, message_id, height, weight, press_h, press_l, bo, bs):
        print('開始記錄生理資訊')

        bmi = getBMI(weight, height)
        print('bmi', bmi)

        birthdate_result = returnSQL("select birthdate from user where lineid = '%s';" % line_id)

        today = datetime.today()
        age = int(today.year) - int(birthdate_result[0][0].year)
        print('age', age)

        record_time = datetime.now()
        print('now', record_time)

        excuteSQL("INSERT INTO healthinfo(lineid, watch_messageid, recordtime, age, height, weight, bmi, bp_high, bp_low, bs, os) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');" % (line_id, message_id, record_time, age, height, weight, bmi, press_h, press_l, bs, bo))
        print('insert health info success')


def setHealthSQLWithTime(line_id, message_id, height, weight, press_h, press_l, bo, bs, recordtime):
    print('開始記錄生理資訊FOR生成')

    bmi = getBMI(weight, height)
    print('bmi', bmi)

    birthdate_result = returnSQL("select birthdate from user where lineid = '%s';" % line_id)

    today = datetime.today()
    age = int(today.year) - int(birthdate_result[0][0].year)
    print('age', age)

    excuteSQL("INSERT INTO healthinfo(lineid, watch_messageid, recordtime, age, height, weight, bmi, bp_high, bp_low, bs, os) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');" % (
        line_id, message_id, recordtime, age, height, weight, bmi, press_h, press_l, bs, bo))

    print('insert health info success')

def getViewHealthList(source_list, date_range):
    view_list = []

    for date in date_range:
        filter_list = []
        print(date)
        for health in source_list:
            print('pl date', health[1].date())
            print('compare', health[1].date() == date)
            if health[1].date() == date:
                print('get value', health[0])
                print('get value', float(health[0]))
                filter_list.append((health[0]))

        print('filter list', filter_list)

        if len(filter_list) != 0:
            total = 0

            for pl in filter_list:
                total += pl

            pl_value = round(total / len(filter_list), 0)
            view_list.append(pl_value)
        else:
            view_list.append(0)

        print('view_list', view_list)

    return view_list

def createHealtImage(line_id):
    print('開始繪製健康報告')
    height = getLastHeight(line_id)
    height = float(height[0][0])

    weight = getLastWeight(line_id)
    weight = float(weight[0][0])

    bmi = getBMI(weight, height)
    # print('bmi', bmi)

    view_pl_list = []
    pl_list = getPL(line_id)
    # print('pl_list', pl_list)

    view_ph_list = []
    ph_list = getPH(line_id)
    # print('ph_list', ph_list)

    view_bo_list = []
    bo_list = getBO(line_id)
    # print('bo_list', bo_list)

    view_bs_list = []
    bs_list = getBS(line_id)
    # print('bs_list', bs_list)

    print('get user name', getUserName(line_id))
    userName = getUserName(line_id)[0][0]

    # skin = getLastOneSkin(line_id)[0]
    # view_skin = [skin[2].strftime("%Y-%m-%d"), skin[1], skin[0]]
    # # print('skin', skin)
    #
    # text_class = getLastOneClass(line_id)[0]
    # view_class = [text_class[2].strftime("%Y-%m-%d"), text_class[1], text_class[0]]
    # # print('text_class', text_class)

    # 生成 14 天日期列表
    datelist = []
    date_count = 13
    while (date_count >= 0):
        datelist.append(datetime.today().date() - timedelta(days=date_count))
        date_count -= 1

    view_pl_list = getViewHealthList(pl_list, datelist)
    view_ph_list = getViewHealthList(ph_list, datelist)
    view_bs_list = getViewHealthList(bs_list, datelist)
    view_bo_list = getViewHealthList(bo_list, datelist)


    try:
        print('病人基本資訊開始')
        fig = make_subplots(
            rows=3, cols=1,
            specs=[[{"type": "table"}],
                   [{"type": "table"}],
                   [{"type": "table"}], ],
            row_heights=[3, 3, 4]
            #     column_widths=[0.4, 0.5],
        )

        # --病人資訊--
        bmi = getBMI(weight, height)
        well_weight = 62 + (173 - 170) * 0.6
        normal_info = [datetime.today().date(), userName, '-', height, weight, well_weight, bmi]

        # 判斷紅字
        bmi = float(bmi)
        if (bmi < 18.5) or (bmi >= 24):
            BMIcolor = 'red'
        else:
            BMIcolor = '#0B1013'

        fig.add_trace(go.Table(
            header=dict(
                values=['紀錄日期', '姓名', '性別', '身高', '體重', '理想體重', 'BMI'],
                line_color='white',
                fill_color='#FAECCD',
                font=dict(color='#0B1013', size=10),
                align="center"
            ),
            cells=dict(
                values=normal_info,
                line_color='white',
                fill=dict(color='white'),
                font=dict(color=['#0B1013', '#0B1013', '#0B1013', '#0B1013', '#0B1013', '#0B1013', BMIcolor], size=10),
                align="center")
        ),
            row=1, col=1
        )

        # --------------------------------------------------------------------------------------------------------------#
        # --病人血液資訊--
        print('病人血液資訊開始')

        白血球WBC = 6.6
        紅血球RBC = 5.53
        血紅素Hgb = 16.3
        血球容積比Hct = 49.8
        平均紅血球容積MCV = 89.9
        血小板數目Platelet = 246

        # 判斷紅字
        WBC = float(白血球WBC)
        if (WBC < 4) or (WBC > 11):
            WBCcolor = 'red'
        else:
            WBCcolor = '#0B1013'

        RBC = float(紅血球RBC)
        if (RBC < 4.5) or (RBC > 6.1):
            RBCcolor = 'red'
        else:
            RBCcolor = '#0B1013'

        Hgb = float(血紅素Hgb)
        if (Hgb < 13.8) or (Hgb > 18.0):
            Hgbcolor = 'red'
        else:
            Hgbcolor = '#0B1013'

        Hct = float(血球容積比Hct)
        if (Hct < 38) or (Hct > 52):
            Hctcolor = 'red'
        else:
            Hctcolor = '#0B1013'

        MCV = float(平均紅血球容積MCV)
        if (MCV < 78) or (MCV > 100):
            MCVcolor = 'red'
        else:
            MCVcolor = '#0B1013'

        Platelet = float(血小板數目Platelet)
        if (Platelet < 150) or (Platelet > 400):
            Plateletcolor = 'red'
        else:
            Plateletcolor = '#0B1013'

        # 建立圖表
        fig.add_trace(
            go.Table(
                header=dict(
                    values=['白血球', '紅血球', '血紅素', '血球容積比', '平均紅血球容積', '血小板數目'],
                    line_color='white',
                    fill_color='#FEDFE1',
                    font=dict(color='#0B1013', size=10),
                    align="center"
                ),
                cells=dict(
                    values=[白血球WBC, 紅血球RBC, 血紅素Hgb, 血球容積比Hct, 平均紅血球容積MCV, 血小板數目Platelet],
                    line_color='white',
                    fill=dict(color='white'),
                    font=dict(color=['#0B1013', WBCcolor, RBCcolor, Hgbcolor, Hctcolor, MCVcolor, Plateletcolor],
                              size=10),
                    align="center")
            ),
            row=2, col=1
        )

        # fig.update_layout(height=800,width=1100,showlegend=False,template='simple_white',title_text="病人基本資料")
        # --------------------------------------------------------------------------------------------------------------#

        # --血液標準--
        df = pd.read_csv("./血液檢查標準.csv")

        fig.add_trace(
            go.Table(
                header=dict(
                    values=['血液常規檢查', '標準範圍'],
                    line_color='#828282',
                    fill_color='white',
                    font=dict(color='#0B1013', size=10),
                    align="center"
                ),
                cells=dict(
                    values=[df['血液常規檢查'], df['標準範圍']],
                    line_color='white',
                    fill=dict(color='white'),
                    font=dict(color='#0B1013', size=10),
                    align="left")
            ),
            row=3, col=1
        )

        fig.update_layout(height=700, width=600, showlegend=False, title_text="病人基本資料")

        print('匯出圖片 生理資訊 開始')
        fig.write_image('.\\static\\Patient_Base.png', scale=3)
        print('匯出圖片 生理資訊 結束')
        # fig.show()
        # --------------------------------------------------------------------------------------------------------------#

        # --BP-BU--
        # 範圍設定
        print('病人血壓血糖資訊開始')
        if max(view_ph_list) > 140:
            y_maxhigh = max(view_ph_list) + 10
        else:
            y_maxhigh = 150

        if min(view_ph_list) < 100:
            y_minhigh = min(view_ph_list) - 10
        else:
            y_minhigh = 50

        if max(view_pl_list) > 90:
            y_maxlow = max(view_pl_list) + 10
        else:
            y_maxlow = 110

        if max(view_bs_list) > 100:
            y_maxbu = max(view_bs_list) + 10
        else:
            y_maxbu = 120

        figB = make_subplots(
            rows=3, cols=1,
            #     shared_xaxes=True,
            #     shared_yaxes=True,
            #     vertical_spacing=0.06,
            #     horizontal_spacing=0.06,
            #     specs=[[{"type": "table"}],
            #            [{"type": "table"}],
            #            [{"type": "table"}],],
            row_heights=[3, 3, 3],
            #     column_widths=[0.4, 0.5],
            subplot_titles=("收縮壓", "舒張壓", "血糖"))

        # BP收縮壓
        figB.add_trace(go.Scatter(x=datelist,
                                  y=view_ph_list,
                                  mode='lines+markers',
                                  # marker=dict(color= '#FEDFE1'),
                                  # line=dict(color='#A2DB84', width=3),
                                  name='收縮壓'),
                       row=1, col=1)
        figB.add_hline(y=100, line_color='red', row=1, col=1)
        figB.add_hline(y=140, line_color='red', row=1, col=1)
        figB.add_hrect(y0=100, y1=y_minhigh, line_width=0, fillcolor="red", opacity=0.1, row=1, col=1)
        figB.add_hrect(y0=140, y1=y_maxhigh, line_width=0, fillcolor="red", opacity=0.1, row=1, col=1)

        # BP舒張壓
        figB.add_trace(go.Scatter(x=datelist,
                                  y=view_pl_list,
                                  mode='lines+markers',
                                  # marker=dict(color= '#E9CD4C'),
                                  # line=dict(color='#E9CD4C', width=3),
                                  name='舒張壓'),
                       row=2, col=1)
        figB.add_hline(y=90, line_color='red', row=2, col=1)
        figB.add_hrect(y0=90, y1=y_maxlow, line_width=0, fillcolor="red", opacity=0.1, row=2, col=1)

        # BU血糖
        figB.add_trace(go.Scatter(x=datelist,
                                  y=view_bs_list,
                                  mode='lines+markers',
                                  # marker=dict(color= [BPcolor,BPcolor,BPcolor,BPcolor,BPcolor,BPcolor,BPcolor,BPcolor,BPcolor,BPcolor]),
                                  # line=dict(color='#B5CAA0', width=3),
                                  name='血糖'),
                       row=3, col=1)
        figB.add_hline(y=100, line_color='red', row=3, col=1)
        figB.add_hrect(y0=100, y1=y_maxbu, line_width=0, fillcolor="red", opacity=0.1, row=3, col=1)

        figB.update_layout(height=700, width=600, showlegend=False, template='simple_white')
        # figB.show()
        print('血液圖片匯出 開始')
        figB.write_image('.\\static\\Patient_BPBU.png', scale=3)
        print('血液圖片匯出 結束')

        img1 = Image.open("./static/Patient_Base.png")
        # img1 = img1.crop((10, 10, 650, 155))   #img1 裁切
        img2 = Image.open("./static/Patient_BPBU.png")

        result = Image.new(img1.mode, (1800, 4200))
        result.paste(img1, box=(0, 0))
        result.paste(img2, box=(0, 1900))
        result.save(f"./static/{line_id}.png")
        result.save("./static/Patient01_dashboard_1.png")
        result.thumbnail((180, 350))
        result.save(f"./static/{line_id}_tiny.png", quality=65, subsampling=0)

        # result = Image.new(img1.mode, (3500, 2200))
        # result.paste(img1, box=(0, 0))
        # result.paste(img2, box=(1800, 0))
        # result.save(f"./static/{line_id}.png")
        # result.save("./static/Patient01_dashboard_1.png")
        # result.thumbnail((350, 220))
        # result.save(f"./static/{line_id}_tiny.png", quality=65, subsampling=0)


    except:
        exception_type, exception, exc_tb = sys.exc_info()
        print(exception)


# def manageForm(event, mtext):
#     try:
#         flist = mtext[1:].split('/')
#         text1 = '姓名：' + flist[0] + '\n'
#         text1 += '身分證：' + flist[1] + '\n'
#         text1 += '日期：' + flist[2] + '\n'
#         text1 += '地址：' + flist[3]
#         message = TextSendMessage(
#             text = text1
#         )
#         line_bot_api.reply_message(event.reply_token,message)
#     except:
#         line_bot_api.reply_message(event.reply_token,TextSendMessage(text='發生錯誤！'))
#     return


# def manageHealth(event, mtext):
#     try:
#         print('manage health', event)
#         flist = mtext[1:].split('/')
#         text1 = '身高：' + flist[0] + '\n'
#         text1 += '體重：' + flist[1] + '\n'
#         text1 += '血壓：' + flist[2] + '\n'
#         text1 += '血糖：' + flist[3]
#         message = TextSendMessage(
#             text = text1
#         )
#         line_bot_api.reply_message(event.reply_token,message)
#     except:
#         line_bot_api.reply_message(event.reply_token,TextSendMessage(text='發生錯誤！'))
#     return

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5004)
