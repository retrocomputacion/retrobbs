###############################################################################
# Basic Database functionality
# Mainly user stuff
###############################################################################

from tinydb import TinyDB, Query, where
from tinydb.operations import increment
import hashlib
import os
import time
import re
from collections import deque

#Dictionary of user editable fields, for some future use?
# [field name, field type, [field length range]]
# field type: 0 Text
#             1 Password
#             2 Date
#             3 Integer
User_Fields = {'User name':['uname',0,[6,15]], 'Password':['pass',1,[6,15]], 'First name':['fname',0,[1,15]], 'Last name':['lname',0,[1,15]],
                'Birthdate':['bday',2,[10,10]], 'Country':['country',0,[2,15]]}

######### DBase class #########
class DBase:
    def __init__(self,path):
    #Open DataBase
        #Only the main script should call this
        self.db = TinyDB(path+'db.json',sort_keys=True, indent=4)
        table = self.db.table('USERS')
        table.update({'online':0})  #Logoff any stray user from last time the BBS was run

    #Close DataBase
    def closeDB(self):
        #Only the main script should call this
        self.db.close()

    ################################
    # User related functions
    ################################

    #Get all users
    #Return list of (id,username) pairs
    def getUsers(self):
        table = self.db.table('USERS')
        ul = []
        for u in table.all():
            ul.append((u.doc_id,u['uname'],u['uclass']))
        return ul

    #Check if user exists
    #Return dictionary, or None if not found
    def chkUser(self, username):
        table = self.db.table('USERS')
        dbQ = Query()
        return table.get(dbQ.uname.search('^'+username+'$',flags=re.IGNORECASE))

    #Check if password matches for the user, and optionally login
    #uentry must be a dictionary
    def chkPW(self, uentry, pw, login = True):
        upw = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), bytes.fromhex(uentry['salt']),100000)
        if upw.hex() == uentry['pass']:
            if login:
                dbQ = Query()
                table = self.db.table('USERS')
                table.update({'lastlogin':time.time(),'online':1}, dbQ.uname == uentry['uname'])
                table.update(increment('visits'), dbQ.uname == uentry['uname'])
            return(True)
        return(False)

    #Logoff user (by id)
    #updates total data transferred
    def logoff(self, id, dbytes, ubytes):
        table = self.db.table('USERS')
        ud = table.get(doc_id=id)
        tt = ud.get('totaltime',0)
        table.update({'online':0, 
                      'upbytes':ud.get('upbytes',0)+ubytes,
                      'downbytes':ud.get('downbytes',0)+dbytes,
                      'totaltime':tt+(time.time()-ud.get('lastlogin',0))},
                     doc_ids=[id])

    #Creates a new user
    def newUser(self, uname, pw, fname, lname, bday, country,uclass=1):
        #Make sure user doesnt already exists
        if self.chkUser(uname) == None:
            table = self.db.table('USERS')
            salt = os.urandom(32)   #New salt for this user
            upw = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt,100000)
            return table.insert({'uname':uname,
                                 'salt':salt.hex(),
                                 'pass':upw.hex(),
                                 'fname':fname,
                                 'lname':lname,
                                 'bday':bday,
                                 'country':country,
                                 'uclass':uclass,
                                 'lastlogin':time.time(),
                                 'joindate':time.time(),
                                 'totaltime':0,
                                 'visits':1,
                                 'online':1})

    #Update user data (by id)
    #Pass untouched fields as None
    def updateUser(self, id, uname, pw, fname, lname, bday, country,uclass):
        temp = locals()
        temp.pop('db',None)
        temp.pop('id',None)
        temp.pop('pw',None)
        table = self.db.table('USERS')
        data = table.get(doc_id = id)
        if pw != None:
            temp['pass'] = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), bytes.fromhex(data['salt']),100000).hex()
        params = {}
        for x,v in temp.items():
            if v != None:
                params[x]=v
        params.pop('self')
        table.update(params, doc_ids=[id])

    #Get user preferences
    def getUserPrefs(self,id,defaults = {}):
        table = self.db.table('USERS')
        data = table.get(doc_id = id)
        if data != None:
            prefs = data.get('preferences',defaults)
            defaults.update(prefs)
        return defaults

    #Update user preferences
    def updateUserPrefs(self,id,prefs:dict):
        table = self.db.table('USERS')
        data = table.get(doc_id = id)
        oldp:dict = data.get('preferences',{})
        oldp.update(prefs)
        table.update({'preferences':oldp}, doc_ids=[id])
    
    ################################
    # BBS session functions
    ################################

    #Increment visitor count
    def newVisit(self, uname='-Guest-'):
        table = self.db
        dbQ = Query()
        if table.get(dbQ.record == 'bbs_stats') == None:
            table.insert({'record':'bbs_stats','visits':1,'latest':[uname]})
        else:
            ut = table.get(dbQ.record == 'bbs_stats')
            lu = ut.get('latest')
            if lu == None:
                lu = []
            v = ut.get('visits')
            if v == None:
                table.update({'visits':0},dbQ.record == 'bbs_stats')
            lu = deque(lu,10)
            lu.appendleft(uname)
            table.update_multiple([(increment('visits'), where('record') == 'bbs_stats'),({'latest':list(lu)}, where('record') == 'bbs_stats')])
    
    #Return the BBS stats db record
    def bbsStats(self):
        table = self.db
        dbQ = Query()
        return table.get(dbQ.record == 'bbs_stats')
    
    #Update total uptime
    #Pass stime = 0 to just return the actual stored uptime
    def uptime(self, stime):
        table = self.db
        dbQ = Query()
        ut = table.get(dbQ.record == 'bbs_stats')
        if ut == None:
            table.insert({'record':'bbs_stats','uptime':stime})
            tt = stime
        else:
            tt = ut.get('uptime',0)
            if stime != 0:
                table.update({'uptime':tt+stime}, dbQ.record == 'bbs_stats')
        return tt