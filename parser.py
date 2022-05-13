#!/usr/bin/python3

import sys, os, re, datetime, pyairtable, logger


class InputFieldParser:
    """
    encapsulates a rule in the parser xml document. Each rule defines
    a thing to look for in the main document - usually a document-level
    parameter, or the beginning of a table. For tables, the table is handed
    off to a specialised table parser, which returns a list of items
    """
    def __init__(self, tree):
        # initialize variables
        self.value = ''
        self.tree = tree
        self.triggers = []
        self.cells = []
        self.checkfunctions = []
        self.timestriggered = 0
        # load triggers, cells, actions etc
        self.name = tree.find('name').text
        try:
            self.maxtriggers = int(getTreeText(tree, 'maxtriggers', '1'))
        except:
            print('maxtriggers not an integer')

        outputfield = tree.find('outputfield')
        # get the output field name
        if outputfield != None:
            self.outputfield = outputfield.text

        for trigger in tree.findall('trigger'):
            # print(trigger.text)
            self.triggers.append(trigger)
        for cell in tree.findall('cell'):
            self.addCell(cell)
        for checkfunction in tree.findall('checkfunction'):
            self.addCheckFunc(checkfunction)
        for action in tree.findall('action'):
            self.addAction(action)

    def addCheckFunc(self, tree):
        """ add a check function based on data in the xml """
        funcname = tree.text
        self.checkfunctions.append(tree)
        pass

    def runCheckFunctions(self, pofield):
        """ run all of the check functions stored in this parser.
        if ANY ONE of them is True, output 'True'
        concatenate all the report strings together, if there are any, 
        and output that. 
        The output boolean and string are stored in the pofield object
        """ 
        outputstring = ''
        outputflags= []
        for checkfunctree in self.checkfunctions:
            flag, string = checkFunction(checkfunctree, pofield)
            outputstring += string
            outputflags.append(flag)
        if outputflags == []:
            outputflags = [False] #defaults to False (NOCHECK)

        # collapse the list of output flags together. if any are set to True, 
        # the whole thing will be true ie if anything needs to be CHECKED, 
        # the whole thing will be set to check.
        pofield.checkFlag = any(outputflags) 
        # print(outputstring)
        pofield.checkString = outputstring
        return pofield

    def addAction(self, treeField):
        """
        add an action based on the data in the xml. 
        can be just a direct output, or a more complex function.
        """
        self.actiontype = treeField.text
        # if the action is 'Parse Table', create a TableParser to 
        # encapsulate the table-specific rules. 
        # We always initialize the rules objects FIRST before doing any parsing.
        if self.actiontype == 'Parse Table':
            self.tableparser = TableParser(self.tree)
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

    def matchAndDoAction(self, string, data_rows, coordinateTuple):
        """
        matches the input string against all triggers. If there is a match,  
        chooses an action to take based on the 'actiontype' variable
        and executes it. Returns either a POField or, in the case of a table,
        a list of POItems (which contain POFields), plus an extra check string. 
        Extracheckstrings are the output of specialized check functions such as
        checking for max # of triggers or checking if the PO matches the filename. 
        
        """
        output = None
        extracheckstrings = ''
        if self.matchTrigger(string):
            # check if this has been triggered more than the number of times specified
            # and add a warning check string if it has
            self.timestriggered += 1
            if self.timestriggered > self.maxtriggers:
                maxtrigchkstr = '{name}: triggered {times} times. Max triggers set to {maxtriggers}'.format(\
                        name = self.name,
                        times = self.timestriggered,
                        maxtriggers = self.maxtriggers )
                extracheckstrings += maxtrigchkstr

            #check what kind of action to take
            actionname = self.actiontype
            if actionname == 'Direct Output': 
                actionname = 'getCells'
            elif actionname == 'Parse Table':
                actionname = 'parseTable'
            #find the method of this class that matches the 'actiontype' string
            action = getattr(self, actionname) 

            # the 'action' function is responsible for running the check functions of this inputfield
            output, checkstrings = action(self.tree, data_rows, coordinateTuple)
            extracheckstrings += checkstrings
            # check output and store the result in the POField's checkFlag and checkString
        return output, extracheckstrings

    def parseTable(self, tree, data_rows, coordinateTuple):
        """ just runs the parse method of the table parser and returns the output """
        output, extracheckstrings = self.tableparser.parse(data_rows, coordinateTuple)
        return output, extracheckstrings

    def matchTrigger(self, string):
        """ checks every trigger and returns a boolean for match
            called by matchAndDoAction()
        """
        output = []
        for trigger in self.triggers:
            txt = trigger.text
            # print(txt)
            trigtype = trigger.attrib['type']
            if trigtype == 'raw':
                if txt == string:
                    output.append(True)
                else:
                    output.append(False)
            elif trigtype == 'regex':
                # print(txt, string)
                if re.search(txt, str(string)):
                   output.append(True)
                else: 
                   output.append(False)
        return any(output)

    def getCells(self, tree,  data_rows, coordinateTuple):
        """
        reads all the items in self.cells, and extracts the data from those cells,
        offset from the start cell (coordinateTuple).
        Returns a POField object and a blank extra check string.
        Called by matchAndDoAction()
        """
        xcoord = coordinateTuple[0]
        ycoord = coordinateTuple[1]
        output = ''
        for item in self.cells:
            xoffset = item[0]
            yoffset = item[1]
            # y first, then x. Just a quirk of how the spreadsheet is stored. 
            try:
                targetcell = data_rows[ycoord+yoffset][xcoord+xoffset]
            except:
                targetcell = None
            if targetcell: 
                # if more than one cell, assume everything is a string and concat. 
                if len(self.cells) > 1: 
                    if targetcell.__class__.__name__ == 'datetime':
                        output += targetcell.strftime('%Y-%m-%d')
                        output += ' '
                    else:
                        output += targetcell
                        output += ' '
                # otherwise, preserve the data type, especially for dates
                else:
                    output = targetcell
        # create a POField with the proper header (self.outputfield) and value (output)
        field = POField(self.outputfield, output)
        self.runCheckFunctions(field)
        # return <pofield>, <extracheckstrings>
        return field, ''



