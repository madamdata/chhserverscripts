import mailbox, os, datetime, dateparser, re
from email.header import decode_header

# ---- path and variable definitions ----
os.chdir('/home/pi/mail/pochhmail') #main mainbox directory. Everything in this script is relative to this path
logfilePath = '../attachments/log/attachscript.log'
synclogPath = '../attachments/log/sync.log'
attachmentFolderPath = '../attachments/'
downloadFolderPath = 'downloaded/'
inboxFolderPath = 'INBOX/'

inbox = mailbox.Maildir(inboxFolderPath, factory=None, create=False)
downloaded = mailbox.Maildir("downloaded", factory=None, create=False) #place to put the downloaded messages

cmdMailbox = mailbox.Maildir('commands', factory=None, create=False) #create a mailbox object for the special logs mailbox

# ---- function definitions ----
def next_path(path_pattern, ext):
    """
    adapted from stackexchange ... 
    adds (1) (2) etc to filenames if a file exists at the specified path
    Runs in log(n) time where n is the number of existing files in sequence (more efficient than a brute force search)
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


# --- MAIN BODY ----

# ---- first, check for commands in the command mailbox ----
for key, msg in cmdMailbox.iteritems():
    if msg.get_subdir() == 'new':
        datestring = datetime.datetime.now().strftime("%d%b%Y-%H:%M")
        subject = msg['Subject']
        if subject == "SENDLOGS": 
            print("SENDLOGS command received at " + datestring)
            cmdMailbox.discard(key) #delete the command message
            logString = open(logfilePath, 'r').read() #open log file and read it to a string
            # --- make a new message object; put the logs in it and format the sender; attach to cmdMailbox --- 
            logMsg = mailbox.MaildirMessage()
            logMsg['From'] = "CHH Mail Processing Server <noreply@chhserver.md>"
            logMsg['Subject'] = "Logs " + datestring
            logMsg.set_payload(logString, "utf-8")
            cmdMailbox.add(logMsg)
        cmdMailbox.flush()
            

msgsToDelete={} #dictionary of messages to delete. will store a unique list of messages to be moved out of the inbox
# ---- next, check the inbox for new attachments ----
for key, msg in inbox.iteritems():            # step through all the mail in the inbox
    if msg.get_subdir() == 'new':
        sender = msg['From']
        tos = msg.get_all('To', [])
        ccs = msg.get_all('Cc', [])
        bccs = msg.get_all('Bcc', [])
        tos = tos + ccs + bccs
        # print(tos)
        to = toComponents = ''
        pathString = pathStringForFilename =  ''
        for addr in tos:
            # to = addr.replace('<', '').replace('>', '').lower()
            # to = msg['To'].split('@')[0].replace("<", "").lower() #grab all the stuff before the '@', then split by '+' and strip any < 
                # print(addr)
            match = re.search(r'po.*@chh.sg', addr)
            try:
                to = match[0]
                to = to.split('@')[0]
                toComponents = to.split('+')
                toComponents.pop(0) #remove 0th element: the 'po' head
            except TypeError:
                pass
                # print("po email not found in 'To' field")
        pathString = '/'.join(toComponents) + '/' #turn it into a path by putting / between items
        pathStringForFilename = '_'.join(toComponents) #with _ instead of / for filename
        currentDatestring = datetime.datetime.now().strftime("%m%d%Y_%H:%M")
        sentDatestring = dateparser.parse(msg['Date']).strftime("%m%d_%Y")

        # ---- subpart handling ----
        for x in msg.walk():                                # msg.walk() goes through all the subparts depth-first
            if x.get_content_disposition() == 'attachment': # proceed only if this subpart is an attachment 

                # ---- figure out what the header is based on RFC 2047 codes - to ensure unicode stuff eg Chinese chars appear correctly --- 
                rawfilename = x.get_filename()
                filename, charset = decode_header(rawfilename)[0] 
                if charset == 'utf-8':
                    filename = filename.decode('utf-8')
                elif charset == None:
                    filename = filename
                else: 
                    print("Can't tell what encoding the filename is.")
                    filename = rawfilename
                    
                # ---- create a filename by adding the name of the box and the date ----
                filename, ext = os.path.splitext(filename)
                filename = pathStringForFilename + "__" + filename + "__" + sentDatestring + ext
                filename = filename.replace(" ", "") #strip whitespace
                print(currentDatestring + " : attachment found (" + x.get_content_type() + ") " + filename)
                filepath = attachmentFolderPath + pathString + filename

                # ---- check for duplicates and incremenk file name if needed, using next_path function defined above ----
                if os.path.exists(filepath):                
                    print(filename + " : File with that name exists already! Incrementing file name.")
                    path, ext = os.path.splitext(filepath)
                    path = path + "(%s)"
                    filepath = next_path(path, ext)

                # --- write the attachment data into a file with the correct name and extension ----
                os.makedirs(os.path.dirname(filepath), exist_ok=True) #make directory if it doesn't already exist
                with open(filepath, 'wb') as fp:
                    fp.write(x.get_payload(decode=True)) #unpack the payload into an actual file

                # --- mark message to be moved out of inbox (can't do it straight away cos there may be more attachments in this message! ---
                msgsToDelete[key] = msg

#print(msgsToDelete)

# --- Move the messages to 'downloaded' mailbox ---
# using 'msgsToDelete' dictionary, find every msg we just downloaded an attachment from, add it to downloaded
# and remove from inbox

for key,msg in msgsToDelete.items():
    newKey=downloaded.add(msg)
    # newMsg=downloaded.get_message(newKey)
    # newMsg.set_subdir('cur')
    # newMsg.add_flag('S')
    # downloaded.update({newKey:newMsg})
    inbox.discard(key)
    downloaded.flush()
    inbox.flush()


            

