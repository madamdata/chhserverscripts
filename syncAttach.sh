#!/bin/bash

mbsync -a
/usr/bin/python3 $HOME/mail/chhserverscripts/attachscript.py >> $HOME/mail/attachments/log/attachscript.log 2>&1 

#remove all pdfs in the /pdf folders
rm -rf $HOME/mail/attachments/rosenberg/pdf/*
rm -rf $HOME/mail/attachments/wolter/pdf/*
rm -rf $HOME/mail/attachments/wsk/pdf/*
rm -rf $HOME/mail/attachments/metavent/pdf/*

rclone sync --exclude "*sync.log*" $HOME/mail/attachments iningDropbox:attachments >> $HOME/mail/attachments/log/sync.log 2>&1


$HOME/mail/chhserverscripts/scraperscript.sh rosenberg $HOME/mail/attachments/rosenberg
$HOME/mail/chhserverscripts/scraperscript.sh wolter $HOME/mail/attachments/wolter

#rclone copy --max-age 4m --exclude "++rosenberg*" --exclude "++wolter*" $HOME/mail/attachments iningDropbox:workingDirectory >> $HOME/wdsync.log 2>&1
rclone copy --max-age 5m --max-duration 60s --max-backlog 30 --ignore-existing --exclude "++rosenberg*" --exclude "++wolter*" $HOME/mail/attachments iningDropbox:workingDirectory >> $HOME/wdsync.log 2>&1

#rclone copy --max-age 10 $HOME/mail/attachments/rosenberg/do iningDropbox:workingDirectory/rosenberg/do >> $HOME/mail/attachments/log/dosync.log 2>&1
#rclone copy --max-age 10m --max-duration 60s --max-backlog 30 --ignore-existing  $HOME/mail/attachments/rosenberg/do iningDropbox:workingDirectory/rosenberg/do >> $HOME/dosync.log 2>&1

#rclone copy --max-age 5m --max-duration 60s --max-backlog 30 --ignore-existing --exclude "++rosenberg*" --exclude "++wolter*" $HOME/mail/attachments iningDropbox:workingDirectory >> $HOME/wdsync.log 2>&1
rclone sync --max-duration 60s --max-backlog 60 --ignore-existing iningDropbox:workingDirectory/rosenberg/do iningDropbox:referenceDirectory/rosenberg/rosenberg-do >> $HOME/wdsync.log 2>&1

rclone sync --max-duration 60s --max-backlog 60 --ignore-existing iningDropbox:workingDirectory/wolter/do iningDropbox:referenceDirectory/wolter/wolter-do >> $HOME/wdsync.log 2>&1

#rclone sync --max-age 5m --max-duration 60s --max-backlog 30 --ignore-existing iningDropbox:workingDirectory/rosenberg/do iningDropbox:referenceDirectory/rosenberg/rosenberg-do >> $HOME/wdsync.log 2>&1

