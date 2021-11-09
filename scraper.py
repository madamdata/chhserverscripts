import csv, os, sys, re, datetime, pyairtable
from dotenv import load_dotenv, dotenv_values
import poclasses

#--- open file and set up some variables ---
filepath = sys.argv[1]
print(filepath)
csvfile = open(filepath, newline='')
reader = csv.reader(csvfile, dialect='excel')
rows = []
for row in reader:
    rows.append(row)
numRows = len(rows)
numCols = len(rows[0])

dataColumns = ['ITEM', 'MODEL', 'T/BOX', 'Motor', 'Qty/Uts', 'S$ U/P', 'S$ Amt']
ponumber_string = 'P/O No'
ponumber = '-'
project_string = 'PROJECT : '
project = '-'

issuedate_string = 'DATE'
issuedate = None

deliverydate_string = 'Delivery'
deliverydate = None

note_string = '**Note'
note = None

po_items = []

# po = poclasses.PO("111111")

# --- load environment and airtable API ---
load_dotenv()
key = os.environ['AIRTABLEKEY']
baseid = os.environ['AIRTABLEBASEID']
remote_table = pyairtable.Table(key, baseid, 't1exp')

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
           break
       else:
           num_items += 1
           new_table.append([]) #add a new empty row to the output table

    # --- append header of each column to every entry, and output a new table
    # of (header, entry) tuples ---
    for column, header in enumerate(header_row):
        if header != '': # if the header is not empty...
            for i in range(num_items): # go down the column, and for each item - 
                # append a new entry to the output table, a (header, entry) tuple.
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
        for entry in new_row:
            po_item.addEntry(entry)
        items.append(po_item)

    return items

       
# --- first pass - to get all the document-level params --- 
for rownumber, row in enumerate(rows): #just to find the row with the 'item', 'model' headings etc
    for colnumber, item in enumerate(row): 
        if item == ponumber_string:
            ponumber = rows[rownumber][colnumber+1].replace(' ', '').replace(':','')
        elif item == project_string:
            project = rows[rownumber][colnumber+1]
        elif item == deliverydate_string:
            rawdate = rows[rownumber][colnumber+1]
            try:
                datestring = re.match(r'.*?([0-9/]+)', rawdate).group(1)
                dateobj = datetime.datetime.strptime(datestring, '%d/%m/%Y')
                deliverydate = dateobj.strftime('%Y-%m-%d')
            except AttributeError: #if no match, .group(1) of None returns this error.
                print("Delivery date does not match known formats. No regex match.")

            # # print(deliverydate)
        elif item == issuedate_string:
            rawdate = rows[rownumber][colnumber+1]
            try:
                datestring = re.match(r'.*?([0-9/]+)', rawdate).group(1)
                dateobj = datetime.datetime.strptime(datestring, '%d/%m/%Y')
                issuedate = dateobj.strftime('%Y-%m-%d')
            except AttributeError:
                print("issue date does not match known formats")
        elif item == note_string:
            note = rows[rownumber][colnumber+1]

# --- second pass - to get the actual items ---
for rownumber, row in enumerate(rows):
    numItems = 0
    for colnumber, item in enumerate(row):
        if item == dataColumns[0]:
            po_items = scrape_data(rows, rownumber, colnumber)#if the thing in the cell is the word 'ITEM'

for poitem in po_items: 
    # print(poitem['PO Delivery Date'])
    poitem.convertallparams()
    poitem.update_remote(remote_table)

# print(remote_table.fields())


# print(key)


# rotated = list(zip(*colData[::]))
# for item in rotated:
    # print('|'.join(item))
    # print('\n')
