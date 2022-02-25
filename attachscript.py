import mailbox, os, datetime, dateparser, re
from email.header import decode_header

# ---- path and variable definitions ----
os.chdir('/home/chh/mail/pochhmail') #main mainbox directory. Everything in this script is relative to this path
logfilePath = '../attachments/log/attachscript.log'
synclogPath = '../attachments/log/sync.log'
attachmentFolderPath = '../attachments/'
downloadFolderPath = 'downloaded/'
inboxFolderPath = 'inbox/'

inbox = mailbox.Maildir(inboxFolderPath, factory=None, create=False)
downloaded = mailbox.Maildir("downloaded", factory=None, create=False) #place to put the downloaded messages

cmdMailbox = mailbox.Maildir('commands', factory=None, create=False) #create a mailbox object for the special logs mailbox

# ---- function definitions ----
def next_path(path_pattern, path_pattern_processed, ext):
    """
    adds (1) (2) etc to filenames if a file exists at the specified path or
    at the path, but missing the ++
    """
    i = 1
    # print(path_pattern_processed)

    while os.path.exists(path_pattern % i + ext) or os.path.exists(path_pattern_processed % i + ext):
        i = i + 1

    return path_pattern % i + ext


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
        subject = msg['Subject']
        if subject == None: 
            subject = '[no subject]'
        tos = tos + ccs + bccs
        to = toComponents = ''
        pathString = pathStringForFilename =  ''
        for addr in tos:
            match = re.search(r'po.*@chh.sg', addr)
            try:
                to = match[0]
                to = to.split('@')[0]
                toComponents = to.split('+')
                toComponents.pop(0) #remove 0th element: the 'po' head
            except TypeError:
                pass
                # print("po email not found in 'To' field")
        pathString = '/'.join(toComponents).lower() + '/' #turn it into a path by putting / between items and force lowercase
        pathStringForFilename = '_'.join(toComponents).lower() #with _ instead of / for filename
        currentDatestring = datetime.datetime.now().strftime("%d%m%Y_%H:%M")
        sentDatestring = dateparser.parse(msg['Date']).strftime("%m%d_%Y")

        # ---- subpart handling ----
        for x in msg.walk():                                # msg.walk() goes through all the subparts depth-first
            if x.get_content_disposition() == 'attachment': # proceed only if this subpart is an attachment 
                # ---- figure out what the header is based on RFC 2047 codes - to ensure unicode stuff eg Chinese chars appear correctly --- 
                rawfilename = x.get_filename()
                charset = None
                try:
                    filename, charset = decode_header(rawfilename)[0] 
                except TypeError:
                    print("Some weird stuff going on with the header. Raw filename: ", rawfilename)
                if charset == 'utf-8':
                    filename = filename.decode('utf-8')
                elif charset == None:
                    filename = filename
                else: 
                    print("Can't tell what encoding the filename is.")
                    filename = rawfilename
                    
                # ---- create a filename by adding the name of the box and the date ----
                filename = filename.replace(" ", "").replace("\n", "") #strip whitespace and line breaks
                filename, file_ext = os.path.splitext(filename)
                filenameprocessed = pathStringForFilename + "__" + filename + file_ext #just for checking duplicates
                filename = "++" + filenameprocessed
 
                content_type = x.get_content_type()
                #log only if file is not in the exclude list etc
                excludeThis = False
                log_exclude = [r'^\+\+_chh.*', r'^\+\+wolter_do.*', r'^\+\+rosenberg_do.*', r'^\+\+rosenberg_pdf.*']
                #log_exclude = [r'^\+\+wolter_do.*']
                for excludeRegex in log_exclude:
                    if re.match(excludeRegex, filename):
                        excludeThis = True #if nothing matches, 'False' value should fall through

                if not excludeThis:
                    print(currentDatestring + ": attachment found in msg (" + subject[:13] +  "..) -- " + filename)
                else:
                    # print("test - skipping log for ++_chh...")
                    pass
                filepath = attachmentFolderPath + pathString + filename
                filepathprocessed = attachmentFolderPath + pathString + filenameprocessed #again just for checking duplicates

                # ---- check for duplicates and incremenk file name if needed, using next_path function defined above ----
                # print("pathExists:", os.path.exists(filepath), "pathProcessedExists:", os.path.exists(filepathprocessed))

                if os.path.exists(filepath) or os.path.exists(filepathprocessed):                
                    if not excludeThis:
                        print(filename + " : File with that name exists already! Incrementing file name.")
                    path, ext = os.path.splitext(filepath)
                    path = path + "(%s)"
                    path_processed, ext2 = os.path.splitext(filepathprocessed)
                    path_processed = path_processed + "(%s)"
                    filepath = next_path(path, path_processed, ext)

                # --- write the attachment data into a file with the correct name and extension ----
                os.makedirs(os.path.dirname(filepath), exist_ok=True) #make directory if it doesn't already exist
                # print(file_ext.lower())
                if file_ext.lower()=='.pdf' or 'spreadsheet' in content_type or 'pdf' in content_type or 'jpeg' in content_type or 'excel' in content_type:
                    with open(filepath, 'wb') as fp:
                        fp.write(x.get_payload(decode=True)) #unpack the payload into an actual file
                else:
                    print("Not a spreadsheet or pdf... not downloading: (" + content_type + ")" )
                

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


            

