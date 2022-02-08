#!/bin/bash

DATESTRING=$(date +%Y-%m-%d)
WORKINGDIRECTORY="/home/chh/mail"
BACKUPLOGFILENAME="attachments/log/backup/aslog_$DATESTRING.log"
BACKUPSCRAPELOGFILENAME="attachments/log/backup/scrlog_$DATESTRING.log"

# make a copy of the file and append 25 lines of the old file into the new log
cd $WORKINGDIRECTORY && mv attachments/log/attachscript.log $BACKUPLOGFILENAME 
cat $BACKUPLOGFILENAME | tail -n 25 > attachments/log/attachscript.log
cd $WORKINGDIRECTORY && mv attachments/log/scrape.log $BACKUPSCRAPELOGFILENAME
cat $BACKUPSCRAPELOGFILENAME | tail -n 25 > attachments/log/scrape.log

echo "Backing up to $BACKUPLOGFILENAME ..."
echo "Backing up to $BACKUPSCRAPELOGFILENAME ..."



