import splunk.Intersplunk as si

def toBinary(stringNumber):
    return format(int(stringNumber), "b")

def binaryStrToIntStr(stringNum):
    return str(int(stringNum, 2))
    
def shiftLeft(stringNumber, numToShift):
    return int(stringNumber) << numToShift

def shiftRight(stringNumber, numToShift):
    return int(stringNumber) >> numToShift

def AND(first, second):
    return int(first) & int(second)
    
def OR(first, second):
    return int(first) | int(second)
    
def XOR(first, second):
    return int(first) ^ int(second)

if __name__ == '__main__':
    keywords,options = si.getKeywordsAndOptions()
    
    validOperations = ['toBinary', 'bit-shift-left', 'bit-shift-right', 'AND', 'OR', 'XOR']
    
    #options for all operations
    operation    = options.get('operation', None)
    field        = options.get('field', None)
    output_field = options.get('output_field', None)
    overwrite    = options.get('overwrite', False)
    
    #options for bit-shift-left and bit-shift-right
    numToShift   = options.get('numToShift', None)
    #options for AND, OR, XOR
    secondField  = options.get('secondField', None)
    
    if overwrite == 'False':
        overwrite = False
    elif overwrite == 'True':
        overwrite = True
        
    #Validate input options
    if operation is None:
        si.parseError("Please specify a valid operation from %s" % validOperations)
    elif operation not in validOperations:
        si.parseError("Please specify a valid operation from %s" % validOperations)
    elif field is None:
        si.parseError("Field to operate on not specified with field=<field name>")
    elif output_field is None:
        si.parseError("Name of field to output the new resulting field not specified with output_field=<field name>")
    
    #Validate bit-shift options
    if (operation == 'bit-shift-left') or (operation == 'bit-shift-right'):
        if numToShift is None:
            si.parseError("Please specify a number of bits to shift using numToShift=<number>")
        numToShift = int(numToShift)
    
    #Validate AND,OR,XOR options
    elif (operation == 'AND') or (operation == 'OR') or (operation == 'XOR'):
        if secondField is None:
            si.parseError("Please specify another field to operate with using secondField=<field name>")    

    results = si.readResults(None, None, True)

    for res in results:
        #if user says not overwrite a field to output the converted field, verify that field name does not already exist
        if overwrite == False:
            if output_field in res and res[output_field] != '':
                si.parseError("Output field name %s already exists in results. Change the output_field name or use overwrite=True to use this field" % output_field)

        #Verify field is in the result before performing any operations
        if field not in res:
            continue
            
        if operation == 'toBinary':
            res[output_field] = toBinary(res[field])
            
        elif operation == 'bit-shift-left':
            res[output_field] = shiftLeft(res[field], numToShift)
            
        elif operation == 'bit-shift-right':
            res[output_field] = shiftRight(res[field], numToShift)
        
        elif ((operation == 'AND') or (operation == 'OR') or (operation == 'XOR')):
            if secondField not in res:
                continue
                
            if operation == 'AND':
                res[output_field] = AND(res[field], res[secondField])
                
            elif operation == 'OR':
                res[output_field] = OR(res[field], res[secondField])
                
            elif operation == 'XOR':
                res[output_field] = XOR(res[field], res[secondField])
        
    si.outputResults(results)
