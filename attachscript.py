import mailbox

mailboxlist = ['a', 'b', 'c']
mailboxes = {}
for mb in mailboxlist:
    mailboxes[mb] = mailbox.Maildir('/home/pi/mailtest/'+mb, factory=None, create=False)

a = mailboxes['a']
msg = a.get(a.keys()[3])
for x in msg.walk():
    if x.get_content_disposition() == 'attachment':
        print("ATTACHMENT FOUND!!")

#testing vim scp 1 2 3 4 5 commit
