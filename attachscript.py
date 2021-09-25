import mailbox
import os

mailboxlist = ['a', 'b', 'c']
mailboxes = {}
for mb in mailboxlist:
    mailboxes[mb] = mailbox.Maildir('/home/pi/mailtest/'+mb, factory=None, create=False)

a = mailboxes['a']
numMessages = len(a.keys())

for key in a.keys():
    msg = a.get(key)
    sender = msg['From']
    if msg.get_subdir() == 'new':
        #print(msg.get_subdir())
        # print(msg.get_flags())
        msg.set_subdir('cur')
        msg.add_flag('S')
        for x in msg.walk():
            if x.get_content_disposition() == 'attachment':
                filename = sender + x.get_filename()
                filename = filename.replace(" ", "")
                filename = filename.replace("<", "-")
                filename = filename.replace(">", "-")
                print("attachment found: " + x.get_content_type() + ": " + filename)
                filepath = '/home/pi/mailtest/attachTest/' + filename
                if os.path.exists(filepath): #check for duplicates
                    print(filepath + " : File exists already! Not writing a new one.")
                else:
                    with open(filepath, 'wb') as fp:
                        fp.write(x.get_payload(decode=True)) #unpack the payload into an actual file
        a.update({key:msg}) #add the --modified-- message, with new flags and subdir, to the mailbox. Remember that 'msg' has no necessary relation to the actual file in the mailbox - it's just a representation that we manipulate. 


            

#testing vim scp 1 2 3 4 5 commit
