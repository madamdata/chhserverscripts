#!/bin/bash

offlineimap -o && /usr/bin/python3 $HOME/mail/chhserverscripts/attachscript.py >> $HOME/mail/attachments/log/attachscript.log 2>&1 && rclone sync $HOME/mail/attachments iningDropbox:attachments >> $HOME/mail/attachments/log/sync.log 2>&1

