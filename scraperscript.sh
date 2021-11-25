#!/bin/bash

cd $1

PRINTLOGFILE="/home/pi/mail/attachments/log/print.log"
SCRAPELOGFILE="/home/pi/mail/attachments/log/scrape.log"


#print any existing unprocessed pdfs - they can't be scraped.
#rename existing pdfs. No unprocessed pdfs left.
if ls ++*.[pP][dD][fF] 1> /dev/null 2>&1; then
	for newpdf in ++*.[pP][dD][fF]; do echo "printing $newpdf" >> $PRINTLOGFILE 2>&1 && lp -d CHH_HP_LASER_2 -o ColorModel=RGB -o print-scaling=fit $newpdf >> $PRINTLOGFILE 2>&1 ; done
	for pdf in ++*.[pP][dD][fF]; do mv "$pdf" "${pdf:2}"; done
fi


#convert individual sheets in the excel files to csv
# and SCRAPE

if ls ++*.[xX][lL][sS][xX] 1> /dev/null 2>&1; then
	for xl in ++*.[xX][lL][sS][xX]; do in2csv -n "$xl" | xargs -I % bash -c "in2csv '$xl' --sheet % > '$xl'%.csv 2> /dev/null"; done
	for filename in ++*.[xX][lL][sS][xX];do mv $filename ${filename:2}; done
	find . -name "*.csv" -exec python3 ~/mail/chhserverscripts/scraper.py {} \; >> $SCRAPELOGFILE 2>&1
#else
	#echo "No new .xlsx files to process."
fi

#convert xlsx to pdf for printing
#for xlp in ++*.xlsx; do libreoffice --headless --convert-to pdf $xlp; done

#print pdfs
#for pdfp in ++*.pdf; do lp -d CHH_HP_LASER_2 -o ColorModel=DeviceGray -o print-scaling=fit $pdfp; done 

#remove all csvs and any pdfs created by this script. (pre existing pdfs have already been renamed
#and so won't be removed)

if ls ++*.csv 1> /dev/null 2>&1; then
	rm ++*.csv
fi
#rm ++*.pdf


