import mailbox
import os

mailboxlist = ['a', 'b', 'c']
# mailboxlist = ['a']
mailboxes = {}
for mb in mailboxlist:
    mailboxes[mb] = mailbox.Maildir('/home/pi/mailtest/'+mb, factory=None, create=False)

a = mailboxes['a']
numMessages = len(a.keys())
# print(mailboxes)

for boxname, box in mailboxes.items():
    for key, msg in box.iteritems():
        if msg.get_subdir() == 'new':
            msg.set_subdir('cur')
            msg.add_flag('S')
            sender = msg['From']
            for x in msg.walk():                                #msg.walk() goes through all the subparts depth-first
                if x.get_content_disposition() == 'attachment': #is this subpart an attachment? 
                    filename = sender + x.get_filename()
                    filename = filename.replace(" ", "")
                    filename = filename.replace("<", "-")
                    filename = filename.replace(">", "-")
                    print("attachment found: " + x.get_content_type() + ": " + filename)
                    filepath = '/home/pi/mailtest/attachTest/' + boxname + "/" + filename
                    if os.path.exists(filepath):                #check for duplicates
                        print(filepath + " : File exists already! Not writing a new one.")
                    else:
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        with open(filepath, 'wb') as fp:
                            fp.write(x.get_payload(decode=True)) #unpack the payload into an actual file
            box.update({key:msg}) #add the --modified-- message, with new flags and subdir, to the mailbox. Remember that 'msg' has no necessary relation to the actual file in the mailbox - it's just a representation that we manipulate. 


            

#testing vim scp 1 2 3 4 5 commit
