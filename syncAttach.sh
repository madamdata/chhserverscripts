#!/bin/bash

mbsync -a
/usr/bin/python3 $HOME/mail/chhserverscripts/attachscript.py >> $HOME/mail/attachments/log/attachscript.log 2>&1 

#remove all pdfs in the /pdf folders
rm -rf $HOME/mail/attachments/rosenberg/pdf/*
rm -rf $HOME/mail/attachments/wolter/pdf/*
rm -rf $HOME/mail/attachments/wsk/pdf/*
rm -rf $HOME/mail/attachments/metavent/pdf/*

rclone sync --exclude "*sync.log*" $HOME/mail/attachments iningDropbox:attachments >> $HOME/mail/attachments/log/sync.log 2>&1
rclone copy --max-age 4m --no-traverse --exclude "++rosenberg*" --exclude "++wolter*" $HOME/mail/attachments iningDropbox:workingDirectory >> $HOME/mail/attachments/log/wdsync.log 2>&1

$HOME/mail/chhserverscripts/scraperscript.sh rosenberg $HOME/mail/attachments/rosenberg
$HOME/mail/chhserverscripts/scraperscript.sh wolter $HOME/mail/attachments/wolter
