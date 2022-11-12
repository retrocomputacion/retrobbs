# RetroBBS Database maintenance tool
# - very early release
# - mostly spaguetti code
# Hopefully I can tidy this up in the future.

from datetime import datetime
import common.dbase as DB
from tinydb.table import Document
from tinydb import Query




print("----RetroBBS Database maintenance tool----\n")

data = DB.DBase()
print("Database open...")
print("Checking database integrity...")
table = data.db.table('USERS')
print("User entries:",len(table))

if len(table)>0:
    admin = False
    for item in table:
        #print(ix, item)
        ix = item.doc_id

        if "salt" not in item:
            print("Entry ",ix," missing salt. DELETING")
            table.remove(doc_ids=[ix])
            continue
        if "pass" not in item:
            print("Entry ",ix," missing password. DELETING")
            table.remove(doc_ids=[ix])
            continue
        if "uname" not in item:
            print("Entry ",ix," missing username. DELETING")
            table.remove(doc_ids=[ix])
            continue

        if "uclass" not in item:
            print("Entry ",ix," missing class. FIXING")
            table.upsert(Document({"uclass":1},doc_id=ix))
        if "lastlogin" not in item:
            print("Entry ",ix," missing last login. FIXING")
            table.upsert(Document({"lastlogin":0},doc_id=ix))
        if "fname" not in item:
            print("Entry ",ix," missing first name. FIXING")
            table.upsert(Document({"fname":""},doc_id=ix))
        if "lname" not in item:
            print("Entry ",ix," missing last name. FIXING")
            table.upsert(Document({"lname":""},doc_id=ix))
        if "bday" not in item:
            print("Entry ",ix," missing birthday. FIXING")
            table.upsert(Document({"bday":"01/01/1970"},doc_id=ix))
        if "country" not in item:
            print("Entry ",ix," missing country. FIXING")
            table.upsert(Document({"country":""},doc_id=ix))
        if "joindate" not in item:
            print("Entry ",ix," missing join date. FIXING")
            table.upsert(Document({"joindate":0},doc_id=ix))
        if "visits" not in item:
            print("Entry ",ix," missing visit count. FIXING")
            table.upsert(Document({"visits":1},doc_id=ix))
        if "online" not in item:
            print("Entry ",ix," missing online flag. FIXING")
            table.upsert(Document({"online":0},doc_id=ix))
        if item['uclass'] == 10:
            admin = True

    if admin == False:
        print("Warning: no admin user(s) present")
        while True:
            a= input("Select an admin user? (Y/N) ")
            user = Query()
            if (a == 'Y') or (a == 'y'):
                user = Query()
                while True:
                    uname = input("Admin username: ")
                    entry = table.search(user.uname == uname)
                    if entry != []:
                        table.update({'uclass':10},user.uname == uname)
                        break
                break
            elif (a == 'N') or (a == 'n'):
                break

mtable = data.db.table('MESSAGES')
print('Total messages:',len(mtable))
if len(mtable) > 0:
    Q = Query()
    threads = mtable.search(Q.msg_parent == 0)
    if len(threads)>0:
        # iterate threads
        for t in threads:
            i = t.doc_id
            tm = mtable.search(Q.msg_parent == i)   # messages linked to this thread
            if len(tm)>0:
                # get a list of thread message ids
                m_ids = [i.doc_id for i in tm]
                n1 = t
                while True:
                    if n1['msg_next'] != 0:
                        n1 = mtable.get(doc_id=n1['msg_next'])
                        if n1.doc_id in m_ids:
                            m_ids.remove(n1.doc_id)
                        else:
                            print("Error: Reply with wrong parent message.")
                            a = input("(F)ix or (U)nlink from thread")
                        ...
                    else:
                        break
                if len(m_ids)>0:    #There's messages with parent t not in the linked list
                    print("There's ",len(m_ids),' orphaned messages associated with thread id:',i)
                    # find which ones actually correspond to the existing thread
                    l_msgs = mtable.search(Q.fragment({'msg_parent':i,'msg_topic':t['msg_topic']}))
                    for om in l_msgs:
                        if om.doc_id in m_ids:
                            # Orphaned message has correct topic, insert it chronologically
                            ...
                            m_ids.remove(om.doc_id)
                    # Remaining ids in m_ids are truly orphaned messages from previously deleted threads
                    print('Deleting ',len(m_ids),' truly orphaned message(s)')
                    mtable.remove(doc_ids=m_ids)
        ...
    else:
        print("All ",len(mtable),' existing messages are orphaned. Purging message database.')
        mtable.truncate()
        



