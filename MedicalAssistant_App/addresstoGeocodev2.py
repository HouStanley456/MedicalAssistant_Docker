


import requests
import json
import math
import pandas
import csv
import configparser
import os

parent_dir =os.path.dirname(os.path.abspath(__file__))
config = configparser.ConfigParser()
config.read(parent_dir + '/config.ini')
config.read('config.ini')

GOOGLE_API_KEY = "AIzaSyBC9OXMvpGIVJ5FVakJ00oQXEPq9j5E804"
submit_url = config.get('line-bot', 'end_point')+"/success"
#'放入自己的google api key'

# 計算距離
def getDistance(latA, lonA, latB, lonB):
    """
    計算經緯度對應距離 單位 公里(km)
    """
    ra = 6378140  # 赤道半徑
    rb = 6356755  # 極半徑
    flatten = (ra - rb) / ra  # Partial rate of the earth
    # change angle to radians
    radLatA = math.radians(latA)
    radLonA = math.radians(lonA)
    radLatB = math.radians(latB)
    radLonB = math.radians(lonB)

    pA = math.atan(rb / ra * math.tan(radLatA))
    pB = math.atan(rb / ra * math.tan(radLatB))
    x = math.acos(math.sin(pA) * math.sin(pB) + math.cos(pA) * math.cos(pB) * math.cos(radLonA - radLonB))
    c1 = (math.sin(x) - x) * (math.sin(pA) + math.sin(pB)) ** 2 / math.cos(x / 2) ** 2
    c2 = (math.sin(x) + x) * (math.sin(pA) - math.sin(pB)) ** 2 / math.sin(x / 2) ** 2
    dr = flatten / 8 * (c1 - c2)
    distance = ra * (x + dr)
    distance = round(distance / 1000, 4)
    return f'{distance}'

def get_latitude_longtitude(lat, lng):
    '''
    透過地圖資訊，串接 google api 回傳的 flex
    '''
    around_hospital_list = getAroundHospital(lat, lng)

    placeID_1 = around_hospital_list[0]['place_id']
    placeID_2 = around_hospital_list[1]['place_id']
    placeID_3 = around_hospital_list[2]['place_id']
    placeID = [placeID_1, placeID_2, placeID_3]

    contents = getContents(placeID)
    return contents

def get_latitude_longtitude_by_class(lat, lng, class_name):
    '''
    [棄用] google api
    過濾 星數 / 留言數 回傳 flex
    '''
    around_hospital_list = getAroundHospital(lat, lng)

    print('around hospital', around_hospital_list)
    print('class name', class_name)

    source_list = list(map(lambda x: {'name': x['name'], 'rating': x['rating'], 'user_ratings_total': x['user_ratings_total'], 'place_id': x['place_id'] }, around_hospital_list))
    print('source list', source_list)
    sort_rating_list = sorted(source_list, key=lambda s: (s['rating'], s['user_ratings_total']), reverse=True)
    print('rating list', sort_rating_list)

    placeID_1 = sort_rating_list[0]['place_id']
    placeID_2 = sort_rating_list[1]['place_id']
    placeID_3 = sort_rating_list[2]['place_id']
    placeID = [placeID_1, placeID_2, placeID_3]

    contents = getContents(placeID)
    return contents

def getAroundHospital(lat, lng):
    """
    取得周遭的醫院
    :param lat:
    :param lng:
    :return: 搜尋到的醫院列表
    """
    radius = 1000
    keyword = "醫院"

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius={radius}&types=".format(
        lat=lat, lng=lng, radius=radius) + "&keyword=" + keyword + "&key=" + GOOGLE_API_KEY
    print(url)

    res = requests.get(url)
    js = json.loads(res.text)  # 指派json進python
    print('google map 取得的 json', js)
    print('hospital count', len(js["results"]))

    return js["results"]

