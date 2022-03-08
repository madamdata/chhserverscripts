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
    data_rows = [] 
    for name in sheetnames: 
        print('Parsing sheet:', name)
        sheet = excelfile[name]
        for row in sheet.iter_rows():
            rowvals = [x.value for x in row]
            data_rows.append(rowvals)

    # Parse the xml document for rules

    tree = ET.parse('data.xml')
    parser = poparser.POParser(tree)
    parser.filename = filename
    root = parser.tree.getroot()


    # parse the excel data and get PO object
    po = parser.parse(data_rows)
    po.printAll()

