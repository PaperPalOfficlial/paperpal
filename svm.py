import os
import sys
import pickle
import numpy as np
from sklearn import svm
from pymongo import MongoClient

client = MongoClient()
db = client.PaperPal

# intermediate pickles
tfidf_path = 'tfidf.p'
meta_path = 'tfidf_meta.p'
sim_path = 'sim_dict.p'
user_sim_path = 'user_sim.p'

user_data = list(db.user.find())
users = set()
for user in user_data:
    users.add(user['user'])

num_recommendations = 100  # papers to recommend per user

# load the tfidf matrix and meta
with open(meta_path, 'rb') as f:
    meta = pickle.load(f)

with open(tfidf_path, 'rb') as f:
    out = pickle.load(f)

X = out['X']
X = X.todense()

# pid -> idx
xtoi = {x: i for x, i in meta['ptoi'].items()}

user_sim = {}
print(f'users = {users}')
for ii, u in enumerate(users):
    print("{}/{} building an SVM for {}".format(
        ii, len(users), u.encode('utf-8')))
    read_papers = list(db.user.find({'user': u}))
    pids = [paper['paperId'] for paper in read_papers]
    y = np.zeros(X.shape[0])
    for ix in pids:
        y[xtoi[ix]] = 1
    clf = svm.LinearSVC(class_weight='balanced', verbose=False,
                        max_iter=10000, tol=1e-6, C=0.1)
    clf.fit(X, y)
    s = clf.decision_function(X)
    sortix = np.argsort(-s)
    sortix = sortix[:min(num_recommendations, len(sortix))]
    user_sim[u] = [meta['pids'][ix] for ix in sortix]

print('writing', user_sim_path)
with open(user_sim_path, 'wb') as f:
    pickle.dump(user_sim, f)
