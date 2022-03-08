#!/usr/bin/python3

import parser as poparser
import sys, os, pyairtable, logger
import xml.etree.ElementTree as ET
from dotenv import load_dotenv, dotenv_values
from openpyxl import load_workbook

if __name__ == '__main__':


    # Load environment and initialize airtable interface
    load_dotenv()
    key = os.environ['AIRTABLEKEY']
    baseid = os.environ['AIRTABLEBASEID']
    remote_table = pyairtable.Table(key, baseid, 'testtable')

    # read excel file
    filepath = sys.argv[1]
    filename = os.path.basename(filepath)
    excelfile = load_workbook(filename = filepath, data_only=True)
    sheetnames = excelfile.sheetnames
    sheetdata = []
    for name in sheetnames: 
        data_rows = [] 
        print('Parsing sheet:', name)
        sheet = excelfile[name]
        for row in sheet.iter_rows():
            rowvals = [x.value for x in row]
            data_rows.append(rowvals)
        sheetdata.append(data_rows)

    # Parse the xml document for rules

    parsertree = ET.parse('rules-parser.xml')
    parser = poparser.POParser(parsertree)
    parser.filename = filename
    root = parser.tree.getroot()


    # parse the excel data from THE FIRST SHEET ONLY and get PO object
    po = parser.parse(sheetdata[0])
    # check for multiple sheets
    if len(sheetnames) > 1:
        multiple_sheets = True
        po.addExtraCheckStrings('MULTIPLE SHEETS IN THIS FILE')

    po.printAll()
    po.summarizeCheckStrings()

    print('-----------------------------')
    print('\n')
