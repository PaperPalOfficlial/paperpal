from flask import Flask, jsonify, render_template, request, g, session,\
    redirect, url_for, flash, render_template_string
from flask_paginate import Pagination, get_page_parameter
from flask_login import LoginManager
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired
from flask_msearch import Search
from collections import defaultdict
import jieba
from pymongo import MongoClient
from flask_pymongo import PyMongo,DESCENDING,ASCENDING
# from  page import get_page
import os
import json
import math
import ast
import pickle
import pymongo
from utils import safe_pickle_dump, strip_version, isvalidid, Config


from tqdm import tqdm
from datetime import datetime, timedelta
# from sshtunnel import SSHTunnelForwarder


# server = SSHTunnelForwarder(
#     '10.141.2.222',
#     ssh_username='fyw',
#     ssh_password='password',
#     remote_bind_address=('127.0.0.1', 27017)
# )
# server.start()

app = Flask(__name__)
app.config.from_pyfile('settings.py')
# app.config['SQLALCHEMY_DATABASE_URI'] =

# MongoDB 数据库，取最新的数据作为 Latest 里面的数据
# client = MongoClient('127.0.0.1', server.local_bind_port)
client = MongoClient('127.0.0.1',27017)
db = client.PaperPal
db.paper.create_index([('title',pymongo.TEXT)])
db.ChinesePaper.create_index([('searchTitle',pymongo.TEXT)])
end_date = datetime.today().strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=100)).strftime('%Y-%m-%d')
PAPERS = [
    # i for i in db.paper.find(
    #     {
    #         'datetime': {
    #             '$gte': start_date,
    #             '$lt': end_date
    #         }
    #     }, limit=200).sort('datetime', pymongo.DESCENDING)
    i for i in db.paper.find().sort('datetime', pymongo.DESCENDING).limit(200)
]
all_conference = {
    'conference':{
        'CCF-AI-A':['AAAI','ACL','CVPR','ICCV','ICML','IJCAI','NIPS'],
        'CCF-AI-B':['AAMAS','COLING','COLT','ECAI','ECCV','EMNLP','ICAPS','ICCBR','ICRA','KR','PPSN','UAI'],
        'CCF-DATA-A':['ICDE','SIGIR','SIGKDD','SIGMOD','VLDB'],
        'CCF-DATA-B':['CIDR','CIKM','DASFAA','ECML-PKDD','EDBT','ICDM','ICDT','ISWC','PODS','SDM','WSDM'],
    },
    'journal':{
        '中文期刊':['计算机学报','软件学报','计算机研究与发展','大数据']
    }

}
conference_years={
    "AAAI":['2019','2018','2017'],
    'ACL':['2019','2018','2017'],
    'CVPR':['2019','2018','2017'],
    'ICCV':['2017'],
    'ICML':['2019','2018','2017'],
    'IJCAI':['2019','2018','2017'],
    'NIPS':['2019','2018','2017'],
    'AAMAS':['2019','2018','2017'],
    'COLING':['2018'],
    'COLT':['2019','2018','2017'],
    'ECAI':['2018'],
    'ECCV':['2018'],
    'EMNLP':['2019','2018','2017'],
    'ICAPS':['2019','2018','2017'],
    'ICCBR':['2017'],
    'ICRA':['2019','2018','2017'],
    'KR':['2018'],
    'PPSN':['2018'],
    'UAI':['2019','2018','2017'],
    '计算机学报':['2020','2019','2018'],
    '软件学报':['2020','2019','2018','2017'],
    '计算机研究与发展':['2020','2019','2018','2017'],
    '大数据':['2020','2019','2018','2017'],
    'ICDE':['2019','2018','2017'],
    'SIGMOD':['2019','2018','2017'],
    'SIGIR':['2019','2018','2017'],
    'SIGKDD':['2019','2018','2017'],
    'VLDB':['2019','2018','2017'],
    'CIDR':['2020','2019','2017'],
    'CIKM':['2019','2018'],
    'DASFAA':['2019','2018','2017'],
    'ECML-PKDD':['2019','2018','2017'],
    'EDBT':['2020','2019','2018','2017'],
    'ICDM':['2019','2018','2017'],
    'ICDT':['2020','2019','2018','2017'],
    'ISWC':['2019','2018','2017'],
    'PODS':['2019','2018','2017'],
    'SDM':['2019','2018','2017'],
    'WSDM':['2020','2019','2018','2017'],
    }
