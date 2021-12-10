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
                'Motor Class': None
                }

    def setglobal(self, key, val):
        self.globaldetails[key] = val
        if key == 'Detail Raw':
            self.parseDetailString(val)
        if self.items: 
            for poitem in self.items:
                poitem.addEntryDict(self.globaldetails)
                

    def addItem(self, poitem):
        self.items.append(poitem)

    def parseDetailString(self, detailstring):
        splitstring = detailstring.split(',')
        print(splitstring)
        for index, item in enumerate(splitstring):
            match1 = re.search(r'(Teco) Motor', item)
            if match1:
                self.globaldetails['Motor Brand'] = match1.group(1) 

            match2 = re.search(r'(\d) Pole', item)
            if match2:
                if match2.group(0) == '2 Pole':
                    self.globaldetails['Motor Speed'] = '2880'
                elif match2.group(0) == '4 Pole':
                    self.globaldetails['Motor Speed'] = '1440'


            match3 = re.search(r'(\d+)v', item)
            if match3:
                self.globaldetails['Motor Voltage'] = match3.group(1) + 'V'
            
            match4 = re.search(r'Class .', item)
            if match4:
                motorclass = match4.group(0)
                try:
                    nextitem = splitstring[index+1]
                except IndexError:
                    nextitem = ''
                    print('Unknown motor class: ', motorclass)

                classmatch = re.search(r'IP55 \((.) Series\)', nextitem)
                if classmatch:
                    motorclass += ' (' + classmatch.group(1) + ')'
                    self.globaldetails['Motor Class'] = motorclass

        pass

    def convertAll(self):
        if self.items: 
            for poitem in self.items:
                poitem.addEntryDict(self.globaldetails)
        for item in self.items:
            item.convertallparams()
    
    def update_remote(self, remote_table):
        for item in self.items:
            item.update_remote(remote_table)

    def sync(self, remote_table):
        print("test")

    def print_all_output(self):
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
            'Project Site':['Project Site'],
            'PO Delivery Date':['PO Delivery Date'],
            'PO Date': ['PO Date'],
            'Note Raw': ['Note Raw'],
            'Detail Raw': ['Detail Raw'],
            'Motor Brand': ['Motor Brand'],
            'Motor Speed': ['Motor Speed'],
            'Motor Voltage': ['Motor Voltage'],
            'Motor Class': ['Motor Class'],

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
        for k,v in entriesDict.items():
            self.addEntry((k,v))

    def parse_model_string(self, modelstring):
        modelstring = modelstring.replace('\n', ' ')
        fields = {}
        match = re.match(r'^(BIF|AND)(-Ex|-GVD|-CR)? (([0-9]+)\/([0-9-]+\/.+)|(.+))$', modelstring)
        match2 = re.match(r'^(RS|RSM) ([0-9]+)(-\d[dD].*)?', modelstring)
        match3 = re.match(r'^(Matching Flanges|Mounting Feet) ([0-9]+)mm.*$', modelstring)
        match4 = re.match(r'^(DKHRC|DKHR|EKHR) ([0-9]+)(-.+?) ?(\(LG 0\))?$', modelstring)
        match5 = re.match(r'^(Guide Vane) \d+ \(([0-9.]+)mm.*\).*?(\d+)mmL', modelstring)
        # print(modelstring)
        item = size = impeller = silencer_size = fan_direction = casing_length = None
        if match:
            item, size, impeller = \
                    match.group(1), match.group(4), match.group(5)
            
            extra = match.group(2)
            if item == 'AND':
                item = 'Ax'
            elif item == 'BIF':
                item = 'Bif'

        elif match2:
            item = match2.group(1)
            size = match2.group(2) + '0'
            if match2.group(3):
                silencer_size = match2.group(3)

        elif match3:
            gr1 = match3.group(1)
            if gr1 == "Matching Flanges":
                item = 'MFlanges'
            elif gr1 == "Mounting Feet":
                item = 'MFeet'
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
            casing_length = match5.group(3)

        if not (match or match2 or match3 or match4 or match5):
            print("Model string doesn't match any known configuration: ", modelstring)
            return None

        fields['Item'] = item
        fields['Size'] = size
        fields['Impeller'] = impeller
        fields['Silencer Size'] = silencer_size
        fields['Fan Direction'] = fan_direction
        fields['Casing Length (Special)'] = casing_length
        return fields
            

    def convert(self, key):
        """returns a dictionary with the output (airtable-correct) key, and
        the output data. Output data is simply the value in the key:value pair,
        unless processing is necessary"""
        output_data = {}
        if key == '_model':
            model_string = self.input_dict['_model'].replace('\n', '')
            output_data['Item Raw'] = model_string
            try:
                for k, v in self.parse_model_string(model_string).items():
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
            
        else:
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
        remote_table.create(self.output_dict)

    def print_output_dict(self):
        output_dict_printstring = ''
        for k, v in self.output_dict.items():
            output_dict_printstring += ' ' + str(k) + ' : ' +  str(v) +  '   |   '
        print(output_dict_printstring)
