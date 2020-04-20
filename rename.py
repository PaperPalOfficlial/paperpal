import json
import pymongo
import os
from pymongo import MongoClient
client = MongoClient('localhost', 27017)
db = client.PaperPal
count = 31453
# count = 0
prefix = '202004'
Chinses_journal = {'Chinese_journal_of_computers':'计算机学报','Journal_of_Software':'软件学报','Journal_of_Computer_Research_and_Development':'计算机研究与发展'}
for type in os.listdir(f'D:/paperPDF'):
    for conference in os.listdir(f'D:/paperPDF/{type}'):
        for yearConference in os.listdir(f'D:/paperPDF/{type}/{conference}'):
            for file in os.listdir(f'D:/paperPDF/{type}/{conference}/{yearConference}'):
                if len(file)<=16:
                    newName = '2020'+file[4:]
                    print(newName)
                    os.rename(f'D:/paperPDF/{type}/{conference}/{yearConference}/{file}',f'D:/paperPDF/{type}/{conference}/{yearConference}/{newName}')




        # print(newName)
        # print(item)
        # if os.path.exists(f"./static/img/{yearConference[:-5]}/{title}.png"):
        #     os.rename(f"./static/img/{yearConference[:-5]}/{title}.png",f"./static/img/{yearConference[:4]}{yearConference[4:-5]}/{item['paperId']}.png")
        #     print(item)
        # con = Chinses_journal[yearConference[4:-5]]
        # print(con)
        # con = '大数据'
        # if os.path.exists(f"./static/img/{yearConference[:4]}{con}/{title}.png"):
        #     print(con)
            # os.rename(f"./static/img/{yearConference[:4]}{con}/{title}.png",f"./static/img/{yearConference[:4]}{con}/{item['paperId']}.png")
            # print(item)