# 前端不同会议button的颜色
button_color = ['btn btn-success','btn btn-danger','btn btn-warning','btn btn-secondary','btn btn-primary']
rank = {'相关':'similarity','时间':'datetime','被引':'citation'}
test1 = []
for paper in PAPERS[:30]:
    test1.append(paper['paperId'])

# 每页展示
PAPER_NUM = 6
TOTALS = math.ceil(len(PAPERS) / PAPER_NUM)
# 最近的论文
latestPapers = list(db.paper.find().sort('datetime', pymongo.DESCENDING).limit(600))
# latestPapers = [
#         i for i in db.paper.aggregate([{'$match':{'year':'2020'}},{ '$sample':{'size':PAPER_NUM * 100 }}])
#     ]
    # p
class UserForm(FlaskForm):
    username = StringField('username',
                           render_kw={'placeholder': '用户名'},
                           validators=[DataRequired()])
    password = PasswordField('password',
                             render_kw={'placeholder': '密码'},
                             validators=[DataRequired()])
    submit = SubmitField(label='确定')


class InterestForm(FlaskForm):
    submit = SubmitField(label='确定')

def unique_papers(papers):
    unique_papers = []
    titles = []
    for p in papers:
        if p['title'] not in titles:
            titles.append(p['title'])
            unique_papers.append(p)
    print(len(unique_papers))
    return unique_papers

@app.route('/')
def main():
    journals = []
    # 得到所有的期刊
    for type in all_conference['journal'].keys():
        journals = journals + all_conference['journal'][type]
    conferences = []
    # 得到所有的会议
    for type in all_conference['conference'].keys():
        conferences += all_conference['conference'][type]
    print(conferences)
    # 所有论文的数量
    paperNum = db.paper.find({}).count()
    conferenceAndJournalNum = 0
    for key in all_conference.keys():
        for value in all_conference[key].values():
            conferenceAndJournalNum += len(value)
    # 代码数量
    codeNum = db.paper.find({'code':{'$regex':'http'}}).count()
    return render_template('main.html',
                           conferences=conferences,
                           journals=journals,
                           paperNum=format(paperNum,','),
                           conferenceAndJournalNum=format(conferenceAndJournalNum,','),
                           codeNum=format(codeNum,','))
