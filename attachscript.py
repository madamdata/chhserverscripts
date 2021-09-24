import mailbox

mailboxlist = ['a', 'b', 'c']
mailboxes = {}
for mb in mailboxlist:
    mailboxes[mb] = mailbox.Maildir('/home/pi/mailtest/'+mb, factory=None, create=False)

for key in mailboxes['a'].keys():
    msg = mailboxes['a'].get(key)
    sender = msg['From']
    print(sender)
    print(msg.keys())
