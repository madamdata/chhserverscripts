import mailbox
import os
import datetime
from email.header import decode_header

mailboxlist = ['a', 'b', 'c']
# mailboxlist = ['a']
mailboxes = {}
for mb in mailboxlist:
    mailboxes[mb] = mailbox.Maildir('/home/pi/mailtest/'+mb, factory=None, create=False)

a = mailboxes['a']
numMessages = len(a.keys())
# print(mailboxes)

def next_path(path_pattern, ext):
    """
    Finds the next free path in an sequentially named list of files

    e.g. path_pattern = 'file-%s.txt':

    file-1.txt
    file-2.txt
    file-3.txt

    Runs in log(n) time where n is the number of existing files in sequence
    """
    i = 1

    # First do an exponential search
    while os.path.exists(path_pattern % i + ext):
        i = i * 2

    # Result lies somewhere in the interval (i/2..i]
    # We call this interval (a..b] and narrow it down until a + 1 = b
    a, b = (i // 2, i)
    while a + 1 < b:
        c = (a + b) // 2 # interval midpoint
        a, b = (c, b) if os.path.exists(path_pattern % c) else (a, c)

    return path_pattern % b + ext


for boxname, box in mailboxes.items():
    for key, msg in box.iteritems():
        if msg.get_subdir() == 'new':
            msg.set_subdir('cur')
            msg.add_flag('S')
            sender = msg['From']
            datestring = datetime.datetime.now().strftime("%d%b%Y")
            for x in msg.walk():                                #msg.walk() goes through all the subparts depth-first
                if x.get_content_disposition() == 'attachment': #is this subpart an attachment? 
                    rawfilename = x.get_filename()
                    # print(rawfilename)
                    filename, charset = decode_header(rawfilename)[0]
                    if charset == 'utf-8':
                        filename = filename.decode('utf-8')
                    elif charset == None:
                        filename = filename
                    else: 
                        print("Can't tell what encoding the filename is.")
                        filename = rawfilename
                    filename, ext = os.path.splitext(filename)
                    filename = boxname + "-" + filename + "-" + datestring + ext
                    filename = filename.replace(" ", "")
                    print(datestring + ": attachment found: " + x.get_content_type() + ": " + filename)
                    filepath = '/home/pi/mailtest/attachTest/' + boxname + "/" + filename
                    if os.path.exists(filepath):                #check for duplicates and increment file name if needed.
                        print(filepath + " : File with that name exists already! Incrementing file name.")
                        path, ext = os.path.splitext(filepath)
                        path = path + "(%s)"
                        filepath = next_path(path, ext)
                        # print(filepath)

                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, 'wb') as fp:
                        fp.write(x.get_payload(decode=True)) #unpack the payload into an actual file
            box.update({key:msg}) #add the --modified-- message, with new flags and subdir, to the mailbox. Remember that 'msg' has no necessary relation to the actual file in the mailbox - it's just a representation that we manipulate. 


            

