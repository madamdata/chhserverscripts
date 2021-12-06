import re

class PO:

    def __init__(self):
        self.items = []
        self.ponumber = '-'
        self.project = '-'
        self.issuedate = None
        self.deliverydate = None
        self.note = None
        self.detail = None

    def addItem(self, poitem):
        self.items.append(poitem)

    def parseDetailString(self, detailstring):
        pass

    def sync(self, remote_table):
        print("test")

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

    def parse_model_string(self, modelstring):
        fields = {}
        match = re.match(r'^(BIF|AND)(-Ex|-GVD)? (([0-9]+)\/([0-9-]+\/.+)|(.+))$', modelstring)
        match2 = re.match(r'^(RS|RSM) ([0-9]+)(-1[dD])?', modelstring)
        match3 = re.match(r'^(Matching Flanges|Mounting Feet) ([0-9]+)mm$', modelstring)
        match4 = re.match(r'^(DKHRC|DKHR|EKHR) ([0-9]+)(-.+?) ?(\(LG 0\))?$', modelstring)
        # print(modelstring)
        item = size = impeller = silencer_size = fan_direction = None
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

        if not (match or match2 or match3 or match4):
            print("Model string doesn't match any known configuration: ", modelstring)
            return None

        fields['Item'] = item
        fields['Size'] = size
        fields['Impeller'] = impeller
        fields['Silencer Size'] = silencer_size
        fields['Fan Direction'] = fan_direction
        return fields
            

    def convert(self, key):
        """returns a dictionary with the output (airtable-correct) key, and
        the output data. Output data is simply the value in the key:value pair,
        unless processing is necessary"""
        output_data = {}
        if key == '_model':
            model_string = self.input_dict['_model']
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
