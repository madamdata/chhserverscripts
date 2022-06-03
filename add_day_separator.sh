#!/bin/bash

DATESTRING=$(date +%d\_%b\_%Y_%H_%M)
WORKINGDIRECTORY="/home/chh/mail"
ALOGFILENAME="attachments/log/attachscript.log"
SLOGFILENAME="attachments/log/scrape.log"

cd $WORKINGDIRECTORY
printf "\n" >> $ALOGFILENAME
printf "   ########### $DATESTRING ############" >> $ALOGFILENAME
printf "\n" >> $ALOGFILENAME

printf "\n" >> $SLOGFILENAME
printf "   ########### $DATESTRING ############" >> $SLOGFILENAME
printf "\n" >> $SLOGFILENAME
