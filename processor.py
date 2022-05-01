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

    def listNodes(self):
        self.nodenetwork.listNodes()

    def parse(self, po_object):
        # initialize starting nodes from the po object
        for item in po_object.items:
            newnode = POFieldNode.fromPOField(item)
            self.nodenetwork.addNode(newnode)
        for poitem in po_object.poitemlist.poitems:
            newnetwork = POItemNetwork.fromPOItem(poitem)
            self.nodenetwork.addpoitem(newnetwork)

            
        # Apply global rules, then individual item rules
        # for header, rule in self.globalinitrules.items():
            # nextrulename = rule.applyRule(self.nodenetwork)
            # while nextrulename != None:
                # nextrule = self.globalrules[nextrulename]
                # nextrulename = nextrule.applyRule(self.nodenetwork)
        for header, rule in self.globalrules.items():
            rule.applyRule(self.nodenetwork)

                
        # for header, rule in self.iteminitrules.items():
            # nextrulename = rule.applyRule(self.nodenetwork)
            # while nextrulename != None:
                # try:
                    # nextrule = self.itemrules[nextrulename]
                # except KeyError:
                    # print("Next rule not found: ", nextrulename)
                    # break

                # nextrulename = nextrule.applyRule(self.nodenetwork)
        for header, rule in self.itemrules.items():
            rule.applyRule(self.nodenetwork)
        
        return self.nodenetwork

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
            self.type = tree.attrib['type']
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
        """ Applies the rule and returns the name of the next rule to apply """
        # print('applying rule ', self.name)
        if self.scope == 'global':
            # find the correct function based on the self.type string
            # eg <type>splitRegex</type>
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
    
    def alias(self, nodenetwork):
        """
        renames nodes
        """
        # inputs = self.tree.findall('input')
        aliases = self.tree.findall('alias')
        for al in aliases:
            name = al.attrib['name']
            newname = al.text
            nodenetwork.renameNode(name, newname)

    def matchAndTranslate(self, nodenetwork):
        """
            translates (modifies) a node's contents based on
            whether it matches various regexes.
        """
        inputs = self.tree.findall('input')
        translations = self.tree.findall('translate')
        for tr in translations:
            matches = tr.findall('match')
            outval = tr.find('node').text
            #### TO DO --> make it possible for multiple output nodes ###
            outnodename = tr.find('node').attrib['name']
            outnode = nodenetwork.getOrMakeNode(outnodename)

            matchTruth = []
            for match in matches:
                inp = match.attrib['input']
                regex = match.text
                inpnode = nodenetwork.getNode(inp)
                # print(nodenetwork.itemnumber())
                if inpnode:
                    inpdata = inpnode.value
                else:
                    inpdata = None
                if not inpdata:
                    inpdata = ''
                if re.search(regex, inpdata): 
                    matchTruth.append(True)
                else: 
                    matchTruth.append(False)

            if all(matchTruth): #if and only if all matches are True, output the specified value
                outnode.value = outval

    def splitRegex(self, nodenetwork):
        """ 
            divides an input string based on regex matches and splits the groups to 
            different nodes.
        """
        # nodes = nodenetwork.nodes
        splits = self.tree.findall('split')
        multisplits = self.tree.findall('multisplit')
        inputnodename = self.tree.find('input').text
        inputnode = nodenetwork.getNode(inputnodename)
        # inputnode = nodes[inputnodename] #a POFieldNode object
        if inputnode:
            for item in splits:
               regex = item.find('regex').text
               groups = item.findall('group')

               match = re.search(regex, inputnode.value)
               # for group in groups:
                   # nodename = group.find('node').attrib['name']
                   # outnode = nodenetwork.getOrMakeNode(nodename)
               if match:
                   #set the POFieldNode value to the specified group of the regex search
                   #make output nodes first
                   for group in groups:
                       nodename = group.find('node').attrib['name']
                       outnode = nodenetwork.getOrMakeNode(nodename)
                       try:
                           groupnumber = int(group.attrib['number']) 
                       except:
                           groupnumber = 0

                       try:
                           outnode.value = match.group(groupnumber)
                       except:
                           pass
                   # print(match, match.group(0))

            for item in multisplits:
               regex = item.find('regex').text
               basenodename = item.find('node').attrib['name'] #node name template
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




class PONodeNetwork:
    def __init__(self):
        self.nodes = {}
        self.poitems = []

    def addItemNode(self, ponode):
        for item in self.poitems:
            item.addNode(copy.copy(ponode))

    def addNode(self, ponode):
        self.nodes[ponode.header] = ponode

    def addpoitem(self, poitem):
        self.poitems.append(poitem)

    def renameNode(self, nodename, newnodename):
        try:
            node = self.nodes[nodename]
        except KeyError:
            return None
        else:
            node.header = newnodename
            self.nodes[newnodename] = node
            self.nodes.pop(nodename)

    def getNode(self, header):
        node = None
        try:
            node = self.nodes[header]
        except KeyError:
            pass
            # print("No such node, skipping: ", header)
        return node

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


    def listNodes(self, **kwargs):
        # currently called manually in the main script
        try:
            nodenames = kwargs['nodenames']
        except KeyError:
            nodenames = []
        print("Listing nodes --- ", nodenames, '\n')
        for header, node in self.nodes.items():
            # print(header, ": ", node.value)
            if (header in nodenames) or ('allglobal' in nodenames) or (nodenames == []):
                node.printAll()

        for poitem in self.poitems:
            poitem.printNodes(nodenames)


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
        node = None
        try:
            node = self.nodes[nodename]
        except KeyError:
            # print("No such node, skipping: ", nodename)
            pass
        return node

    def renameNode(self, nodename, newnodename):
        try:
            node = self.nodes[nodename]
        except KeyError:
            return None
        else:
            node.header = newnodename
            self.nodes[newnodename] = node
            self.nodes.pop(nodename)

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

    def printNodes(self, nodenames):
        outstring = ''
        for header, node in self.nodes.items():
            if (header in nodenames) or (nodenames == []) or ('allitems' in nodenames):
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

    def getPrintString(self):
        string = ''
        if self.value:
            string = self.header + ' : ' + str(self.value) + ' - ' + ' ' + self.checkString + '| '
        return string 
        
    def printAll(self):
        print(self.header, ' : ', self.value, ' - ', self.checkFlag, ' ', self.checkString)

    @classmethod
    def fromPOField(cls, pofield):
        newnode = POFieldNode(pofield.header, pofield.value)
        newnode.checkFlag = pofield.checkFlag
        newnode.checkString = pofield.checkString
        return newnode
