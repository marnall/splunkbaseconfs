#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.  
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software 
# contains proprietary trade and business secrets.            
#
import sys
import saUtils
import platform,time
import splunk.Intersplunk as si

if __name__ == '__main__':

    argList = []
    addSemicolon = 0
    addScope = 0
    addContainer = 0
    addClass = 0
    classString = ''
    app = ''
    containerString = ''
    contextName = ''
    contextString = ''
    scopeString = ''
    setSeparator = ";"
    setString = ''
    synonyms = 'synonyms'

    appKeyword = ''
    byKeyword = ''
    fromKeyword = ''
    inKeyword = ''
    scopedKeyword = ''
    usingKeyword = ''
    try:
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower() == "from":
                    fromKeyword = "from"
                elif arg.lower() == "in":
                    inKeyword = "in"
                elif arg.lower() == "by":
                    byKeyword = "by"
                elif arg.lower() == "scoped":
                    scopedKeyword = "scoped"
                elif arg.lower() == "app":
                    appKeyword = "app"
                elif arg.lower() == "using":
                    usingKeyword = "using"
                else:
                    if arg.endswith(setSeparator) and arg != setSeparator:
                        comma = arg.find(setSeparator)
                        arg = arg[0:comma]
                        addSemicolon = 1
                    if fromKeyword == "from":
                        contextName = arg
                        contextString = contextString + arg
                        fromKeyword = ''
                        addScope = 1
                        addContainer = 1
                        addClass = 1
                    elif scopedKeyword == "scoped":
                        scopeString = scopeString + arg
                        scopedKeyword = ''
                        addScope = 0
                    elif appKeyword == "app":
                        app = arg
                        appKeyword = ''
                    elif inKeyword == "in":
                        containerString = containerString + arg
                        inKeyword = ''
                        addContainer = 0
                    elif byKeyword == "by":
                        classString = classString + arg
                        byKeyword = ''
                        addClass = 0
                    elif usingKeyword == "using":
                        synonyms = arg
                        usingKeyword = ''
                    elif arg != setSeparator:
                        if setString == '':
                            setString = arg
                        else:
                            if setString[len(setString)-1:len(setString)] == ';':
                                setString = setString + arg
                            else:
                                setString = setString + "," + arg
                    else:
                        addSemicolon = 1
                        x = "YES"
                    if addSemicolon == 1:
                        contextString = contextString + ";"
                        setString = setString + ";"                     

                        if addContainer == 1:
                            containerString = containerString + contextName 
                            addContainer = 0
                        containerString = containerString + ";"

                        if addClass == 1:
                            classString = classString + ""
                            addClass = 0
                        classString = classString + ";"

                        if addScope == 1:
                            scopeString = scopeString + "none"
                            addScope = 0
                        scopeString = scopeString + ";"

                        addSemicolon = 0


                    
        else:
            raise Exception("xsvDisplayConcept-F-001: Usage: xsvDisplayConcept [hedge]* concept FROM context [IN container] [BY class] [SCOPED scope] [APP app] [; [hedge]* concept FROM context [IN container] [BY class] [SCOPED scope] [APP app] ]* [USING synonyms]") 


        if addContainer == 1:
            containerString = containerString + contextName
        if addClass == 1:
            classString = classString + " "
        if addScope == 1:
            scopeString = scopeString + "none"

        argList.append("-c")
        argList.append(contextString)
        argList.append("-C")
        argList.append(containerString)
        argList.append("-l")
        argList.append(setString)
        argList.append("-p")
        argList.append(scopeString)
        argList.append("-a")
        argList.append(app)
        argList.append("-s")
        argList.append(synonyms)
        argList.append("-Y")
        argList.append(classString)

        saUtils.runProcess(sys.argv[0], "xsvDisplayConcept", argList, False)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)
