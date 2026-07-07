# Rest handler to generate confs

## Overview

    This app sits on deployment servers, receives payload from the SH app <app-name here>.
  
    The python program decodes the payload and generates inputs.conf and serverclass.conf
  
    Checks for existing app/conf files and adds only new updates. Duplicates are ignored.

## To do
1. Create another handler to send phoning phone list to SH/ or log them and read from the dashboard app.
2. Keep track of updated serverclass, reload them at an interval.


To modify the below 

# to do 
create ability to delete source/app probably in a new endpoint
create ability to update source/app probably in a new endpoint

validate :
app name - can't have space 
any fields can't have space
