###############################################################################
# Basic Database functionality
# Mainly user stuff
###############################################################################

from tinydb import TinyDB, Query
from tinydb.operations import increment
import hashlib
import os
import inspect
import time

#Dictionary of user editable fields, for some future use?
# [field name, field type, [field length range]]
# field type: 0 Text
#             1 Password
#             2 Date
#             3 Integer
User_Fields = {'User name':['uname',0,[6,15]], 'Password':['pass',1,[6,15]], 'First name':['fname',0,[1,15]], 'Last name':['lname',0,[1,15]],
                'Birthdate':['bday',2,[10,10]], 'Country':['country',0,[2,15]]}

class DBase:
    def __init__(self):
    #Open DataBase
        #Only the main script should call this
        self.db = TinyDB('bbsfiles/db.json',sort_keys=True, indent=4)
        table = self.db.table('USERS')
        table.update({'online':0})  #Logoff any stray user from last time the BBS was run

    #Close DataBase
    def closeDB(self):
        #Only the main script should call this
        self.db.close()

    #Get all users
    #Return list of [id,username] pairs
    def getUsers(self):
        table = self.db.table('USERS')
        ul = []
        for u in table.all():
            ul.append([u.doc_id,u['uname']])
        return ul

    #Check if user exists
    #Return dictionary, or None if not found
    def chkUser(self, username):
        table = self.db.table('USERS')
        dbQ = Query()
        return table.get(dbQ.uname == username)


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
    def logoff(self, id):
        table = self.db.table('USERS')
        table.update({'online':0}, doc_ids=[id])

    #Creates a new user
    def newUser(self, uname, pw, fname, lname, bday, country):
        #Make sure user doesnt already exists
        if self.chkUser(uname) == None:
            table = self.db.table('USERS')
            salt = os.urandom(32)   #New salt for this user
            upw = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt,100000)
            return table.insert({'uname':uname,'salt':salt.hex(),'pass':upw.hex(),'fname':fname,'lname':lname,'bday':bday,'country':country,'uclass':1,
                                'lastlogin':time.time(),'joindate':time.time(),'visits':1,'online':1})

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
                #data[x]=v
        #dbQ = Query()
        params.pop('self')
        table.update(params, doc_ids=[id])
        