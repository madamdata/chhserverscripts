#!/bin/bash

DATESTRING=$(date +%d\_%b\_%H:%M)
WORKINGDIRECTORY="/home/pi/mail"
BACKUPFILENAME="backup/$DATESTRING.zip"
BACKUPLOGFILENAME="attachments/log/backup/aslog$DATESTRING.log"

cd $WORKINGDIRECTORY && zip -r $BACKUPFILENAME attachments && mv attachments/log/attachscript.log $BACKUPLOGFILENAME && touch attachscript.log
echo "Backing up to $BACKUPFILENAME ..."
#cp /home/pi/Polytope/server/evennia.db3 $BACKUPFILENAME

rclone sync $HOME/mail/backup iningDropbox:backup

echo "Deleting files older than 7 days ..."
find $WORKINGDIRECTORY/backup/* -mtime +7 -exec rm {} \;
find $WORKINGDIRECTORY/attachments/log/backup/* -mtime +7 -exec rm {} \;