class POParser:
    """
    class for parsing PO-level stuff. encapsulates functions performed on the 
    document level.
    """

    def __init__(self, tree):
        """ reads an XML tree on creation and creates a list of InputFieldParsers,
        which store parsing rules """
        self.tree = tree
        self.filename = ''
        self.inputfields = []
        self.outputfields = []
        # get input fields from the tree
        inputs = self.tree.find('inputs')
        outputs = self.tree.find('outputs')
        for item in inputs.findall('field'): #find all fields
            try: 
                fieldname = item.find('name')
            except: 
                print("Can't find item name.")
            else: # make a new InputFieldParser object 
                self.inputfields.append(InputFieldParser(item))
        # populate the list of output fields. These will go into the final PO object.
        # for item in outputs.iter('name'):
            # self.outputfields.append(item.text)

    def parse(self, data_rows):
        """ 
        reads a spreadsheet in list form and returns a PO object 
        by applying stored rules. 
        """ 
        # for every cell in the sheet, addressed by row and col (x and y)... 
        po_object = PO()
        po_object.filename = self.filename
        for rownum, row in enumerate(data_rows):
            for colnum, cell in enumerate(row):
                # if the cell isn't empty, apply every single field's 'matchAndDoAction' function to the cell to see which is a match
                # inefficient but this scraper doesn't have to be quick. 
                if cell != None:
                    for field in self.inputfields:
                        # output is a POField or None if no match
                        output, extracheckstrings = field.matchAndDoAction(cell, data_rows, (colnum, rownum))
                        # output = field.matchAndGet(cell, data_rows, (colnum, rownum))  
                        if output:
                            po_object.addItem(output)
                        if extracheckstrings != '':
                            po_object.addExtraCheckStrings(extracheckstrings)
        return po_object

    def funcAllFields(self, func):
        for item in self.inputfields: 
            func(item)

