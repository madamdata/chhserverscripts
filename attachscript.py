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
    for x in msg.walk():
        if x.get_content_disposition() == 'attachment':
            filename = sender + x.get_filename()
            filename = filename.replace(" ", "")
            filename = filename.replace("<", "-")
            filename = filename.replace(">", "-")
            print("ATTACHMENT FOUND!!")
            print(x.get_content_type())
            print(filename)
            with open('/home/pi/mailtest/attachTest/'+filename, 'wb') as fp:
                fp.write(x.get_payload(decode=True))
            

#testing vim scp 1 2 3 4 5 commit
