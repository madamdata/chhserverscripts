import parser as poparser
import re, os, sys, copy, pyairtable, datetime, requests


class POProcessor:
    """ Top level class for reading, parsing and executing rules in rules-processor.xml """
    def __init__(self, tree):
        # all the rules
        self.globalrules = {}
        self.itemrules = {}
        self.checkrules = {}
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

        checkruletree = tree.find('checkrules')
        for ruletree in checkruletree.findall('rule'):
            self.addCheckRule(ProcessorRule(ruletree, 'item'))

    def addGlobalRule(self, rule):
        self.globalrules[rule.name] = rule
        if rule.sequence == 'init':
            self.globalinitrules[rule.name] = rule
        
    def addItemRule(self, rule):
        self.itemrules[rule.name] = rule
        if rule.sequence == 'init':
            self.iteminitrules[rule.name] = rule

    def addCheckRule(self, rule):
        self.checkrules[rule.name] = rule

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

        for header, rule in self.globalrules.items():
            rule.applyRule(self.nodenetwork)
                
        for header, rule in self.itemrules.items():
            rule.applyRule(self.nodenetwork)
        
        return self.nodenetwork

    def upload(self, uploadrulename, remote_table, **kwargs):
        # print(self.checkrules) 
        try:
            dryrun = kwargs['dryrun']
        except KeyError:
            dryrun = False

        try:
            uploadrule = self.checkrules[uploadrulename]
        except KeyError:
            print('No upload rule found by that name: ', uploadrulename)
            return None
        nodetrees = uploadrule.tree.findall('node') 
        #print ------------ upload data ------------- marker
        if kwargs['printout']:
            if dryrun:
                print('---------------- UPLOAD DATA (DRY RUN) -----------------')
            else:
                print('---------------- UPLOAD DATA -----------------')
        for poitem in self.nodenetwork.poitems:
            nodes = {}
            for tr in nodetrees:
                val = poitem.getOutputValue(tr.attrib['name']) #returns node value or None
                try:
                    valtype = tr.attrib['type']
                except KeyError:
                    valtype = None
                # if a field name is specified in the xml, use that, otherwise use node name
                header = tr.text
                if header == None:
                    header = tr.attrib['name']
                # check types
                if val == '':
                    val = None
                if val:
                    if valtype == 'string':
                        val = str(val)
                    if valtype == 'int':
                        try:
                            val = int(val)
                        except ValueError: #can't be bodged into int
                            val = None
                    if valtype == 'float':
                        try:
                            val = float(val)
                        except ValueError: #can't be bodged into float
                            val = None
                    if valtype == 'list':
                        val = [val]
                    if valtype == 'datetime':
                        # if it's supposed to be datetime and it's not, don't upload
                        if val.__class__.__name__ != 'datetime':
                            val = None
                        else:
                            val = val.strftime('%Y-%m-%d')
                #apply extra processing if there is an 'extra' attribute
                try:
                    if tr.attrib['extra'] == 'stripspaces':
                        if val: 
                            val = val.replace(' ', '')
                except KeyError:
                    pass
                if val != None:
                    nodes[header] = val

            # see 'printout' variable from kwargs
            if kwargs['printout']: 
                print(nodes, '\n')

            if not dryrun:
                try:
                    remote_table.create(nodes)
                except requests.exceptions.HTTPError as error:
                    # Error handling - if it's one of the usual wrong field / no option errors, post only revelant info
                    errortext = repr(error)
                    errmatch = re.search(r'(select option|Unknown field name).*', errortext)
                    if errmatch:
                        print("HTTPError - ", errmatch.group(0), '\n')
                        emergencynodes = {}
                        emergencynodes['PO Number'] = nodes['PO Number']
                        try:
                            remote_table.create(emergencynodes)
                        except requests.exceptions.HTTPError as error:
                            print("Sorry can't help you, emergency upload also threw an error")
                    else:
                        print(errortext)

        # nodes = []
        # for tr in nodetrees:
            
        


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

    def evaluateRuleCondition(self, nodenetwork):
        conditiontree = self.tree.find('condition')
        if not conditiontree:
            return True

        inp = conditiontree.find('node').attrib['name']
        inpnode = nodenetwork.getNode(inp) 
        conditiontype = conditiontree.attrib['type']
        # parity = conditiontree.attrib['parity'],
        output = False
        if inpnode:
            val = inpnode.value
            if conditiontype == 'match':
                regex = conditiontree.find('regex').text
                match = re.search(regex, val)
                if match:
                    output = True
                else:
                    output = False
            elif conditiontype == 'nomatch':
                regex = conditiontree.find('regex').text
                match = re.search(regex, val)
                if match:
                    output = False
                else:
                    output = True

        # if testing for node exists, fail True
        if conditiontype == 'nodeDoesNotExist': 
            if inpnode:
                output = False
            else:
                output = True
        if conditiontype == 'nodeExists': 
            if inpnode:
                output = True
            else:
                output = False

        return output

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
                if self.evaluateRuleCondition(nodenetwork):
                    function(nodenetwork)

        if self.scope == 'item':
            try: 
                function = getattr(self, self.type)
            except AttributeError:
                print('No such function: ', self.type)
            else:
                for item in nodenetwork.poitems:
                    if self.evaluateRuleCondition(item):
                        # print(item.itemnumber())
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

    def copyNode(self, nodenetwork):
        """
        copies nodes within the network
        """
        # inputs = self.tree.findall('input')
        inp = self.tree.find('input').text 
        newnodename = self.tree.find('newnodename').text
        inpnode = nodenetwork.getNode(inp)
        if inpnode and inpnode.value:
            newnode = copy.copy(inpnode)
            newnode.header = newnodename
            # print("COPYING ", newnodename)
            nodenetwork.addNode(newnode) #WILL OVERRIDE NODES OF THE SAME NAME

    def coerceDate(self, nodenetwork):
        """ tries to get whatever fubar date format provided by the client into
        something recognizable, usually a datetime object """ 
        inp = self.tree.find('input').text
        inpnode = nodenetwork.getNode(inp)
        if inpnode:
            val = inpnode.value
            try: 
                val = datetime.datetime.strptime(val, '%d/%m/%Y')
            except ValueError: #if it's some other unrecognizable fubar string
                pass
            except TypeError: #if it's actually a datetime object already
                pass
            try: 
                val = datetime.datetime.strptime(val, '%Y-%m-%d')
            except ValueError:
                pass
            except TypeError:
                pass

            if val == 'ASAP':
                val = datetime.datetime.now()
            inpnode.value = val

    def copyToItems(self, nodenetwork):
        """ copies a node from global to every child POItemNetwork """
        inp = self.tree.find('input').text 
        newnodename = self.tree.find('newnodename').text
        inpnode = nodenetwork.getNode(inp)
        if inpnode:
            newnode = copy.copy(inpnode)
            newnode.header = newnodename
            for poitem in nodenetwork.poitems:
                poitem.addNode(newnode)

    def copyByRegex(self, nodenetwork):
        """ GLOBAL ONLY - for copying splitA, splitB etc to individual items """
        regex = self.tree.find('regex').text
        # print(regex)
        keyfield = self.tree.find('keyfield').text
        newnodename = self.tree.find('newnodename').text
        for header, node in nodenetwork.nodes.items():
            # does the header of the global node match the regex?
            match = re.match(regex, header)
            if match:
                group = match.group(1)
                for poitem in nodenetwork.poitems:
                    keynode = poitem.nodes[keyfield]
                    if group in keynode.value:
                        newnode = copy.deepcopy(node)
                        newnode.header = newnodename
                        # print('copying ', keynode.value, newnode.value)
                        poitem.addNode(newnode)
            
            

    def substituteNodeValues(self, string, nodenetwork):
        """
        replaces {foo} in string with {value of node foo}
        called in matchAndTranslate
        """
        listOfReplacements = []
        if string:
            substitutions = re.findall(r'\{(.+?)\}', string)
            for item in substitutions:
                replacementText = ''
                node = nodenetwork.getNode(item)
                if node:
                    replacementText = node.value
                    if replacementText == None:
                        replacementText = ''
                    # print(outval)
                    # print(replacementText)
                    # print(outvalTmpSub)
                listOfReplacements.append(replacementText)
            # print(listOfReplacements)
            outstring = re.sub('\{.+?\}', '{}', string)
            outstring = outstring.format(*listOfReplacements)
            return outstring

    def mathx10RS(self, nodenetwork):
        """ multiplies by 10. unless the result is more than 1350.
            for bizarre RS model strings with inconsistent sizing"""
        inp = self.tree.find('input').text
        inpnode = nodenetwork.getNode(inp)
        # print(inpnode)
        out = self.tree.find('node').attrib['name']
        outnode = nodenetwork.getOrMakeNode(out)
        if inpnode: 
            try:
                outval = float(inpnode.value) * 10 
                if outval > 1600:
                    outval = outval/10
            except ValueError:
                print('input not a number: ', inp)
            outval = int(outval)
            outnode.value = outval

    def matchAndTranslate(self, nodenetwork):
        """
            translates (modifies) a node's contents based on
            whether it matches various regexes.
        """
        inputs = self.tree.findall('input')
        translations = self.tree.findall('translate')
        for tr in translations:
            matches = tr.findall('match')
            #### TO DO --> make it possible for multiple output nodes ###
            outnodetrees = tr.findall('node')
            outnodes = []
            # outnode = nodenetwork.getOrMakeNode(outnodename)

            # Test for the presence of all matches
            matchTruth = []
            for match in matches:
                inp = match.attrib['input']
                try:
                    matchtype = match.attrib['matchtype']
                except KeyError: #no 'matchtype' attrib - assume type is match
                    matchtype = 'match'
                regex = match.text
                inpnode = nodenetwork.getNode(inp)
                # print(nodenetwork.itemnumber())
                if inpnode:
                    inpdata = inpnode.value
                else:
                    inpdata = None
                if not inpdata:
                    inpdata = ''

                # if inpdata.__class__.__name__ == 'datetime':
                    # #dates will ALWAYS match
                    # matchTruth.append(True)
                if re.search(regex, str(inpdata)): 
                    if matchtype == 'match':
                        matchTruth.append(True)
                    else:
                        matchTruth.append(False)
                else: 
                    if matchtype == 'match':
                        matchTruth.append(False)
                    else:
                        matchTruth.append(True)

            if all(matchTruth): #if and only if all matches are True, output the specified value
                for tree in outnodetrees:
                    nodename = tree.attrib['name']
                    node = nodenetwork.getOrMakeNode(nodename)
                    outval = tree.text #if there is no text between the xml <node> tags, this is None rather than ''
                    outval = self.substituteNodeValues(outval, nodenetwork) #sub in values of any other nodes in {curly braces}
                    node.value = outval

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
               try: 
                   match = re.search(regex, inputnode.value)
               except TypeError: #inputnode.value is not a string - probably a datetime
                   #print('Splitregex: node value is not a string and cannot be regexed.')
                   match = False
                   pass

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
        """ adds a node. Overwrites existing nodes of the same name """
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

    def getAllNodesByRegex(self, nameregex):
        nodes = []
        for header, node in self.nodes.items():
            if re.match(nameregex, header):
                nodes.append(node)
        return nodes

            

    def listNodes(self, **kwargs):
        # currently called manually in the main script
        try:
            nodenames = kwargs['nodenames']
        except KeyError:
            nodenames = []
        print("------------ PROCESSOR OUTPUT : Listing nodes ", nodenames, '----------------- \n')
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

    def getOutputValue(self, nodename):
        node = self.getNode(nodename)
        output = None
        if node:
            output = node.value
        return output

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
        outstring = outstring.replace('\n', '@nl')
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
        value = pofield.value
        if value.__class__ == str :
            value = value.replace('\n', '@nl')

        newnode = POFieldNode(pofield.header, value)
        newnode.checkFlag = pofield.checkFlag
        newnode.checkString = pofield.checkString
        return newnode

