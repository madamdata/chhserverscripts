#!/bin/bash

DATESTRING=$(date +%d\_%b%Y)
WORKINGDIRECTORY="/home/pi/mail"
BACKUPLOGFILENAME="attachments/log/backup/aslog$DATESTRING.log"
BACKUPSCRAPELOGFILENAME="attachments/log/backup/scrlog$DATESTRING.log"

cd $WORKINGDIRECTORY && mv attachments/log/attachscript.log $BACKUPLOGFILENAME && touch attachscript.log
cd $WORKINGDIRECTORY && mv attachments/log/scrape.log $BACKUPSCRAPELOGFILENAME && touch scrape.log
echo "Backing up to $BACKUPLOGFILENAME ..."


#echo "Deleting files older than 7 days ..."
#find $WORKINGDIRECTORY/attachments/log/backup/* -mtime +7 -exec rm {} \;

