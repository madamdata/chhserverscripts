#!/usr/bin/python3

import sys, os, re, datetime, pyairtable, poclasses
from openpyxl import load_workbook

filepath = sys.argv[1]
excelfile = load_workbook(filename = filepath)
sheetnames = excelfile.sheetnames
print(sheetnames)
for name in sheetnames: 
    sheet = excelfile[name]
    po = poclasses.PO()
    for row in sheet.iter_rows():
        rowvals = [x.value for x in row]
        print(rowvals)




