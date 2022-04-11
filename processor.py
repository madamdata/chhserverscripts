import parser as poparser
import re, os, sys, copy


class POProcessor:
    """ Top level class for reading, parsing and executing rules in rules-processor.xml """
    def __init__(self, tree):
        self.globalrules = []
        self.itemrules = []
        self.nodenetwork = PONodeNetwork()
        self.tree = tree

    
        # load rules from the xml
        globalruletree = tree.find('globalrules')
        for ruletree in globalruletree.findall('rule'):
            self.globalrules.append(ProcessorRule(ruletree, 'global'))
            
        itemruletree = tree.find('itemrules')
        for ruletree in itemruletree.findall('rule'):
            self.itemrules.append(ProcessorRule(ruletree, 'item'))



    def parse(self, po_object):
        # initialize starting nodes from the po object
        for item in po_object.items:
            newnode = POFieldNode.fromPOField(item)
            self.nodenetwork.addNode(newnode)
        for poitem in po_object.poitemlist.poitems:
            newnetwork = POItemNetwork.fromPOItem(poitem)
            self.nodenetwork.addpoitem(newnetwork)

        # create blank nodes by scanning the xml 
        # tempNodeDict is used to remove duplicates
        # first globals, then items
        globalruletree = self.tree.find('globalrules')
        itemruletree = self.tree.find('itemrules')
        tempNodeDict = {}
        for node in globalruletree.iter('node'):
            tempNodeDict[node.text] = None
        for header in tempNodeDict:
            newnode = POFieldNode(header, None)
            self.nodenetwork.addNode(newnode)

        tempNodeDict = {}
        for node in itemruletree.iter('node'):
            tempNodeDict[node.text] = None
        for header in tempNodeDict:
            newnode = POFieldNode(header, None)
            self.nodenetwork.addItemNode(newnode)
            
        # Apply global rules, then individual item rules
        for rule in self.globalrules:
            rule.applyRule(self.nodenetwork)
        for rule in self.itemrules:
            rule.applyRule(self.nodenetwork)
        
        return self.nodenetwork

    def listNodes(self):
        self.nodenetwork.listNodes()

class ProcessorRule:
    """ class for parsing and executing individual rule """ 
    def __init__(self, tree, scope):
        self.regex = None
        self.tree = tree
        self.scope = scope
        self.triggers = []
        try: 
            self.type = tree.find('type').text.lower()
        except AttributeError:
            self.type = None
            print('Rule has no specified type. Defaulting to :')
        
        self.outs = []
        try:
            self.name = tree.find('name').text
        except AttributeError:
            print('no name provided.')

        # load outs
        try:
            for outtree in tree.find('out'):
                self.outs.append(outtree)
        except:
            pass

        try: 
            self.regex = tree.find('regex').text
        except AttributeError:
            if self.type == 'regex':
                print('Type set to regex but no regex string provided.')


    def applyRule(self, nodenetwork):
        if self.scope == 'global':
            if self.type == 'splitregex':
                self.splitRegex(nodenetwork)
                   # print(regex, node)

        if self.scope == 'item':
            if self.type == 'splitregex':
                for item in nodenetwork.poitems:
                    self.splitRegex(item)

    def splitRegex(self, nodenetwork):
        # nodes = nodenetwork.nodes
        splits = self.tree.findall('split')
        inputnodename = self.tree.find('input').text
        inputnode = nodenetwork.getNode(inputnodename)
        # inputnode = nodes[inputnodename] #a POFieldNode object
        for item in splits:
           regex = item.find('regex').text
           nodename = item.find('node').text
           try:
               groupnumber = item.find('group').text
           except AttributeError:
               groupnumber = 0
           else: 
               groupnumber = int(groupnumber)

           outnode = nodenetwork.getNode(nodename)
           match = re.search(regex, inputnode.value)
           if match:
               #set the POFieldNode value to the specified group of the regex search
               outnode.value = match.group(groupnumber)
               # print(match, match.group(0))



class PONodeNetwork:
    def __init__(self):
        self.nodes = {}
        self.poitems = []

    def addNode(self, ponode):
        self.nodes[ponode.header] = ponode

    def addItemNode(self, ponode):
        for item in self.poitems:
            item.addNode(copy.copy(ponode))

    def getNode(self, nodename):
        return self.nodes[nodename]

    def addpoitem(self, poitem):
        self.poitems.append(poitem)

    def listNodes(self):
        # currently called manually in the main script
        print("Listing nodes --- \n")
        for header, node in self.nodes.items():
            # print(header, ": ", node.value)
            node.printAll()

        for poitem in self.poitems:
            poitem.printAllNodes()

    def getNode(self, header):
        return self.nodes[header]

class POItemNetwork:
    """ analogous to POItem in the scraper module - data struct. """ 
    def __init__(self, itemnumber, poitem):
        self.nodes = {}
        self.itemnumber = itemnumber
        self.poitem_object = poitem
        for header, field in poitem.fields.items():
            self.nodes[header] = POFieldNode.fromPOField(field)

    def addNode(self, ponode):
        self.nodes[ponode.header] = ponode

    def getNode(self, nodename):
        return self.nodes[nodename]

    def printAllNodes(self):
        outstring = ''
        for header, node in self.nodes.items():
            outstring += node.getPrintString()
        print(outstring)

    @classmethod
    def fromPOItem(cls, poitem):
        newnetwork = POItemNetwork(poitem.getItemNumber, poitem)
        return newnetwork

class POFieldNode:
    """ analagous to POField in the scraper module - a data struct. """


    def __init__(self, header, value):
        self.header = header
        self.value = value
        self.checkFlag = False
        self.checkString = ''

    def printAll(self):
        print(self.header, ' : ', self.value, ' - ', self.checkFlag, ' ', self.checkString)

    def getPrintString(self):
        string = ''
        if self.value:
            string = self.header + ' : ' + str(self.value) + ' - ' + ' ' + self.checkString + '| '
        return string 
        
    @classmethod
    def fromPOField(cls, pofield):
        newnode = POFieldNode(pofield.header, pofield.value)
        newnode.checkFlag = pofield.checkFlag
        newnode.checkString = pofield.checkString
        return newnode