def getTargetClass(lat, lng, class_name):
    '''
    當有語言科別辨識，給予地圖資訊，會經過CSV過濾，回傳 flex
    '''
    # 取得所有醫院名稱和 ID
    csv_file_path = "hostipalClassData.csv"

    class_list = None

    with open(csv_file_path, mode='r', encoding='utf-8') as f:
        rows = csv.DictReader(f)
        class_list = list((row) for row in rows)

    class_list = list(map(lambda x: {'class_name': x['0'], 'compare_hospotal_id': x['1']}, class_list))

    # 詳細醫院資料
    detail_csv_file_path = "hos_df_v2.2.csv"

    detail_list = None

    with open(detail_csv_file_path, mode='r', encoding='utf-8') as f:
        rows = csv.DictReader(f)
        detail_list = list((row) for row in rows)

    detail_list = list(
        map(lambda x: {'Hosp_ID': x['Hosp_ID'], 'Hosp_Name': x['Hosp_Name'], 'Special_Type': x['Special_Type'],
                       'Special_Name': x['Special_Name'], 'Regist_Fee': x['Regist_Fee'],
                       'EM_Regist_Fee': x['EM_Regist_Fee'], 'Fee_Remark': x['Fee_Remark'], 'Address': x['Address'],
                       'Tel_Num': x['Tel_Num'], 'Stars': x['Stars'], 'Comments': x['Comments']}, detail_list))

    # 取得醫院經緯度資料
    location_list = pandas.read_excel('hospital-location.xlsx', engine='openpyxl')

    # class_list - 科別
    # detail_list - 醫院細節 星數和回覆
    # location_list - 醫院經緯度

    # class_name = '解剖病理科'
    # lat = 25.0508991  # 緯度
    # lon = 121.5607744  # 經度
    class_name = class_name
    lat = lat  # 緯度
    lon = lng  # 經度

    # 取得科目對應醫院ID
    filter_class_list = list(filter(lambda x: x['class_name'] == class_name, class_list))
    if(len(filter_class_list)==0):
        # 空 flex
        return emptyContents()
    target_class_list = filter_class_list[0]['compare_hospotal_id']
    target_class_list = target_class_list[1:][:-1].split(',')
    target_class_list = list(map(lambda x: x.strip()[1:][:-1], target_class_list))
    print(len(target_class_list))

    # 取得有對應科目的醫院資料，並用星號和留言量排序
    target_detail_list = []
    for detail in detail_list:
        if (detail['Hosp_ID'] in target_class_list):
            target_detail_list.append(detail)

    sort_rating_list = sorted(target_detail_list, key=lambda s: (s['Stars'], s['Comments']), reverse=True)
    sort_rating_list = list(filter(lambda x: x['Stars'] != '\\N', sort_rating_list))

    target_name_list = list(map(lambda x: x['Hosp_Name'], sort_rating_list))

    target_location_list = location_list.loc[location_list['醫院名稱'].isin(target_name_list)].values.tolist()

    compare_hospital_list = []
    print('過濾科別排序完的醫院數量', len(target_location_list))
    # 取得 距離兩公里內的醫院
    pickCount = 3
    for location in target_location_list:
        # print(float(getDistance(lat, lon, location[2], location[3])))
        distance = float(getDistance(lat, lon, location[2], location[3]))
        if (distance <= 3 and pickCount != 0):
            print(str(distance) + 'km')
            compare_hospital_list.append(location[1])
            pickCount = pickCount - 1

    full_detail_list = list(filter(lambda x: x['Hosp_Name'] in compare_hospital_list, detail_list))

    contents = dict()
    contents['type'] = 'carousel'
    bubbles = []

    print('取的詳細資料的醫院數量', len(full_detail_list))
    for detail in full_detail_list:
        import random
        jpg_url = random.choice(["https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT24omhm_NFsqa0H93BCj3CzH1IUHNZ7EinQg&usqp=CAU","https://www.cathay-ins.com.tw/CXIDocs/PF/image/group/PFA1_0540/persona-hospital@2x.png","https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRVwmNyfhQvLHiju0RIWC14OiM7CoRfiJPheQ&usqp=CAU","https://img.ixintu.com/download/jpg/20200802/a55dba541a20c31c3d7521d8fd1e491a_512_512.jpg!ys"])
        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": detail['Hosp_Name'],
                        "wrap": True
                    }
                ]
            },
            "hero": {
                "type": "image",
                "size": "full",
                "url": jpg_url
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "電話 : " + detail['Tel_Num']
                    },
                    {
                        "type": "text",
                        "text": "等級 : " + detail['Special_Name']
                    },
                    {
                        "type": "text",
                        "text": "地址 : " + detail['Address']
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "預約",
                            "uri": submit_url
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)

    contents['contents']=bubbles
    return contents

def emptyContents():
    return {
  "type": "bubble",
  "hero": {
    "type": "image",
    "url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQIH34HtYbba1FyTgaE6n6pyAd-Y6R7TnGFpQ&usqp=CAU",
    "size": "full",
    "aspectRatio": "20:13",
    "aspectMode": "fit",
    "action": {
      "type": "uri",
      "uri": "https://linecorp.com"
    }
  },
  "body": {
    "type": "box",
    "layout": "vertical",
    "spacing": "md",
    "action": {
      "type": "uri",
      "uri": "https://linecorp.com"
    },
    "contents": [
      {
        "type": "text",
        "text": "目前無推薦醫院",
        "size": "xl",
        "weight": "bold"
      },
      {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": []
      }
    ]
  }
}


def getContents(placeID_list):
    """
    將 place_id 傳入集合成對應卡片畫面
    :param placeID_list:
    :return:
    """
    contents = dict()
    contents['type'] = 'carousel'
    bubbles = []

    for x in placeID_list:
        # placeID=js["results"][x]['place_id']   #placeID="ChIJlblYxnOpQjQR_7C_sDPc4P0"
        url = "https://maps.googleapis.com/maps/api/place/details/json?&fields=name,formatted_address,rating,formatted_phone_number,geometry&place_id=" +x + "&key=" + GOOGLE_API_KEY + "&language=zh_TW"

        res = requests.get(url)
        js = json.loads(res.text)  # 指派json進python
        print('中文輸出資訊', js)
        formatted_address = js["result"]["formatted_address"]

        try:
            formatted_phone_number = js["result"]["formatted_phone_number"]
        except:
            print("沒有電話")

        hosname = js["result"]["name"]
        try:
            rat = js["result"]["rating"]
        except:
            print("沒有星數")

        lat = js["result"]["geometry"]["location"]["lat"]
        lng = js["result"]["geometry"]["location"]["lng"]
        # print(formatted_address,formatted_phone_number,hosname,rat,lat,lng)
        import random
        jpg_url=random.choice(["https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT24omhm_NFsqa0H93BCj3CzH1IUHNZ7EinQg&usqp=CAU","https://www.cathay-ins.com.tw/CXIDocs/PF/image/group/PFA1_0540/persona-hospital@2x.png","https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRVwmNyfhQvLHiju0RIWC14OiM7CoRfiJPheQ&usqp=CAU","https://img.ixintu.com/download/jpg/20200802/a55dba541a20c31c3d7521d8fd1e491a_512_512.jpg!ys"])
        bubble ={
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": hosname,
                        "wrap": True
                    }
                ]
            },
            "hero": {
                "type": "image",
                "size": "full",
                "url": jpg_url
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "電話 : " + formatted_phone_number
                    },
                    {
                        "type": "text",
                        "text": "地址 : " + formatted_address
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "預約",
                            "uri": submit_url
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)

    contents['contents']=bubbles
    return contents


if __name__ == '__main__' :
    pass