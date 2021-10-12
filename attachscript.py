import mailbox
import os
import datetime
from email.header import decode_header

# ---- path and variable definitions ----
os.chdir('/home/pi/mail/pochhmail') #main mainbox directory. Everything in this script is relative to this path
logfilePath = '../attachments/log/attachscript.log'
synclogPath = '../attachments/log/sync.log'
attachmentFolderPath = '../attachments/'

inbox = mailbox.Maildir("INBOX", factory=None, create=False)

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
            

# ---- next, check the inbox for new attachments ----
for key, msg in inbox.iteritems():            # step through all the mail in the inbox
    #print(key)
    if msg.get_subdir() == 'new':
        msg.set_subdir('cur') # if it's in 'new', mark message as read
        msg.add_flag('S') # set 'read' flag (not sure how this is different from putting it in cur instead of new)
        sender = msg['From']
        to = msg['To'].split('@')[0].replace("<", "") #grab all the stuff before the '@', then split by '+' and strip any < 
        toComponents = to.split('+')
        toComponents.pop(0) #remove 0th element: the 'po' head
        pathString = '/'.join(toComponents) + '/' #turn it into a path by putting / between items
        # print(pathString)
        datestring = datetime.datetime.now().strftime("%d%b%Y")

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
                filename = to + "__" + filename + "__" + datestring + ext
                filename = filename.replace(" ", "") #strip whitespace
                print(datestring + ": attachment found: " + x.get_content_type() + ": " + filename)
                filepath = attachmentFolderPath + pathString + filename

                # ---- check for duplicates and incremenk file name if needed, using next_path function defined above ----
                if os.path.exists(filepath):                
                    print(filename + " : File with that name exists already! Incrementing file name.")
                    path, ext = os.path.splitext(filepath)
                    path = path + "(%s)"
                    filepath = next_path(path, ext)

                # --- write the attachment data into a file with the correct name and extension ----
                os.makedirs(os.path.dirname(filepath), exist_ok=True) #make directory if it doesn't already exist
                # print(filepath)
                with open(filepath, 'wb') as fp:
                    fp.write(x.get_payload(decode=True)) #unpack the payload into an actual file

        #add the modified message, with new flags and subdir, to the mailbox. 
        #Remember that 'msg' has no necessary relation to the actual file in the mailbox - 
        #it's just a representation that we manipulate. 
        inbox.update({key:msg}) 


            

