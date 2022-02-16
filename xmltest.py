#!/usr/bin/python3

import sys, os, re, datetime, pyairtable
import xml.etree.ElementTree as ET
from dotenv import load_dotenv, dotenv_values
from openpyxl import load_workbook


class InputFieldParser:
    def __init__(self, tree):
        # initialize variables
        self.value = ''
        self.tree = tree
        self.triggers = []
        self.cells = []
        # load triggers, cells, actions etc
        self.name = tree.find('name').text
        for trigger in tree.findall('trigger'):
            self.triggers.append(trigger)
        for cell in tree.findall('cell'):
            self.addCell(cell)
        for action in tree.findall('action'):
            self.addAction(action)

    def addAction(self, treeField):
        """
        add an action based on the data in the xml. 
        can be just a direct output, or a more complex function.
        """
        self.actiontype = treeField.attrib['type']
        # print(self.actiontype)

    def addCell(self, cellObj):
        """
        the 'cell' variable stores a relative vector pointing toward where the 
        data in the spreadsheet is, from the location of the header
        """
        processedList = cellObj.text.replace(' ', '').split(',')
        try: 
            xcoord = int(processedList[0])
        except ValueError:
            print("Invalid cell definition: ", cellObj.text)
        try: 
            ycoord = int(processedList[1])
        except ValueError:
            print("Invalid cell definition: ", cellObj.text)
        cellCoords = (xcoord, ycoord)
        self.cells.append(cellCoords)
        
    def matchAndGet(self, string, data_rows, coordinateTuple):
        output = None
        if self.matchTrigger(string):
            print(string, ' matched!')
            output = self.getCells(data_rows, coordinateTuple)
        return output

    def matchTrigger(self, string):
        for trigger in self.triggers:
            txt = trigger.text
            trigtype = trigger.attrib['type']
            if trigtype == 'raw':
                if txt == string:
                    return True
                else:
                    return False
            elif trigtype == 'regex':
                # print(txt, string)
                if re.match(txt, str(string)):
                   return True
                else: 
                    return False

    def getCells(self, data_rows, coordinateTuple):
        # print(coordinateTuple)
        xcoord = coordinateTuple[0]
        ycoord = coordinateTuple[1]
        output = ''
        for item in self.cells:
            xoffset = item[0]
            yoffset = item[1]
            # print('x', xcoord+xoffset, 'y', ycoord+yoffset)
            targetcell = data_rows[ycoord+yoffset][xcoord+xoffset]
            if targetcell: 
                if targetcell.__class__.__name__ == 'datetime':
                    output += targetcell.strftime('%Y-%m-%d')
                else:
                    output += targetcell
            output += ' '
        return output



class POParser:
    def __init__(self, tree):
        self.tree = tree
        self.fields = []
        # get fields from the tree
        for item in self.tree.findall('field'):
            try: 
                fieldname = item.find('name')
            except: 
                print("Can't find item name.")
            else: 
                self.fields.append(InputFieldParser(item))

    def parse(self, data_rows, po_object):
        for rownum, row in enumerate(data_rows):
            for colnum, cell in enumerate(row):
                if cell != None:
                    for field in self.fields:
                        output = field.matchAndGet(cell, data_rows, (colnum, rownum))  
                        if output:
                            print(output)

    def funcAllFields(self, func):
        for item in self.fields: 
            func(item)

class PO:
    def __init__(self):
        self.items = [] 

class POItem:
    def __init__(self):
        self.fields = []
    

def printAll(iterobj, func):
    for item in iterobj: 
        print(func(iterobj[item]))

if __name__ == '__main__':

    # Load environment and initialize airtable interface
    load_dotenv()
    key = os.environ['AIRTABLEKEY']
    baseid = os.environ['AIRTABLEBASEID']
    remote_table = pyairtable.Table(key, baseid, 'testtable')

    # read excel file
    filepath = sys.argv[1]
    excelfile = load_workbook(filename = filepath)
    sheetnames = excelfile.sheetnames
    data_rows = [] 
    for name in sheetnames: 
        print('Parsing ', name)
        sheet = excelfile[name]
        po = PO()
        for row in sheet.iter_rows():
            rowvals = [x.value for x in row]
            data_rows.append(rowvals)

    # Parse the xml document for rules
    tree = ET.parse('data.xml')
    parser = POParser(tree)
    root = parser.tree.getroot()


    parser.parse(data_rows, po)


    # parser.funcAllFields(lambda x: print(x.name, x.cells))



