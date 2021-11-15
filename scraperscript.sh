#!/bin/bash

cd $1

#print any existing unprocessed pdfs - they can't be scraped.
for f in ++*.pdf; do lp -d CHH_XEROX -oColorModel=Gray $f; done

#rename existing pdfs. No unprocessed pdfs left.
for f in ++*.pdf; do mv $f ${f:2}; done

#convert individual sheets in the excel files to csv
for f in ++*.xlsx; do in2csv -n "$f" | xargs -I % bash -c "in2csv '$f' --sheet % > '$f'%.csv"; done

#convert csvs to pdf for printing
for f in ++*.csv; do libreoffice --headless --convert-to pdf $f; done

#print pdfs
for f in ++*.pdf; do lp -d CHH_XEROX -oColorModel=Gray $f; done 


#scrape 
find . -name "*.csv" -exec python3 ~/mail/chhserverscripts/scraper.py {} \;

#remove all csvs and any pdfs created by this script. (pre existing pdfs have already been renamed
#and so won't be removed)
rm ++*.csv
rm ++*.pdf

for f in ++*;do mv $f ${f:2}; done
