import re

class PO:

    def __init__(self, ponumber):
        self.ponumber = ponumber
        self.items = []

    def addItem(self, poitem):
        self.items.append(poitem)

    def sync(self, remote_table):
        print("test")
        # pass




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

    # def __getattr__(self, name):
        # if name in self:
            # return self[name]
        # else:
            # raise AttributeError("No such attribute: " + name)

    # def __setattr__(self, name, value):
        # self[name] = value

    # def __delattr__(self, name):
        # if name in self:
            # del self[name]
        # else:
            # raise AttributeError("No such attribute: " + name)

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
        match = re.match(r'^(BIF|RSM|AND)(-Ex)? (([0-9]+)\/([0-9-]+\/.+)|(.+))$', modelstring)
        # print(match)
        try: 
            print("group4:", match.group(4))
            item, size, impeller = \
                    match.group(1), match.group(4), match.group(5)
            if item == 'AND':
                item = 'Ax'
            elif item == 'BIF':
                item = 'Bif'
            fields['Item'] = item
            fields['Size'] = size
            fields['Impeller'] = impeller
            return fields
        except AttributeError:
            print("Model string doesn't match any known configuration!")
            return None
        except IndexError:
            print("not enough matches, something is wrong.")
            return None
            

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
                # print("Cannot split model string into fields: no regex match")
            # try:
                # item, rest = model_string.split(' ', 1)
                # if item == 'AND' or item == 'AND-Ex':
                    # item = 'Ax'
                # elif item == 'BIF':
                    # item = 'Bif'
                # # output_data.append(('Item', item))
                # output_data['Item'] = item
                # size, impeller = rest.split('/', 1)
                # # output_data.append(('Size', size))
                # output_data['Size'] = size
                # # output_data.append(('Impeller', impeller))
                # output_data['Impeller'] = impeller
            # except ValueError:
                # print('model string not parseable')

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
            # output_data.append(('Motor Size', motor_number))
            if motor_number == '4':
                motor_number = '4.0'
            output_data['Motor Size'] = motor_number
        elif key == 'Qty':
            qty = self.input_dict['Qty']
            qty = int(qty)
            # output_data.append(('Qty', qty))
            output_data['Qty'] = qty
        elif key == 'Price per Unit':
            ppu = self.input_dict['Price per Unit']
            ppu = float(ppu)
            # output_data.append(('Price per Unit', ppu))
            output_data['Price per Unit'] = ppu
            
        else:
            # output_datum = self.input_dict[key]
            # if output_datum == '':
                # output_datum = None
            output_data[key] = self.input_dict[key]

        # print(output_data)
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
        # for key,value in self.output_dict:
        print(self.output_dict)
        remote_table.create(self.output_dict)

        # pass
        


# testItem = POItem()
# print(testItem.model)
