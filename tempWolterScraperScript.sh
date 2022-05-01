#!/bin/bash

cd $1

SCRAPELOGFILE="/home/chh/mail/attachments/log/tempwolterscrape.log"


#rename existing pdfs, since they can't be scraped. No unprocessed pdfs left.
if ls ++*.[pP][dD][fF] 1> /dev/null 2>&1; then
	for pdf in ++*.[pP][dD][fF]; do mv "$pdf" "${pdf:2}"; done
fi


#convert individual sheets in the excel files to csv
# and SCRAPE

#find . -name "++*.xls" -exec pyexcel transcode {} {}.xlsx \; >> $SCRAPELOGFILE 2>&1
#find . -name "++*.xls" -exec pyexcel transcode {} {}.xlsx \; >> $SCRAPELOGFILE 2>&1
find . -name "++*.xlsx" -exec sh -c "python3 ~/mail/chhserverscripts/2scraper.py -potype wolter -mode upload {}" \; >> $SCRAPELOGFILE 2>&1
#find . -name "++*.xlsx" -exec python3 ~/mail/chhserverscripts/2scraper.py {} wolter upload \;

for filename in ++*.[xX][lL][sS][xX];do echo $filename && mv $filename ${filename:2}; done
#for filename in ++*.[xX][lL][sS];do mv $filename ${filename:2}; done