@app.route('/query')
def query():
    # 给标题创建索引
    # db.paper.create_index([('title', pymongo.TEXT)])
    rankBy = request.args.get('rankBy') if request.args.get('rankBy') else '相关' #默认按时间排序
    code = request.args.get('code',type=str,default='')
    logout = request.args.get('logout')
    latest = request.args.get('/?latest=true')
    if 'user' in session:
        print(f"user in session: {session['user']}")
    if 'user' not in session or logout == 'true':
        session['user'] = ''
    q = request.args.get('q')
    # c代表用户制定在会议c里面查找论文
    c = request.args.get('c', type=str, default='')
    if c:
        total_papers = list(
            db.paper.find({
                'conference':c,
                'code':{'$regex':code},
                '$text': {
                    '$search': q
                }},
                {
                    'score': {
                        '$meta': 'textScore'
                    }}
            ).limit(600).sort([('score',{'$meta': 'textScore'})]))
    else:
        # 在所有论文中查找
        total_papers = list(
            db.paper.find({
                'code': {'$regex': code},
                '$text': {
                    '$search': q
                }},
                {
                    'score': {
                        '$meta': 'textScore'
                    }}
            ).limit(600).sort([('score', {'$meta': 'textScore'})]))
    if len(total_papers) == 0:
        # 如果上述搜索结果为零，再去中文文献集合中查找
        qJieba = ' '.join(jieba.cut_for_search(q))
        if qJieba.find("\"") != -1:
            qJieba = qJieba.replace("\" ","\"").replace(" \"","\"")
        elif qJieba.find("-"):
            qJieba = qJieba.replace("- ","-")
        else:
            pass
        if c:
            total_papers = list(
                db.ChinesePaper.find({
                    'conference': c,
                    'code': {'$regex': code},
                    '$text': {
                        '$search': qJieba
                    }},
                    {
                        'score': {
                            '$meta': 'textScore'
                        }}
                ).limit(600).sort([('score', {'$meta': 'textScore'})]))
        else:
            total_papers = list(
                db.ChinesePaper.find({
                    'code': {'$regex': code},
                    '$text': {
                        '$search': qJieba
                    }},
                    {
                        'score': {
                            '$meta': 'textScore'
                        }}
                ).limit(600).sort([('score', {'$meta': 'textScore'})]))
    q_papers = []
    unique_title = []

    for p in total_papers:
        if p['title'] not in unique_title:
            unique_title.append(p['title'])
            q_papers.append(p)
    page = request.args.get(get_page_parameter(), type=int, default=1)  # 1
    pagination = Pagination(page=page, total=len(q_papers), css_framework="foundation",per_page=PAPER_NUM)
    for i,paper in enumerate(q_papers):
        q_papers[i]['datetime'] = int(paper['datetime'].replace('-',''))
    if rankBy != '相关':
        q_papers.sort(key = lambda k: k.get(rank[rankBy], 0),reverse = True)
    papers = q_papers[PAPER_NUM * (page - 1):PAPER_NUM * page]
    for i,paper in enumerate(papers):
        q_papers[i]['datetime'] = str(paper['datetime'])[:4] + '-' + str(paper['datetime'])[4:6] + '-' + str(paper['datetime'])[6:]
    '''中文文献与英文文献显示的摘要字数不一样'''
    for p in papers:
        if p['conference'] not in ['计算机学报', '软件学报', '计算机研究与发展']:
            p['abstract'] = ' '.join(p['abstract'].split(' ')[:40]).rstrip('...') + '...'
        else:
            p['abstract'] = p['abstract'][:180].rstrip('...') + '...'
    return render_template('query.html',
                           rankBy = rankBy,
                           c=c,
                           papers=papers,
                           pagination = pagination,
                           page=page,
                           keyword=q,
                           user=session['user'])
@app.route('/recommend')
def recommend(user=''):
    logout = request.args.get('logout')
    # latest = request.args.get('/?latest=true')
    page = request.args.get(get_page_parameter(), type=int, default=1)  # 1
    if 'user' not in session or logout == 'true':
        session['user'] = ''

    if session['user'] == '' or db.user.find({'user': session['user']}):
        papers = PAPERS[PAPER_NUM * (page - 1):PAPER_NUM * page]
        pagination = Pagination(page=page, total=len(PAPERS), css_framework="foundation",
                                per_page=PAPER_NUM)
    # 中文文献与英文文献的摘要字数不一样
    for p in papers:
        if p['conference'] not in ['计算机学报', '软件学报', '计算机研究与发展']:
            p['abstract'] = ' '.join(p['abstract'].split(' ')[:40]) + '...'
        else:
            p['abstract'] = p['abstract'][:180] + '...'
    return render_template('index.html',
                           papers=papers,
                           page=page,
                           pagination = pagination,
                           # totals=paginate_list(page),
                           user=session['user'])


