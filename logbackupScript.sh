#!/bin/bash

DATESTRING=$(date +%d\_%b\_%H:%M)
WORKINGDIRECTORY="/home/pi/mail"
BACKUPLOGFILENAME="attachments/log/backup/aslog$DATESTRING.log"

mv attachments/log/attachscript.log $BACKUPLOGFILENAME && touch attachscript.log
echo "Backing up to $BACKUPLOGFILENAME ..."


#echo "Deleting files older than 7 days ..."
#find $WORKINGDIRECTORY/attachments/log/backup/* -mtime +7 -exec rm {} \;