class TableParser:
    """ called by InputFieldParser """
    def __init__(self, tree):
        self.tree = tree
        self.checkfunctrees = []
        for checkfunctree in tree.findall('checkfunction'):
            self.checkfunctrees.append(checkfunctree)
        # print(self.headers)

    def getItemRowNumbers(self, coordinateTuple):
        """ 
        returns a list of row numbers with items in them, and a string
        denoting whether a gap was detected, which may require manual
        inspection
        """
        rowNumbers = []
        gapCheckString = ''
        ycoord = coordinateTuple[1]
        numRows = len(self.rawtable)
        for rownum in range(ycoord+1, numRows-1):
            # print(self.rawtable[rownum])
            if self.rawtable[rownum][0] != None:
                # print('nonecell', self.rawtable[rownum][0])
                rowNumbers.append(rownum)
            # Check the next row for empty space
            elif self.rawtable[rownum+1][0] == None:
                # Check for 2 blanks in a row, in case there's a single blank in the item col
                if self.rawtable[rownum+2][0] == None:
                    break
                else: 
                    gapCheckString = 'GAP IN TABLE DETECTED, CHECK MANUALLY'
        return rowNumbers, gapCheckString

    def getHeadersAndColumnNumbers(self, coordinateTuple):
        colNumbers = []
        xcoord = coordinateTuple[0]
        ycoord = coordinateTuple[1]
        numCols = len(self.rawtable[0])
        print('numcols ', numCols)
        for colnum in range(0, numCols):
            header = self.rawtable[ycoord][colnum]
            if colnum == 0: #get the first column header and store as the item field title
                itemHeader = header
            if header != None:
                colNumbers.append((header, colnum))
        return colNumbers, itemHeader

    def parse(self, data_rows, coordinateTuple):
        """
        returns a POItemList of POItems and an extra check string
        """
        self.rawtable = data_rows
        xcoord = coordinateTuple[0]
        ycoord = coordinateTuple[1]
        self.tablestartcoord = (xcoord, ycoord)
        self.headers = [header for header in self.rawtable[ycoord] if header != None]
        rowNumbers, gapCheckString = self.getItemRowNumbers(self.tablestartcoord)
        colNumbers, itemHeader = self.getHeadersAndColumnNumbers(self.tablestartcoord)
        output = POItemList()
        for row in rowNumbers:
            po_item = POItem()
            for header, column in colNumbers: 
                # make a new POField, with the header and value from the table
                checkFlags = []
                checkString = ''
                field = POField(header, self.rawtable[row][column])
                # print(header, '-->', self.rawtable[row][column])
                for checkfunctree in self.checkfunctrees:
                    try:
                        headerregex = checkfunctree.find('header').text
                    except AttributeError:
                        print("No header defined for checkfunction!")#Nonetype has no attribute 'text'
                    else:
                        if re.search(headerregex, header):
                            flag, string = checkFunction(checkfunctree, field)
                            # print(string)
                            checkFlags.append(flag)
                            checkString += string
                field.checkFlag = any(checkFlags)
                field.checkString = checkString

                #add the field to the growing POItem
                po_item.addField(field)
            output.addPOItem(po_item)
                

        return output, gapCheckString


class PO:
    def __init__(self):
        self.items = [] 
        self.globalitems = {}
        self.poitemlist = None
        self.filename = ''
        self.ponumber = ''
        self.extracheckstrings = ''

    def addItem(self, item):
        if item.__class__.__name__ == 'POField':
            self.items.append(item)
            self.globalitems[item.header] = item
            if item.header == 'PO Number':
                ponumber = item.value
                ponumber = ponumber.replace(':', '').replace(' ', '')
                self.ponumber = ponumber
        if item.__class__.__name__ == 'POItemList':
            self.poitemlist = item
        
        # print(item.__class__)

    def addExtraCheckStrings(self, string):
        self.extracheckstrings += string

    def printAll(self):
        for item in self.items:
            item.printVal()
            # if item.__class__.__name__ == 'POItemList':
                # for poitem in item:
                    # poitem.printVal()
            # else:
                # item.printVal()
        if self.poitemlist: 
            self.poitemlist.printVal()
        print('Filename: ', self.filename)

    def tempUploadFunc(self, remote_table):
        ponumber = self
        for item in self.poitemlist.poitems:
            outputdict = item.createTempOutputDict(self.globalitems)
            outputdict['PO Number'] = self.ponumber
            remote_table.create(outputdict)
            print(outputdict)

    def summarizeCheckStrings(self):
        checkstrings = ''
        for item in self.items:
            checkstrings += item.getCheckString()
        
        try:
            checkstrings +=self.poitemlist.getCheckString()
        except AttributeError:
            print("No POItemList in this PO Object.")

        # avoid multiple 'multiTypeItem' flags - usually if there's one, it's the same for every item
        if 'multiTypeItem' in checkstrings:
            checkstrings = checkstrings.replace('multiTypeItem ', '')
            checkstrings += 'multiTypeItems'

        print('Summary of check strings: ', checkstrings)
        print('Extra checks: ', self.extracheckstrings)
             
            
class POItemList:
    def __init__(self):
        self.poitems = []

    def addPOItem(self, item):
        self.poitems.append(item)

    def printVal(self):
        for item in self.poitems:
            item.printVal()

    def getCheckString(self):
        checkstring = ''
        for item in self.poitems:
            checkstring += item.getCheckString()
        return checkstring

