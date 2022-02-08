#!/bin/bash

DATESTRING=$(date +%d\_%b\_%H:%M)
WORKINGDIRECTORY="/home/chh/mail"
BACKUPFILENAME="backup/$DATESTRING.zip"

cd $WORKINGDIRECTORY && zip -r $BACKUPFILENAME attachments
echo "Backing up to $BACKUPFILENAME ..."

rclone sync $HOME/mail/backup iningDropbox:backup

echo "Deleting files older than 7 days ..."
find backup/* -mtime +7 -exec rm {} \;

~/mail/chhserverscripts/add_day_separator.sh

