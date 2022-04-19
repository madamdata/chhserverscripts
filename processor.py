import parser as poparser
import re, os, sys, copy


class POProcessor:
    """ Top level class for reading, parsing and executing rules in rules-processor.xml """
    def __init__(self, tree):
        # all the rules
        self.globalrules = {}
        self.itemrules = {}
        # dictionaries to store refs to the rules that will be called first, without being pointed to
        self.globalinitrules = {}
        self.iteminitrules = {}

        self.nodenetwork = PONodeNetwork()
        self.tree = tree

    
        # load rules from the xml
        globalruletree = tree.find('globalrules')
        for ruletree in globalruletree.findall('rule'):
            self.addGlobalRule(ProcessorRule(ruletree, 'global'))
            
        itemruletree = tree.find('itemrules')
        for ruletree in itemruletree.findall('rule'):
            self.addItemRule(ProcessorRule(ruletree, 'item'))

    def addGlobalRule(self, rule):
        self.globalrules[rule.name] = rule
        if rule.sequence == 'init':
            self.globalinitrules[rule.name] = rule
        
    def addItemRule(self, rule):
        self.itemrules[rule.name] = rule
        if rule.sequence == 'init':
            self.iteminitrules[rule.name] = rule

    def getGlobalRule(self, rulename):
        return self.globalrules[rulename]

    def getItemRule(self, rulename):
        return self.itemrules[rulename]

    def parse(self, po_object):
        # initialize starting nodes from the po object
        for item in po_object.items:
            newnode = POFieldNode.fromPOField(item)
            self.nodenetwork.addNode(newnode)
        for poitem in po_object.poitemlist.poitems:
            newnetwork = POItemNetwork.fromPOItem(poitem)
            self.nodenetwork.addpoitem(newnetwork)

            
        # Apply global rules, then individual item rules
        for header, rule in self.globalinitrules.items():
            nextrulename = rule.applyRule(self.nodenetwork)
            while nextrulename != None:
                nextrule = self.globalrules[nextrulename]
                nextrulename = nextrule.applyRule(self.nodenetwork)
                
        for header, rule in self.iteminitrules.items():
            nextrulename = rule.applyRule(self.nodenetwork)
            while nextrulename != None:
                try:
                    nextrule = self.itemrules[nextrulename]
                except KeyError:
                    print("Next rule not found: ", nextrulename)
                    break

                nextrulename = nextrule.applyRule(self.nodenetwork)
        
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
            self.nextrule = tree.find('nextrule').text
        except AttributeError:
            self.nextrule = None

        try: 
            self.sequence = tree.find('sequence').text.lower()
        except AttributeError:
            self.sequence = None

        try: 
            self.type = tree.find('type').text
        except AttributeError:
            self.type = None
            print('Rule has no specified type. Defaulting to :')
        
        self.outs = []
        try:
            self.name = tree.find('name').text
        except AttributeError:
            print('no name provided.')
            self.name = 'ERROR NO NAME'

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
        print('applying rule ', self.name)
        if self.scope == 'global':
            # find the correct function based on the self.type string
            try: 
                function = getattr(self, self.type)
            except AttributeError:
                print('No such function: ', self.type)
            else:
                function(nodenetwork)

        if self.scope == 'item':
            try: 
                function = getattr(self, self.type)
            except AttributeError:
                print('No such function: ', self.type)
            else:
                for item in nodenetwork.poitems:
                    function(item)
            # if self.type == 'splitregex':
                # for item in nodenetwork.poitems:
                    # self.splitregex(item)

        return self.nextrule

    def splitRegex(self, nodenetwork):
        # nodes = nodenetwork.nodes
        splits = self.tree.findall('split')
        multisplits = self.tree.findall('multisplit')
        inputnodename = self.tree.find('input').text
        inputnode = nodenetwork.getNode(inputnodename)
        # inputnode = nodes[inputnodename] #a POFieldNode object
        for item in splits:
           regex = item.find('regex').text
           groups = item.findall('group')

           match = re.search(regex, inputnode.value)
           for group in groups:
               #make output nodes first
               nodename = group.find('node').text
               outnode = nodenetwork.getOrMakeNode(nodename)
           if match:
               #set the POFieldNode value to the specified group of the regex search
               for group in groups:
                   nodename = group.find('node').text
                   outnode = nodenetwork.getOrMakeNode(nodename)
                   groupnumber = int(group.find('groupnumber').text) 
                   try:
                       outnode.value = match.group(groupnumber)
                   except:
                       pass
               # print(match, match.group(0))

        for item in multisplits:
           regex = item.find('regex').text
           basenodename = item.find('node').text #node name template
           try:
               groupnumber = item.find('group').text
           except AttributeError:
               groupnumber = 0
           else: 
               groupnumber = int(groupnumber)
           matchlist = re.findall(regex, inputnode.value)
           if matchlist != []:
               #set the POFieldNode value to the specified group of the regex search
               for item in matchlist:
                   #make specific node name from basenodename template
                   newnodename = basenodename.replace('{}', item[1])
                   outnode = nodenetwork.getOrMakeNode(newnodename)
                   outnode.value = item[0]
               # print(match, match.group(0))

    def matchAndTranslate(self, nodenetwork):
        inputs = self.tree.findall('input')
        translations = self.tree.findall('translate')
        for tr in translations:
            matches = tr.findall('match')
            outval = tr.find('value').text
            outnodename = tr.find('node').text
            outnode = nodenetwork.getOrMakeNode(outnodename)
            matchTruth = []
            for match in matches:
                inp = match.attrib['input']
                regex = match.text
                inpdata = nodenetwork.getNode(inp).value
                if not inpdata:
                    inpdata = ''
                if re.search(regex, inpdata): 
                    matchTruth.append(True)
                else: 
                    matchTruth.append(False)

            if all(matchTruth): #if and only if all matches are True, output the specified value
                outnode.value = outval




class PONodeNetwork:
    def __init__(self):
        self.nodes = {}
        self.poitems = []

    def addNode(self, ponode):
        self.nodes[ponode.header] = ponode

    def getOrMakeNode(self, nodename):
        """if there is such a node in the network, return it. Otherwise, make a blank one and return that.
            called by applyRule
            """
        if nodename in self.nodes:
            return self.nodes[nodename]
        else:
            newnode = POFieldNode(nodename, None)
            self.addNode(newnode)
            return newnode

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

    def getOrMakeNode(self, nodename):
        """if there is such a node in the network, return it. Otherwise, make a blank one and return that.
            called by applyRule
            """
        if nodename in self.nodes:
            return self.nodes[nodename]
        else:
            newnode = POFieldNode(nodename, None)
            self.addNode(newnode)
            return newnode

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
