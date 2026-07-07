import os
import sys

'''
simple script used to parse the API documents and build out the lookup csv files

* please note the csv files are create in the current working directory
* you will need a copy of the API documents inorder to generate the csv files
'''

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if os.path.isdir(arg) == True:
            dirList = os.listdir(arg)
            for d in dirList:
                    fh = open(arg+'\\'+d,'r')
                    metrics = {}
                    header = None
                    while 1:
                        line = fh.readline()
                        if not line:
                            break
                        else:
                            if line.startswith("extrahop.device"):
                                header = line[line.rfind('.')+1:line.rfind(' ')]
                                metrics[header] = {}
                            elif line.startswith('  field '):
                                line = line.strip()
                                line = line.split(' ')
                                metrics[header][line[2]] = line[3]
                                
                    fh.close()
                    fh = open(d+"_lookup.csv",'w')
                    fh.write("device_type,device,metric,type\n")
                    lines = []
                    for k,v in metrics.iteritems():
                        for m,n in v.iteritems():
                            lines.append(d+','+k+','+m+','+n+'\n')
                    fh.writelines(lines)
                    fh.close()
                                
            with open("metrics_lookup.csv",'w') as fh:
                fh.write("metric\n")
                for d in dirList:
                    fh.write(d+'\n')



if __name__ == '__main__':
    if len(sys.argv) == 2:
        main()
        sys.exit(0)
    else:
        print "\n%s usage:"%sys.argv[0]
        print "\n\tpython "+sys.argv[0]+" <path/to/api/docs>\n"
        sys.exit(1)