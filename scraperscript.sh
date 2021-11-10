#!/bin/bash

cd $1

for f in *.xlsx; do in2csv -n "$f" | xargs -I % sh -c "in2csv $f --sheet % > $f%.csv"; done

find . -name "*.csv" -exec python3 ~/mail/chhserverscripts/scraper.py {} \;

rm *.csv
mv *.xlsx ../