class POItem:
    def __init__(self):
        self.fields = {}

    def addField(self, pofield):
        self.fields[pofield.header] = pofield

    def printVal(self):
        outputstring = ''
        for key in self.fields:
            outputstring += self.fields[key].header
            outputstring += ': '
            outputstring += self.fields[key].getValString() + ' | '
        print(outputstring)

    def getCheckString(self):
        checkstring = ''
        for key, field in self.fields.items():
            newcheckstring = field.getCheckString()
            # label checkstrings with the item (this POItem) that they came from,
            # for easier checking
            if (not 'multiTypeItem' in newcheckstring) and newcheckstring != '':
                try:
                    checkstring += self.fields['ITEM'].value
                    checkstring += '-'
                except:
                    pass
            checkstring += newcheckstring
        return checkstring

    def getByHeader(self, header):
        return self.fields[header].value

    def getItemNumber(self):
        try:
            itemnumber = self.fields['ITEM'].value
        except:
            itemnumber = 'No Item Number'
        return itemnumber

    def createTempOutputDict(self, globalfieldsdict):

        try:
            # deldate = self.fields['Estimate'].getValString()
            deldate = self.fields['date'].getValString()
        except KeyError:
            print("TEMP: valid date field not found")
            deldate = None

        try:
            # deldate = self.fields['Estimate'].getValString()
            deldate = self.fields['Targeted Date'].getValString()
        except KeyError:
            print("TEMP: valid date field not found")
            deldate = None

        try:
            deldate = globalfieldsdict['deliverydate']
        except KeyError:
            print("TEMP: no global delivery date")
            deldate = None


        itemno = self.fields['s/n'].getValString()
        outdict = {}
        if deldate != 'None':
            outdict['PO Delivery Date'] = deldate
        if itemno:
            outdict['Item No.'] = itemno
        return outdict

class POField:
    """ 
    class to store data for a single PO field (as on the excel) 
    ideally, will only be a data struct and not hold a lot of functions
    """ 
    def __init__(self, header, value):
        # self.value = str(value).replace('\n', ' @nl ')
        self.value = value
        self.header = header
        self.checkFlag = False
        self.checkString = ''

    def updateVal(self, newVal):
        self.value = newVal

    def getValString(self):
        if self.checkFlag:
            checkoutput = ' c: ' + self.checkString
        else:
            checkoutput = ''
        if self.value.__class__.__name__ == 'datetime':
            valstring = self.value.strftime('%Y-%m-%d')
        else:
            valstring = str(self.value)
        return (valstring.replace('\n', ' @nl ') + checkoutput)

    def getCheckString(self):
        return self.checkString

    def printVal(self):
        valstring = self.getValString()
        print(self.header, ': ', valstring)
        # print(self.header, ': ', valstring, checkoutput)


# ------------ misc global functions -------------

def checkFunction(tree, pofield):
    """ 
        takes a <checkfunction> xml tree and a POField object. 
        returns a tuple with a single checkFlag (bool) and a single checkstring (str)
    """
    checktype = tree.attrib['type']
    checkif = getTreeText(tree, 'checkif', 'match').lower()
    # checkif - does the function set check flag if there's a match, or if there is no match?
    # can be True (match) or False (nomatch). 
    if checkif == 'match':
        checkif = True
    else:
        checkif = False

    checkstring = getTreeText(tree, 'checkstring', '')
    nocheckstring = getTreeText(tree, 'nocheckstring', '')
    outputstring = ''
    outputflag = False

    if checktype == 'regex': #for regex checkfuncs..
        # get the field 'checkstring' etc - if not present, default to empty string
        try:
            # see if whoever input the function into the xml provided a regex. If not, 
            # raise an exception.
            regex = tree.find('regex').text
            string = str(pofield.value)
        except AttributeError:
            print("No regex defined!")
            regex = ''
            return (False, '')
        else:
            if re.search(regex, string):
                check = checkif
            else:
                check = not checkif

    elif checktype == 'typecheck':
        typestring = tree.find('typename').text
        datatype = pofield.value.__class__.__name__
        if typestring == datatype:
            check = checkif
            # print('fooo')
        else:
            check = not checkif

    if check:
        outputstring = checkstring
        outputflag = True
    else: 
        outputstring = nocheckstring
        outputflag = False
        
    return outputflag, outputstring


def getTreeText(tree, fieldname, ifCantFind):
    text = tree.find(fieldname)
    if text != None:
        text = text.text
    else: 
        text = ifCantFind
    return text

