import re
'''
These classes are mainly data structures with some functions for internal processing. 
The scraping should be left to the scraper script. 

'''

class PO:

    def __init__(self):
        self.items = []
        self.globaldetails = {
                'PO Number' : '-',
                'Project Site' : '-',
                'PO Date' : None,
                'PO Delivery Date' : None,
                'Note Raw' : None,
                'Detail Raw' : None,
                'Motor Brand': None,
                'Motor Speed': None,
                'Motor Voltage': None,
                'Motor Class': None,
                'Filename': None
                }

    def setglobal(self, key, val): #called in scraper.py for each PO-wide field
        self.globaldetails[key] = val
        if key == 'Detail Raw':
            self.parseDetailString(val) #parse detail string for additional global fields
        if self.items: 
            for poitem in self.items:
                poitem.addEntryDict(self.globaldetails)
                

    def addItem(self, poitem):
        self.items.append(poitem)

    def parseDetailString(self, detailstring): # called once per PO 
        splitstring = detailstring.split(',') #split into parts based on commas
        ex_proof = False
        for index, item in enumerate(splitstring): #search every part for various regex matches. 
            match1 = re.search(r'(Teco|RAEL|Att) Motor', item)
            if match1:
                self.globaldetails['Motor Brand'] = match1.group(1) 

            match2 = re.search(r'(\d) Pole', item)
            if match2:
                if match2.group(0) == '2 Pole':
                    self.globaldetails['Motor Speed'] = '2880'
                elif match2.group(0) == '4 Pole':
                    self.globaldetails['Motor Speed'] = '1440'
                elif match2.group(0) == '2/4 Pole':
                    self.globaldetails['Motor Speed'] = '2880/1440'


            match3 = re.search(r'(\d+)v', item)
            if match3:
                self.globaldetails['Motor Voltage'] = match3.group(1) + 'V'
            
            match4 = re.search(r'Class .', item)
            if match4:
                motorclass = match4.group(0)
                try:
                    nextitem = splitstring[index+1] #search the next segment after the comma
                except IndexError:
                    nextitem = ''

                classmatch = re.search(r'IP55 \((.) Series\)', nextitem)
                if classmatch:
                    motorclass += ' (' + classmatch.group(1) + ')'
                
                self.globaldetails['Motor Class'] = motorclass

            match5 = re.search(r'Axial(.*)', item)
            if match5:
                if match5.group(1) == '-EX':
                    ex_proof = True


    def convertAll(self): 
        """ 
        called once at end of scraper.py. Updates all child POItems with global details, then calls
        convertallparams() on each child POItem.
        """
        if self.items: 
            for poitem in self.items: #append all global parameters to each child POItem()
                poitem.addEntryDict(self.globaldetails)
        for item in self.items:
            item.convertallparams()
    
    def update_remote(self, remote_table):
        """call update_remote on all child POItems""" 
        for item in self.items:
            item.update_remote(remote_table)

    def print_all_output(self):
        """ for dumping to log. calls print_output_dict on all child POItems """ 
        for item in self.items:
            item.print_output_dict()

