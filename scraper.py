import csv, os, sys, re, datetime, pyairtable
from dotenv import load_dotenv, dotenv_values
import poclasses

#--- open file and set up some variables ---
datestring = datetime.datetime.now().strftime("%d%b%Y-%H:%M")
filepath = sys.argv[1]
print(datestring + " :scraping " + filepath + " ...")
csvfile = open(filepath, newline='')
reader = csv.reader(csvfile, dialect='excel')
rows = []
for row in reader:
    rows.append(row)
numRows = len(rows)
numCols = len(rows[0])

dataBegin = ['ITEM', 'item', 'Item']
ponumber_string = 'P/O No'
ponumber = '-'
project_string = 'PROJECT'
project = '-'

issuedate_string = 'DATE'
issuedate = None

deliverydate_string = 'Delivery'
deliverydate = None

note_string = '**Note'
note = None

detail_string = '^DETAIL.+'
detail = None

po_items = []


# --- load environment and airtable API ---
load_dotenv()
key = os.environ['AIRTABLEKEY']
baseid = os.environ['AIRTABLEBASEID']
remote_table = pyairtable.Table(key, baseid, 'Table 1')

def scrape_data(table, startrow, startcol):
    """ takes a table, start row and start column,
    and scrapes the cells to the right and left, 
    returning a list of POItems
    """
    header_row = table[startrow]
    num_items = 0
    items = []
    new_table = []

    # --- calculate number of items ---
    for i in range(startrow+1,numRows-1): #goes down the starting column, calculating number of items
       entry = table[i][startcol]
       if entry == '':
           #could be a single blank spot. test for 2 consecutive blank cells
           if table[i+1][startcol] == '':
               break
           else: 
               num_items +=1
               new_table.append([])
       else:
           num_items += 1
           new_table.append([]) #add a new empty row to the output table

    # --- append header of each column to every entry, and output a new table
    # of (header, entry) tuples ---
    for column, header in enumerate(header_row):
        if header != '': # if the header is not empty...
            for i in range(num_items): # go down the column, and for each item - 
                # append a new entry to tje output table, a (header, entry) tuple.
                new_table[i].append((header, table[i+startrow+1][column+startcol])) 

    # --- generate list of POItems ---
    for new_row in new_table:
        po_item = poclasses.POItem()
        # po_item.input_dict['PO Number'] = ponumber
        po_item.addEntry(('PO Number', ponumber))
        po_item.addEntry(('Project Site', project))
        po_item.addEntry(('PO Delivery Date', deliverydate))
        po_item.addEntry(('PO Date', issuedate))
        po_item.addEntry(('Note Raw', note))
        po_item.addEntry(('Detail Raw', detail))
        for entry in new_row:
            po_item.addEntry(entry)
        items.append(po_item)

    return items

       
# --- first pass - to get all the document-level params --- 
for rownumber, row in enumerate(rows): #just to find the row with the 'item', 'model' headings etc
    for colnumber, item in enumerate(row): 
        if item == ponumber_string:
            ponumber = rows[rownumber][colnumber+1]
            ponumber = ponumber + rows[rownumber][colnumber+2]
            ponumber = ponumber.replace(' ', '').replace(':','')
        elif item == project_string:
            project = rows[rownumber][colnumber+1]
            project = project + rows[rownumber][colnumber+2]
        elif item == deliverydate_string:
            rawdate = rows[rownumber][colnumber+1] + rows[rownumber][colnumber+2]
            rawdate = rawdate.replace(':', '')
            try:
                datestring = re.match(r'.*?([0-9\/-]+)', rawdate).group(1)
            except AttributeError: #if no match, group(1) above returns this error
                if rawdate == "ASAP": 
                    print("Delivery date ASAP: setting to today.")
                    # deliverydate = datetime.datetime.now().strftime('%Y-%m-%d')  
                    datestring = datetime.datetime.now().strftime('%Y-%m-%d')  
                else:
                    print("Delivery date does not match known formats: ", rawdate)

            try: 
                dateobj = datetime.datetime.strptime(datestring, '%Y-%m-%d')
            except ValueError: #string is not in the specified format
                print("Delivery Date not in %Y-%m-%d format: ", datestring)

            try: 
                dateobj = datetime.datetime.strptime(datestring, '%d/%m/%Y')
            except ValueError: #string is not in the specified format
                print("Delivery Date not in %d/%m/%Y format: ", datestring)

            try: 
                deliverydate = dateobj.strftime('%Y-%m-%d') #has to be in bizarre US order cos of airtable
            except AttributeError: #dateobj is None
                print("Delivery date object invalid: ", dateobj, rawdate)
            # try:
                # datestring = re.match(r'.*?([0-9\/-]+)', rawdate).group(1)
                # dateobj = datetime.datetime.strptime(datestring, '%Y-%m-%d')
                # deliverydate = dateobj.strftime('%Y-%m-%d') #has to be in bizarre US order cos of airtable
            # except AttributeError: #if no match, .group(1) of None returns this error.
                # print("Delivery date does not match known formats. No regex match: ", rawdate)
                # if rawdate == "ASAP": 
                    # deliverydate = datetime.datetime.now().strftime('%Y-%m-%d')  
            # except ValueError:
                # print("Delivery date looks like a date but can't be parsed: ", rawdate)

        elif item == issuedate_string:
            rawdate = rows[rownumber][colnumber+1] + rows[rownumber][colnumber+2]
            rawdate = rawdate.replace(':', '')
            dateobj = None

            try:
                datestring = re.match(r'.*?([0-9\/-]+)', rawdate).group(1)
            except AttributeError:
                print("Issue date does not match known formats: ", rawdate)

            try: 
                dateobj = datetime.datetime.strptime(datestring, '%Y-%m-%d')
            except ValueError:
                print("Issue Date not in %Y-%m-%d format: ", datestring)

            try: 
                dateobj = datetime.datetime.strptime(datestring, '%d/%m/%Y')
            except ValueError:
                print("Issue Date not in %d/%m/%Y format: ", datestring)

            try: 
                issuedate = dateobj.strftime('%Y-%m-%d') #has to be in bizarre US order cos of airtable
            except AttributeError: #dateobj is None
                print("Issue date object invalid: ", dateobj, rawdate)


        elif item == note_string:
            note = rows[rownumber][colnumber+1] + rows[rownumber][colnumber+2] + rows[rownumber][colnumber+3]
            note = note + rows[rownumber+1][colnumber+1] + rows[rownumber+1][colnumber+2] + rows[rownumber+1][colnumber+3]
            # print(note)

        #scrape both the detail cell and the next cell to the right, using regex 
        #in case of weird formatting. Hopefully we don't have to keep doing this - regex is slow.
        elif re.match(detail_string, item):
            detail = rows[rownumber][colnumber+1]
            detail = item + detail 
            poclasses.parse_detail(detail)

# --- second pass - to get the actual items ---
for rownumber, row in enumerate(rows):
    numItems = 0
    for colnumber, item in enumerate(row):
        if item in dataBegin:
            po_items = scrape_data(rows, rownumber, colnumber)#if the thing in the cell is the word 'ITEM' or 'Item'

for poitem in po_items: 
    poitem.convertallparams()
    output_dict = poitem.output_dict
    output_dict_printstring = ""
    for k, v in output_dict.items():
        output_dict_printstring = output_dict_printstring + " " + str(k) + " : " +  str(v) +  "   |   " 
    print(output_dict_printstring)
    poitem.update_remote(remote_table)

print("         ----           ")
