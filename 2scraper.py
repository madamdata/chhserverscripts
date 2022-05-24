#!/usr/bin/python3

import parser as poparser
import processor as poprocessor
import sys, os, pyairtable, logger, argparse
import xml.etree.ElementTree as ET
from dotenv import load_dotenv, dotenv_values
from openpyxl import load_workbook

if __name__ == '__main__':


    # Load environment and initialize airtable interface
    # load_dotenv()
    # key = os.environ['AIRTABLEKEY']
    # baseid = os.environ['AIRTABLEBASEID']
    # remote_table = pyairtable.Table(key, baseid, 'testtable')

    # TEMPORARY FOR WOLTER SCRAPING
    load_dotenv()
    key = os.environ['AIRTABLEKEY']
    baseid = os.environ['AIRTABLEBASEID']
    remote_table = pyairtable.Table(key, baseid, 'Table 1')
    test_table = pyairtable.Table(key, baseid, 'test table')

    # read excel file
    argparser = argparse.ArgumentParser(description="Scraper v2.0")
    argparser.add_argument('-potype')
    argparser.add_argument('-mode', nargs='?', const='dryrun')
    argparser.add_argument('filepath')
    args = argparser.parse_args()
    print(args.filepath, args.potype)

    filepath = args.filepath
    mode = args.mode
    potype = args.potype
    uploadflag = False
    testupload = False

    if mode == 'upload':
        uploadflag = True

    if mode == 'testupload':
        testupload = True

    filename = os.path.basename(filepath)
    excelfile = load_workbook(filename = filepath, data_only=True)
    sheetnames = excelfile.sheetnames
    sheetFileMismatch = False
    sheetdata = []
    for name in sheetnames: 
        data_rows = [] 
        print('Parsing sheet:', name)
        if name not in filename:
            print('sheet name not the same as filename!!')
            sheetFileMismatch = True
        sheet = excelfile[name]
        for row in sheet.iter_rows():
            rowvals = [x.value for x in row]
            newrowvals = []
            # print(rowvals)
            for item in rowvals:
                newitem = item
                if item == ' ':
                    newitem = None
                newrowvals.append(newitem)
                    
            # if rowvals[0]:
                # codes = ''
                # for char in str(rowvals[0]):
                    # codes += str(ord(char))
                    # codes += '.'
                # print(rowvals[0], codes)
            # print(rowvals)
            # print(len(newrowvals))
            data_rows.append(newrowvals)
        sheetdata.append(data_rows)

    # Parse the xml document for rules

    if potype == 'wolter': 
        parsertree = ET.parse('/home/chh/mail/chhserverscripts/rules-parser-wolter.xml')
    elif potype == 'rosenberg':
        parsertree = ET.parse('rules-parser.xml')
    parser = poparser.POParser(parsertree)
    parser.filename = filename


    # parse the excel data from THE FIRST SHEET ONLY and get PO object
    po = parser.parse(sheetdata[0])
    if sheetFileMismatch:       
        po.addExtraCheckStrings('sheetFileMismatch')
    # check for multiple sheets
    if len(sheetnames) > 1:
        multiple_sheets = True
        po.addExtraCheckStrings('MULTIPLE SHEETS IN THIS FILE')

    print('---------- PARSER OUTPUT -----------\n')

    po.printAll()
    po.summarizeCheckStrings()

    print('---------- PROCESSOR OUTPUT -----------\n')

    #PROCESSOR
    processortree = ET.parse('/home/chh/mail/chhserverscripts/rules-processor.xml')
    processor = poprocessor.POProcessor(processortree)
    nodenetwork = processor.parse(po)
    # nodenetwork.listNodes()
    if testupload:
        processor.upload('upload group 1', test_table)
    # nodenetwork.listNodes(nodenames = ['PO Date', 'PO Delivery Date'])
    nodenetwork.listNodes(nodenames = ['Note Raw', 'bracket1st', 'bracket2nd', 'F/B (scraped)'])
    # nodenetwork.listNodes(nodenames=['ITEM', 'modelstringItem', 'MODEL'])
    # nodenetwork.listNodes(nodenames=['ITEM', 'splitA', 'modelstringItem', 'MODEL', 'modelstringExtra'])
    # nodenetwork.listNodes(nodenames=['ITEM', 'detailSplit'])

    print('-----------------------------\n')


    if uploadflag:
        po.tempUploadFunc(remote_table)

