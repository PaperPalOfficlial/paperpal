import os
import pickle
from random import shuffle, seed

import numpy as np
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm

seed(123)
max_train = 5000
max_features = 300

# intermediate pickles
tfidf_path = 'tfidf.p'
meta_path = 'tfidf_meta.p'
sim_path = 'sim_dict.p'
user_sim_path = 'user_sim.p'

# sql database file
db_serve_path = 'db2.p'  # an enriched db.p with various preprocessing info
database_path = 'as.db'
serve_cache_path = 'serve_cache.p'
client = MongoClient('127.0.0.1',27017)

# client = MongoClient()
db = client.PaperPal
papers = list(db.paper.find())

# 从数据库中读取 pid 和 abstract
txts, pids = [], []
for paper in tqdm(papers):
    pid = paper['paperId']
    txt = paper['abstract'].replace('Abstract: ', '').strip()
    txts.append(txt)
    pids.append(pid)

# 用 tfidf 提取特征
v = TfidfVectorizer(input='content',
                    encoding='utf-8',
                    decode_error='replace',
                    strip_accents='unicode',
                    lowercase=True,
                    analyzer='word',
                    stop_words='english',
                    ngram_range=(1, 2),
                    norm='l2',
                    max_features=max_features,
                    use_idf=True,
                    smooth_idf=True,
                    token_pattern=r'(?u)\b[a-zA-Z_][a-zA-Z0-9_]+\b',
                    sublinear_tf=True,
                    max_df=1.0,
                    min_df=1)
v.fit(txts)
X = v.transform(txts)  # (1122, 300)

# write full matrix out
out = {}
out['X'] = X  # this one is heavy!
print("writing", tfidf_path)
with open(tfidf_path, 'wb') as f:
    pickle.dump(out, f)

# writing lighter metadata information into a separate (smaller) file
out = {}
out['vocab'] = v.vocabulary_
out['idf'] = v._tfidf.idf_
out['pids'] = pids  # a full idvv string (id and version number)
out['ptoi'] = {x: i for i, x in enumerate(pids)}  # pid to ix in X mapping
print("writing", meta_path)
with open(meta_path, 'wb') as f:
    pickle.dump(out, f)

print("precomputing nearest neighbor queries in batches...")
X = X.todense()  # originally it's a sparse matrix
sim_dict = {}
batch_size = 200
for i in range(0, len(pids), batch_size):
    i1 = min(len(pids), i + batch_size)
    xquery = X[i:i1]  # BxD
    ds = -np.asarray(np.dot(X, xquery.T))  # NxD * DxB => NxB
    IX = np.argsort(ds, axis=0)  # NxB
    for j in range(i1 - i):
        sim_dict[pids[i + j]] = [pids[q] for q in list(IX[:50, j])]
    print('%d/%d...' % (i, len(pids)))

print("writing", sim_path)
with open(sim_path, 'wb') as f:
    pickle.dump(sim_dict, f)