class POItem:

    # input_params_list : keys -> by default, field names as on the airtable database. sometimes it is a placeholder
    # parameter like 'model' that needs to be parsed into the correct output fields. 
    # by default, placeholder parameters start with '_'
    # values -> list of potential things the client might call them, ie aliases
    input_params_list = {
            # PO - level params
            'PO Number':['ponumber', 'PO Number'],
            'Filename':['Filename'],
            'Project Site':['Project Site'],
            'PO Delivery Date':['PO Delivery Date'],
            'PO Date': ['PO Date'],
            'Note Raw': ['Note Raw'],
            'Detail Raw': ['Detail Raw'],
            'Motor Brand': ['Motor Brand'],
            'Motor Speed': ['Motor Speed'],
            'Motor Voltage': ['Motor Voltage'],
            
            # either?
            'Motor Class': ['Motor Class', 'Class', 'CLASS'],

            # Item - level params
            '_model':['MODEL','Model / Description', 'Model'], 
            'T-box Position': ['T/BOX', 'T/Box'], 
            'Motor Size': ['MOTOR', 'Motor'], 
            'Qty': ['QTY', 'Qty', 'Qty/Uts'], 
            'Price per Unit': ['S$U/P', 'S$ U/P'], 
            'Motor Frame (Scrapped)': ['Frame', 'FRAME'] 
            }


    def __init__(self):
        self.input_dict={}
        #fill input_dict with 'None' - this allows for the correct fall-through behaviour later. 
        #if nothing is done, item will remain as 'None' and the appropriate errors will be caught, 
        #or it will be detected at the conversion stage and not converted and not uploaded.
        for item in self.__class__.input_params_list.keys(): 
            self.input_dict[item] = None 
            self.output_dict={}

    def addEntry(self, entryTuple):
        """
        Inputs an entry into input_dict. Coerces all of the aliases in input_params_list
        into the standardized field names.
        """
        entry_header = entryTuple[0]
        entry_data = entryTuple[1]
        if entry_data == '':
            entry_data = None
        for param, aliases in self.__class__.input_params_list.items():
            if entry_header in aliases:
                self.input_dict[param] = entry_data

    def addEntryDict(self, entriesDict):
        """ addEntry, but with a dictionary of items rather than a tuple with a single item """ 
        for k,v in entriesDict.items():
            self.addEntry((k,v))

    def parse_model_string(self, modelstring): #called by convert()
        """ 
        Called by convert(). Reads the model string and matches against a set of regexes.
        returns a dictionary called 'fields' of appropriate airtable-fields and values
        """
        modelstring = modelstring.replace('\n', ' ')
        fields = {}
        match = re.match(r'^(BIF|AND|RV|DQ)(-Ex|-GVD|-CR|-T)? (([0-9]+)\/([^\/]+\/.+?( \((\d+)mmL\).*?)?)|(.+))$', modelstring)
        match2 = re.match(r'^(RS|RSM) ([0-9]+)(-[\d.]+[dD].*)?', modelstring)
        match3 = re.match(r'^(Matching Flanges|Mounting Feet) ([0-9]+)mm.*$', modelstring)
        match4 = re.match(r'^(DKHRC|DKHR|EKHR) ([0-9]+)(-.+?) ?(\(LG 0\))?$', modelstring)
        match5 = re.match(r'^(Guide Vane) (\d+).*?(\d+ Blades), ?(\d+)mmL', modelstring)
        item = size = impeller = silencer_size = fan_direction = casing_length = motor_size = None
        if match:
            item, size, impeller = \
                    match.group(1), match.group(4), match.group(5)
            
            extra = match.group(2)
            if match.group(7):
                casing_length = match.group(7)

            if item == 'AND':
                item = 'Ax'
            elif item == 'BIF':
                if extra == '-T':
                    item = 'Bif T/p'
                else:
                    item = 'Bif'
            elif item == 'RV':
                item = 'RV - Ax'
            elif item == 'DQ':
                item = 'DQ - Ax'

        elif match2:
            item = match2.group(1)
            size = match2.group(2) + '0'
            if match2.group(3):
                silencer_size = match2.group(3)

        elif match3:
            gr1 = match3.group(1)
            if gr1 == "Matching Flanges":
                item = 'MFlanges'
                motor_size = '-'
            elif gr1 == "Mounting Feet":
                item = 'MFeet'
                motor_size = '-'
            size = match3.group(2)

        elif match4:
            item = match4.group(1)
            size = match4.group(2)
            silencer_size = match4.group(3)
            if match4.group(4):
                fan_direction = match4.group(4)
        
        elif match5:
            item = match5.group(1)
            size = match5.group(2)
            impeller = match5.group(3)
            casing_length = match5.group(4)

        if not (match or match2 or match3 or match4 or match5):
            print("Model string doesn't match any known configuration: ", modelstring)
            return None

        fields['Item'] = item
        fields['Size'] = size
        fields['Motor Size'] = motor_size
        fields['Impeller'] = impeller
        fields['Silencer Size'] = silencer_size
        fields['Fan Direction'] = fan_direction
        fields['Casing Length (Special)'] = casing_length
        return fields
            

    def convert(self, key):
        """Called by convertallparams(). returns a dictionary with the output (airtable-correct) key, and
        the output data. Output data is simply the value in the key:value pair,
        unless processing is necessary"""
        output_data = {}
        if key == '_model':
            model_string = self.input_dict['_model'].replace('\n', '')
            output_data['Item Raw'] = model_string
            try:
                for k, v in self.parse_model_string(model_string).items(): #parse_model_string returns a dict of fields and values
                    output_data[k] = v
            except AttributeError:
                pass

        elif key == 'Motor Size':
            motor_string = self.input_dict['Motor Size'];
            motor_number = None
            try:
                motor_number = re.search(r'([0-9\.]+).*', motor_string).group(1)
            except IndexError:
                pass
            except AttributeError:
                pass
            except TypeError: #no motor string
                pass
            if motor_number == '4':
                motor_number = '4.0'
            elif motor_number == '3':
                motor_number = '3.0'
            output_data['Motor Size'] = motor_number
        elif key == 'Motor Class':
            motor_class = self.input_dict['Motor Class']
            if motor_class != None:
                if re.match(r'^[a-zA-Z]$', motor_class):  #if it's a single letter, add 'class', else pass it along
                    motor_class = 'Class' + motor_class_intable.upper()
                    output_data['Motor Class'] = motor_class_intable
            output_data['Motor Class'] = motor_class

        elif key == 'Qty':
            qty = self.input_dict['Qty']
            qty = re.match(r'(\d+).*', qty).group(1)
            qty = int(qty)
            output_data['Qty'] = qty
        elif key == 'Price per Unit':
            ppu = self.input_dict['Price per Unit']
            try:
                ppu = float(ppu)
            except ValueError:
                if ppu == '-': 
                    ppu = None
                    pass
                else:
                    print("ValueError: Price per unit doesn't seem to be a number:", ppu)
            except TypeError:
                print("TypeError: Price per unit doesn't seem to be a number:", ppu)

            output_data['Price per Unit'] = ppu
            
        else: #if the input key is not one of the above, just pass the key and its associated data straight to the output
            output_data[key] = self.input_dict[key]

        return output_data

    def convertallparams(self):
        """
        convert internal parameters to correct airtable names and
        do any math / splitting / conversion needed. 

        """
        self.output_dict = {}
        # for every input item, run the self.convert() method on the key
        # self.convert() returns a dictionary of processed key:value pairs
        # where the keys are correct for the airtable fields.
        # only add to the dictionary if the value is not None.
        for key in self.__class__.input_params_list:
            for k, v in self.convert(key).items():
                if v != None:
                    self.output_dict[k] = v
        return self.output_dict

    def update_remote(self, remote_table):
        """send contents of output_dict to airtable as a new record""" 
        remote_table.create(self.output_dict)

    def print_output_dict(self): 
        """ for dumping to log """ 
        output_dict_printstring = ''
        for k, v in self.output_dict.items():
            output_dict_printstring += ' ' + str(k) + ' : ' +  str(v) +  '   |   '
        print(output_dict_printstring)
