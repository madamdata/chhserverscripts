#!/bin/bash

DATESTRING=$(date +%Y-%m-%d)
WORKINGDIRECTORY="/home/pi/mail"
BACKUPLOGFILENAME="attachments/log/backup/aslog_$DATESTRING.log"
BACKUPSCRAPELOGFILENAME="attachments/log/backup/scrlog_$DATESTRING.log"

cd $WORKINGDIRECTORY && mv attachments/log/attachscript.log $BACKUPLOGFILENAME && touch attachments/log/attachscript.log
cd $WORKINGDIRECTORY && mv attachments/log/scrape.log $BACKUPSCRAPELOGFILENAME && touch attachments/log/scrape.log
echo "Backing up to $BACKUPLOGFILENAME ..."
echo "Backing up to $BACKUPSCRAPELOGFILENAME ..."


#echo "Deleting files older than 7 days ..."
#find $WORKINGDIRECTORY/attachments/log/backup/* -mtime +7 -exec rm {} \;

