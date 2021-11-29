import re

class PO:

    def __init__(self, ponumber):
        self.ponumber = ponumber
        self.items = []

    def addItem(self, poitem):
        self.items.append(poitem)

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
            '_model':['MODEL','Model / Description'], 
            'T-box Position': ['T/BOX'], 
            'Motor Size': ['MOTOR'], 
            'Qty': ['QTY'], 
            'Price per Unit': ['S$U/P'], 
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
        print(modelstring)
        item = size = impeller = silencer_size = None
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
            try:
                silencer_size = match2.group(3)
            except IndexError:
                pass

        elif match3:
            gr1 = match3.group(1)
            if gr1 == "Matching Flanges":
                item = 'MFlanges'
            elif gr1 == "Mounting Feet":
                item = 'MFeet'
            size = match3.group(2)

        if not (match or match2 or match3):
            print("Model string doesn't match any known configuration: ", modelstring)
            return None

        fields['Item'] = item
        fields['Size'] = size
        fields['Impeller'] = impeller
        fields['Silencer Size'] = silencer_size
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
                    print("Price per unit doesn't seem to be a number.")

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
