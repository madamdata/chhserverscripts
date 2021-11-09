<b> Attachscript.py : </b>
process a Maildir folder, extracting attachments, sorting them into mailboxes based on sender and appending sender emails to filenames.
Uses Python 3.

<b> Scraper.py : </b>
scrapes data from a csv file and uploads it to Airtable

usage for now: 
first, navigate to the folder with scraper.py

(converts all xlsx in myFolderName into csv)
for f in myFolderName/*.xlsx; do in2csv "$f" > "myFolderName/${f%.xlsx}.csv"; done

(executes the scraper on every csv file in a folder)
find (myFolderName) -name *.csv -exec python3 scraper.py {} \;



