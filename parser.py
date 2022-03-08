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
        # load triggers, cells, actions etc
        self.name = tree.find('name').text
        outputfield = tree.find('outputfield')
        # get the output field name
        if outputfield != None:
            self.outputfield = outputfield.text

        for trigger in tree.findall('trigger'):
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
        a list of POItems (which contain POFields)
        
        """
        output = None
        extracheckstrings = ''
        if self.matchTrigger(string):
            actionname = self.actiontype
            if actionname == 'Direct Output': 
                actionname = 'getCells'
            elif actionname == 'Parse Table':
                actionname = 'parseTable'
            action = getattr(self, actionname) #find the method of this class that matches the 'actiontype' string
            # the 'action' function is responsible for running the check functions of this inputfield
            output, extracheckstrings = action(self.tree, data_rows, coordinateTuple)
            # check output and store the result in the POField's checkFlag and checkString
        return output, extracheckstrings

    def parseTable(self, tree, data_rows, coordinateTuple):
        """ just runs the parse method of the table parser and returns the output """
        output, extracheckstrings = self.tableparser.parse(data_rows, coordinateTuple)
        return output, extracheckstrings

    def matchTrigger(self, string):
        """ checks every trigger and returns a boolean for match """ 
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

    def getCells(self, tree,  data_rows, coordinateTuple):
        """
        reads all the items in self.cells, and extracts the data from those cells,
        offset from the start cell (coordinateTuple).
        Returns a POField object and a blank extra check string.
        """
        xcoord = coordinateTuple[0]
        ycoord = coordinateTuple[1]
        output = ''
        for item in self.cells:
            xoffset = item[0]
            yoffset = item[1]
            # y first, then x. Just a quirk of how the spreadsheet is stored. 
            targetcell = data_rows[ycoord+yoffset][xcoord+xoffset]
            if targetcell: 
                if targetcell.__class__.__name__ == 'datetime':
                    output += targetcell.strftime('%Y-%m-%d')
                else:
                    output += targetcell
            output += ' '
        field = POField(self.outputfield, output)
        self.runCheckFunctions(field)
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
        for item in outputs.iter('name'):
            self.outputfields.append(item.text)

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
            if self.rawtable[rownum][0] != None:
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
        for colnum in range(0, numCols - 1):
            header = self.rawtable[ycoord][colnum]
            if colnum == 0: #get the first column header and store as the item field title
                itemHeader = header
            if header != None:
                colNumbers.append((header, colnum))
        return colNumbers, itemHeader

    def parse(self, data_rows, coordinateTuple):
        """
        returns a list of POItems and an extra check string
        """
        self.rawtable = data_rows
        xcoord = coordinateTuple[0]
        ycoord = coordinateTuple[1]
        self.tablestartcoord = (xcoord, ycoord)
        self.headers = [header for header in self.rawtable[ycoord] if header != None]
        rowNumbers, gapCheckString = self.getItemRowNumbers(self.tablestartcoord)
        colNumbers, itemHeader = self.getHeadersAndColumnNumbers(self.tablestartcoord)
        output = []
        for row in rowNumbers:
            po_item = POItem()
            for header, column in colNumbers: 
                # make a new POField, with the header and value from the table
                checkFlags = []
                checkString = ''
                field = POField(header, self.rawtable[row][column])
                for checkfunctree in self.checkfunctrees:
                    try:
                        headerregex = checkfunctree.find('header').text
                    except AttributeError:
                        print("No header defined for checkfunction!")#Nonetype has no attribute 'text'
                    else:
                        if re.match(headerregex, header):
                            flag, string = checkFunction(checkfunctree, field)
                            # print(string)
                            checkFlags.append(flag)
                            checkString += string
                field.checkFlag = any(checkFlags)
                field.checkString = checkString

                #add the field to the growing POItem
                po_item.addField(field)
            output.append(po_item)
                

        return output, gapCheckString


class PO:
    def __init__(self):
        self.items = [] 
        self.filename = ''
        self.extracheckstrings = ''

    def addItem(self, item):
        self.items.append(item)
        # print(item.__class__)

    def addExtraCheckStrings(self, string):
        self.extracheckstrings += string

    def printAll(self):
        for item in self.items:
            if item.__class__.__name__ == 'list':
                for poitem in item:
                    poitem.printVal()
            else:
                item.printVal()
        print('Extra checks: ', self.extracheckstrings)

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

    def getByHeader(self, header):
        return self.fields[header].value

class POField:
    """ 
    class to store data for a single PO field (as on the excel) 
    ideally, will only be a data struct and not hold a lot of functions
    """ 
    def __init__(self, header, value):
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
        return (str(self.value) + checkoutput)

    def printVal(self):
        if self.checkFlag:
            checkoutput = ' c: ' + self.checkString
        else:
            checkoutput = ''
        print(self.header, ': ', self.value, checkoutput)


# ------------ misc global functions -------------

def checkFunction(tree, pofield):
    """ returns a tuple with a single checkFlag (bool) and a single checkstring (str) """ 
    checktype = tree.attrib['type']
    if checktype == 'regex': #for regex checkfuncs..
        # get the field 'checkstring' etc - if not present, default to empty string
        checkstring = getTreeText(tree, 'checkstring', '')
        nocheckstring = getTreeText(tree, 'nocheckstring', '')
        outputstring = ''
        outputflag = False

        # checkif - does the function set check flag if there's a match, or if there is no match?
        # can be True (match) or False (nomatch). 
        checkif = getTreeText(tree, 'checkif', 'match').lower()
        if checkif == 'match':
            checkif = True
        else:
            checkif = False

        try:
            # see if whoever input the function into the xml provided a regex. If not, 
            # raise an exception.
            regex = tree.find('regex').text
            string = pofield.value 
        except AttributeError:
            print("No regex defined!")
            regex = ''
            return (False, '')
        else:
            if re.match(regex, string):
                check = checkif
            else:
                check = not checkif

            if check:
                outputstring = checkstring
                outputflag = True
            else: 
                outputstring = nocheckstring
                outputflag = False

            return (outputflag, outputstring)
            # outputstring += ' '
            


def getTreeText(tree, fieldname, ifCantFind):
    text = tree.find(fieldname)
    if text != None:
        text = text.text
    else: 
        text = ifCantFind
    return text

