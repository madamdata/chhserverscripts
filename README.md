<b> Attachscript.py : </b>
process a Maildir folder, extracting attachments, sorting them into mailboxes based on sender and appending sender emails to filenames.
Uses Python 3.

<b> Scraper.py : </b>
scrapes data from a csv file and uploads it to Airtable

usage for now: 
first, navigate to the folder with scraper.py

(converts all xlsx in myFolderName into csv)
for f in *.xlsx; do in2csv -n "$f" | xargs -I % sh -c "in2csv $f --sheet % > $f_sheet%.csv"; done


(executes the scraper on every csv file in a folder)
find ../testdata -name *.csv -exec python3 scraper.py {} \\;



