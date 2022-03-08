#!/bin/bash

mbsync -a
/usr/bin/python3 $HOME/mail/chhserverscripts/attachscript.py >> $HOME/mail/attachments/log/attachscript.log 2>&1 
rclone sync $HOME/mail/attachments iningDropbox:attachments >> $HOME/mail/attachments/log/sync.log 2>&1
rclone copy --max-age 4m --no-traverse --exclude "++*" $HOME/mail/attachments iningDropbox:workingDirectory >> $HOME/mail/attachments/log/wdsync.log 2>&1

$HOME/mail/chhserverscripts/scraperscript.sh $HOME/mail/attachments/rosenberg
