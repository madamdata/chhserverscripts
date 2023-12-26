#!/bin/bash

cd $2

POTYPE=$1

SCRAPELOGFILE="/home/chh/mail/attachments/log/scrape.log"


#rename existing pdfs, since they can't be scraped. No unprocessed pdfs left.
if ls ++*.[pP][dD][fF] 1> /dev/null 2>&1; then
	for pdf in ++*.[pP][dD][fF]; do mv "$pdf" "${pdf:2}"; done
fi


#convert individual sheets in the excel files to csv
# and SCRAPE

############### NEW SCRAPER CODE ################

if ls *.[xX][lL][sS][xX] 1> /dev/null 2>&1; then
	MODE='realupload'
	#find . -name '++*.xlsx' -exec sh -c "~/mail/chhserverscripts/2scraper.py -mode $MODE -potype $POTYPE '{}'" \; >> $SCRAPELOGFILE 2>&1
	#for filename in ++*.[xX][lL][sS][xX];do mv $filename ${filename:2}; done
	find . -maxdepth 1 -name '*.xlsx' -mmin -5 -exec sh -c "~/mail/chhserverscripts/2scraper.py -mode $MODE -potype $POTYPE '{}'" \; >> $SCRAPELOGFILE 2>&1
	for filename in *.[xX][lL][sS][xX];do mv -n $filename $POTYPE-processed/$filename; done
fi



