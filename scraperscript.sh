#!/bin/bash

cd $1

SCRAPELOGFILE="/home/chh/mail/attachments/log/scrape.log"


#rename existing pdfs, since they can't be scraped. No unprocessed pdfs left.
if ls ++*.[pP][dD][fF] 1> /dev/null 2>&1; then
	for pdf in ++*.[pP][dD][fF]; do mv "$pdf" "${pdf:2}"; done
fi


#convert individual sheets in the excel files to csv
# and SCRAPE

################ OLD SCRAPER CODE ##############
#if ls ++*.[xX][lL][sS][xX] 1> /dev/null 2>&1; then
	#for xl in ++*.[xX][lL][sS][xX]; do /usr/local/bin/in2csv -n "$xl" | xargs -I % bash -c "/usr/local/bin/in2csv '$xl' --sheet % > '$xl'%.csv 2> /dev/null"; done
	#for filename in ++*.[xX][lL][sS][xX];do mv $filename ${filename:2}; done
	#find . -name "*.csv" -exec python3 ~/mail/chhserverscripts/scraper.py {} \; >> $SCRAPELOGFILE 2>&1
##else
	##echo "No new .xlsx files to process."
#fi


############### NEW SCRAPER CODE ################

if ls ++*.[xX][lL][sS][xX] 1> /dev/null 2>&1; then
	MODE='realupload'
	POTYPE='rosenberg'
	find . -name '++*.xlsx' -exec sh -c "~/mail/chhserverscripts/2scraper.py -mode $MODE -potype $POTYPE '{}'" \; >> $SCRAPELOGFILE 2>&1
	for filename in ++*.[xX][lL][sS][xX];do mv $filename ${filename:2}; done
	#find . -name "*.csv" -exec sh -c "2scraper.py -mode $MODE -potype $POTYPE '{}'" \; >> $SCRAPELOGFILE 2>&1
#else
fi

#remove all csvs created by this script

if ls ++*.csv 1> /dev/null 2>&1; then
	rm ++*.csv
fi


