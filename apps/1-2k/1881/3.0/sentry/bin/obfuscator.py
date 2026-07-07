
import string, random, re

replacementMapping = {}

def rand_generator(origText, minLength=1, replaceDict=None, replaceList=None):
    global replacementMapping

    newString = []
    
    for word in origText.split():
        if word in replacementMapping:
            newString.append(replacementMapping[word])
        elif replaceDict and word in replaceDict:
            replacementMapping[word] = replaceDict[word]
            newString.append(replaceDict[word])
        elif replaceList:
            newWord = random.choice(replaceList)
            replacementMapping[word] = newWord
            newString.append(newWord)
        elif len(word) >= minLength:
            chars = ''
            for charClass in [string.ascii_uppercase, string.ascii_lowercase, string.digits, string.punctuation]:
                if re.search('[' + charClass + ']', word):
                    chars += charClass
                    
            newWord = ''.join(random.choice(chars) for _ in range(len(word)))
            replacementMapping[word] = newWord
            newString.append(newWord)
            
    return ' '.join(newString)
    
    