@app.route('/latest')
def latest():
    logout = request.args.get('logout')
    # latest = request.args.get('/?latest=true')
    page = request.args.get(get_page_parameter(), type=int, default=1)
    paper = db.paper.aggregate([{ '$sample':{'size':PAPER_NUM }}])
    # 默认最多显示100页最新论文
    pagination = Pagination(page=page,total= len(latestPapers), css_framework="foundation",per_page=PAPER_NUM)
    latestCurrentPapers = latestPapers[(page - 1)*PAPER_NUM : page * PAPER_NUM]
    print(latestPapers[(page - 1)*PAPER_NUM : page * PAPER_NUM])
    for p in latestCurrentPapers:
        if p['conference'] not in ['计算机学报', '软件学报', '计算机研究与发展']:
            p['abstract'] = ' '.join(p['abstract'].split(' ')[:40]).rstrip('...') + '...'
        else:
            p['abstract'] = p['abstract'][:180].rstrip('...') + '...'
    if 'user' in session:
        print(f"user in session: {session['user']}")
    if 'user' not in session or logout == 'true':
        session['user'] = ''
    return render_template('index.html',
                           papers=latestCurrentPapers,
                           page=page,
                           user=session['user'],
                           pagination =pagination,
                           show='latest')


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = UserForm()
    status = request.args.get('status')
    print(f"status is {status} and user is {session['user']}")
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        print(f'username is {username}, password is {password}')
        '''register'''
        if status == 'register':
            u = db.users.find_one({'username': username})
            if not u: #判断用户名是否已经被注册
                db.users.insert_one({'username':username,'password':password})
                session['user'] = username
                return redirect(url_for('interest'))
            else:
                session['user'] = ''
                return render_template('login.html',
                                       form=form,
                                       user = session['user'],
                                       status=status,
                                       errorInfo = 'register')
        # login
        else:
            u = db.users.find_one({'username':username})
            if u and u['password'] == password:
                session['user'] = username
                return redirect(url_for('recommend', user=username))

            else:
                session['user'] = ''
                return render_template('login.html',
                                       form=form,
                                       user=session['user'],
                                       status=status,
                                       errorInfo='login')
    return render_template('login.html',
                           status=status,
                           form=form,
                           user=session['user'])


@app.route('/about')
def about():
    if 'user' in session:
        user = session['user']
    else:
        user=''
    return render_template('about.html', user=user)


@app.route('/interest')
def interest():
    logout = request.args.get('logout')
    latest = request.args.get('/?latest=true')
    if 'user' in session:
        print(f"user in session: {session['user']}")
    if 'user' not in session or logout == 'true':
        session['user'] = ''    
    form = InterestForm()
    return render_template('interest.html', form=form, user=session['user'])


@app.route('/dataset')
def dataset():
    logout = request.args.get('logout')
    if 'user' in session:
        print(f"user in session: {session['user']}")
    if 'user' not in session or logout == 'true':
        session['user'] = ''
    return render_template('dataset.html', user=session['user'])