while True:
    print("---------------------\nPlease select action:\n---------------------")
    if len(table) > 0:
        print("1: Update user data")
        print("2: Delete user")
    print("3: Add user")
    print("0: Quit\n")
    ii = input("Your selection:")
    #### QUIT ####
    if ii == '0':
        break
    #### UPDATE ####
    if ii == '1' and len(table) > 0:
        change = False
        while True:
            un = input("User Name:")
            ud = data.chkUser(un)
            if ud != None:
                break
            else:
                print("----- User not found -----")
        ud = ud[0]

        print("Username:",ud['uname'])
        while True:
            uname = input("New username (enter skip):")
            if uname == '':
                uname = None
                break
            else:
                if 6<=len(uname)<=16:
                    if uname != '_guest_':
                        change = True
                        break
                else:
                    print("Username must be 6 to 16 characters long")

        print("Password: ******")
        while True:
            pw = input("New password (6+ chars, enter to skip):")
            if pw == '':
                pw = None
                break
            elif 6<=len(pw)<=16:
                change = True
                break
            else:
                print("Password must be 6 to 16 characters long")

        print("First name:",ud['fname'])
        while True:
            fname = input("New first name (enter skip):")
            if fname == '':
                fname = None
                break
            elif len(fname)<=16:
                change = True
                break
            else:
                print("New first name must be 16 characters or less")

        print("Last name:",ud['lname'])
        while True:
            lname = input("New last name (enter skip):")
            if lname == '':
                lname = None
                break
            elif len(lname)<=16:
                change = True
                break
            else:
                print("New last name must be 16 characters or less")
        print("Birthday:",ud['bday'])
        
        while True:
            bday = input("New birthday DD/MM/YYYY (enter skip):")
            if bday == '':
                bday = None
                break
            else:
                try:
                    datetime.strptime(bday,'%d/%m/%Y')
                    change = True
                    break
                except:
                    ...

        print("Country:",ud['country'])
        while True:
            country = input("New country (enter skip):")
            if country == '':
                country = None
                break
            elif len(country)<=16:
                change = True
                break
            else:
                print("New country must be 16 characters or less")

        print("Class:",ud['uclass'])
        while True:
            uclass = input("New class 1-10 (enter skip):")
            if uclass == '':
                uclass = None
                break
            elif 1<=int(uclass)<=10:
                change = True
                uclass = int(uclass)
                break
            else:
                print("New class must be between 1 and 10(admin)")

        if change:
            data.updateUser(ud.doc_id,uname,pw,fname,lname,bday,country,uclass)
            print("\n----- User data updated -----\n")

    #### DELETE ####
    if ii == '2' and len(table) > 0:
        while True:
            un = input("User Name:")
            ud = data.chkUser(un)
            if ud != None:
                break
            else:
                print("----- User not found -----")
        #ud = ud[0]
        Q = Query()
        if input("Are you sure you want to delete this user? ") == 'y':
            uid = ud.doc_id
            table.remove(Q.uname == un)
            print("\n----- USER DELETED -----\n")
            print("Updating messages...")
            mtable.update({'msg_to':un}, Q.msg_to == uid)
            mtable.update({'msg_from':un}, Q.msg_from == uid)

    #### ADD NEW USER ####
    if ii == '3':
        while True:
            uname = input("User Name:")
            if not(6 <= len(uname) <= 16):
                print("----- User name should be between 6 and 16 characters long -----")
            else:
                ud = data.chkUser(uname)
                if ud != None:
                    print("----- User already exists -----")
                else:
                    break
        while True:
            pw = input("Password (6 to 16 chars):")
            if 6 <= len(pw) <= 16:
                break
        while True:
            fname = input("First name (enter skip):")
            if len(fname) < 17:
                break
        while True:
            lname = input("Last name (enter skip):")
            if len(lname) < 17:
                break
        bday = input("Birthday DD/MM/YYYY (warning, no sanity check performed):")
        if bday == '':
            bday = "01/01/1970"
        while True:
            country = input("Country (enter skip):")
            if len(country) < 17:
                break
        while True:
            uclass = input("New class 1-10 (enter 1):")
            if uclass == '':
                uclass = 1
                break
            elif 1<=int(uclass)<=10:
                change = True
                uclass = int(uclass)
                break
            else:
                print("New class must be between 1 and 10(admin)")
        data.newUser(uname,pw,fname,lname,bday,country,uclass)
        print("\n----- New user added -----\n")

print("Closing database")
data.closeDB()