@app.route('/conference',methods = ['GET','POST'])
def conference():
    logout = request.args.get('logout')
    # 按照时间还是被引用次数排序
    rankBy = request.args.get('rankBy') if request.args.get('rankBy') else '时间' #默认按时间排序
    # 是否只看代码
    code= request.args.get('code', type=str, default='')
    # 选择期刊还是会议
    journalOrConference = request.args.get('journalOrConference') if request.args.get('journalOrConference') else 'conference'
    conference_type = request.args.get('type', type=str, default='CCF-AI-A') if journalOrConference == 'conference' else list(all_conference['journal'].keys())[0]#中文期刊
    # name为会议或者期刊的名字
    if request.args.get('name'):
        for key,value in all_conference.items():
            if request.args.get('name') in value:
                conference_type = key
    # 默认展示页面第一个会议的最近年份的论文
    conference = request.args.get('name') if request.args.get('name') else all_conference[journalOrConference][conference_type][0]
    year = request.args.get('year') if request.args.get('year') else '2019'
    page = request.args.get(get_page_parameter(), type=int, default=1)
    if 'user' in session:
        print(f"user in session: {session['user']}")
    if 'user' not in session or logout == 'true':
        session['user'] = ''
    # 得到某一类下的所有会议
    conferences = all_conference[journalOrConference][conference_type]
    conference_button_color = {}
    for c in enumerate(conferences):
        # 每两个按钮换一次颜色
        conference_button_color[c[1]] = button_color[c[0]//2%len(button_color)]
    print(code)
    current_page_papers = list(db.paper.find({
        'year':year,
        'conference':conference,
        'code':{'$regex':code}
    }).skip(PAPER_NUM*(page-1)).sort(rank[rankBy], pymongo.DESCENDING).limit(PAPER_NUM))
    # 分页
    pagination = Pagination(page=page, total=db.paper.find({ 'year':year,'conference':conference}).count(),css_framework="foundation",per_page=PAPER_NUM)
    for p in current_page_papers:
        if p['conference'] not in ['计算机学报','软件学报','计算机研究与发展']:
            p['abstract'] = ' '.join(p['abstract'].split(' ')[:40]).rstrip('...') + '...'
        else:
            p['abstract'] = p['abstract'][:180].rstrip('...') + '...'
    return render_template('conference.html',
                           current_page_papers=current_page_papers,
                           page=page,
                           year=year,
                           rankBy = rankBy,
                           types = all_conference[journalOrConference].keys(),
                           journalOrConference = journalOrConference,
                           conference=conference,
                           user=session['user'],
                           pagination=pagination,
                           conferences = conferences,
                           conference_years = conference_years,
                           conference_button_color=conference_button_color,
                           conference_type = conference_type
                           )

@app.route('/home',methods = ['GET','POST'])
def home():
    user = session['user']
    choice = request.args.get('choice')
    '''c->create collection n->the name of the collection'''
    if request.args.get('c'):
        useCollection=db.collec.find_one({
            'user':user
        })
        files = []
        # 如果该用户还未添加任何收藏夹，则为该用户初始化数据库的数据
        if useCollection == None:
            db.collec.insert_one({'user':user,'files':[]})
            useCollection = db.collec.find_one({
                'user': user
            })
        # 用户收藏夹的名字不能重复
        if request.args.get('n') not in files:
            files = useCollection['files']
            files.append(request.args.get('n'))
            db.collec.update_one(
                {
                    'user':user
                },{
                  '$set':{
                      'files':files,
                      request.args.get('n'): []
                  }
                }
            )
        return render_template('home.html',
                               user=user,
                               choice = 'collection',
                               files = files
                               )
    # 用户收藏版块的页面
    if choice == 'collection':
        useCollection = db.collec.find_one({
            'user': user
        })
        if useCollection == None:
            useCollection={'files':[]}
        return  render_template('home.html',
                                user = user,
                                choice=choice,
                                files = useCollection['files'])
    # 对指定收藏夹生成相似论文
    elif choice == 'collectionSimilarPaper':
        # 取前60篇
        collectionSimilarPapers=[db.paper.find_one({'paperId':paperId}) for num,paperId in enumerate(user_sim[user][request.args.get('collectionName')]) if num < 60]
        print('collectionSimilarPapers:',collectionSimilarPapers)
        return render_template('home.html',
                               choice='collectionSimilarPaper',
                               user=session['user'],
                               collectionSimilarPapers=collectionSimilarPapers)

    # 查看收藏夹的内容
    elif choice == 'collectionContent':
        collectionName = request.args.get('collectionName')
        collectionContent = db.collec.find_one({
            'user': user
        })[collectionName]
        return render_template('home.html',
                               choice='collectionContent',
                               user=session['user'],
                               collection = collectionName,
                               collectionContent=collectionContent)
    # 删除某收藏夹
    elif choice =='collectionDelete':
        collectionName=request.args.get('collectionName')
        files = db.collec.find_one({'user':user})['files']
        collectionFiles = [f for f in files if f != collectionName]
        db.collec.update_one({
            'user':user
        },{
            '$set':{'files':collectionFiles},
            '$unset': {collectionName: 1}
        })
        useCollection = db.collec.find_one({
            'user':user
        })
        return render_template('home.html',
                               user=user,
                               choice='collection',
                               files=useCollection['files'])
    # 删除收藏夹里的某篇论文
    elif choice == 'paperDelete':
        paperId = request.args.get('paperId',type=str,default = '')
        collectionName = request.args.get('collectionName')
        papers = db.collec.find_one({'user': user})[collectionName]
        newPapers = [p for p in papers if p['paperId'] != paperId]
        db.collec.update_one({
            'user': user
        }, {
            '$set': {collectionName: newPapers},
        })
        useCollection = db.collec.find_one({
            'user': user
        })
        return render_template('home.html',
                               user=user,
                               choice='collectionContent',
                               files=useCollection[collectionName])
    # 用户浏览记录页面
    else:
        user_data = list(
            db.user.find({
                'user': user
            }).sort('date', pymongo.DESCENDING))
        for i in range(len(user_data)):
            user_data[i]['num'] = i + 1
        return render_template('home.html', user_data=user_data, user=user,choice = choice)
# 记录用户的浏览记录
@app.route('/record', methods=['POST', 'GET'])
def record():
    data = request.json
    paperId = data['id']
    user = session['user']
    print('record:',paperId)
    res = list(db.user.find({'user': user, 'paperId': paperId}))
    print("res:",res)
    paper = db.paper.find_one({'paperId': paperId})
    if len(res) == 0:
        date = datetime.now().strftime('%Y-%m-%d')
        print(date)
        db.user.insert_one({
            'user': user,
            'code': paper['code'],
            'title': paper['title'],
            'date': date
        })
    else:
        date = datetime.now().strftime('%Y-%m-%d')
        db.user.update_one({
            'user': user,
            'title': paper['title']
        }, {'$set': {
            'date': date,
        }})
    return render_template_string('Add log data to dataset.')

@app.route('/paperPage',methods=['POST', 'GET'])
def paperPage():
    print('herehere')
    user = session['user']
    logout = request.args.get('logout')
    paperId  = request.args.get('paperId')
    # 用户评论版块相关代码
    # if request.args.get('commentSubmit') == 'True':
    #     db.paperInfo.update_one({
    #         'paperId':paperId
    #     },{
    #         '$addToSet':{
    #             'reviews':{'content':request.args.get('comment'),'reviewer':user,'time':datetime.today().strftime('%Y-%m-%d')}
    #         }
    #     })
    similarPaperId = sim_dict[paperId]
    similarPapers = [db.paper.find_one({'paperId':pid}) for num,pid in enumerate(similarPaperId) if num < 10 and pid != paperId]
    paperInfo = db.paper.find_one({
        'paperId': paperId
    })
    '''
    评论版块 关闭
        reviews = db.paperInfo.find_one({
        'paperId':paperId
    }
    )['reviews']
    '''
    # 返回用户收藏夹列表
    useCollection = db.collec.find_one({
        'user': user
    })
    if useCollection == None:
        collections=[]
    else:
        collections = useCollection['files']
    if 'user' in session:
        print(f"user in session: {session['user']}")
    if 'user' not in session or logout == 'true':
        session['user'] = ''
    collectionName = request.args.get('whichCollection')
    if collectionName: #将paperInfo存到collection中
        print('addtoset ',collectionName)
        print(type(paperInfo))
        db.collec.update_one({
            'user': user
        }, {
            '$addToSet': {
                collectionName: paperInfo
            }
        })
        return render_template('paperPage.html',
                               user=session['user'],
                               paperInfo=paperInfo)

    return render_template('paperPage.html',
                           user=user,
                           paperInfo=paperInfo,
                           # reviews = reviews,
                           similarPapers=similarPapers,
                           collections = collections
                           )

if __name__ == '__main__':
    print('loading paper similarities', Config.sim_path)
    sim_dict = pickle.load(open(Config.sim_path, "rb"))
    print('loading user recommendations', Config.user_sim_path)
    user_sim = {}
    if os.path.isfile(Config.user_sim_path):
        user_sim = pickle.load(open(Config.user_sim_path, 'rb'))
    app.run(host='127.0.0.1', debug=True)

