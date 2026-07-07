Author: Kyle Smith (splunkapps at kyleasmith dot info)
Copyright (c) 2012 Kyle Smith
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, but NOT sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Some modifications were made to the Google Apps Manager Libraries to properly get the API working, and to call the next url in a results series. 
Original code copyright by these guys: http://code.google.com/p/google-apps-manager/

Greetings! This App is designed for use with a single or multiple Google Apps Domain(s). 
In order for this to work, you must use a Super Admin account for your domain to authorize the API Calls.

***********************************You MUST RUN run_first.py BEFORE YOU ENABLE THE APP**************************

****AUDIT API
Reporting from the Audit API
These are the valid report keys: report:all, report:login, report:docs, report:drive, report:token, report:calendar, report:admin

****GENERAL
If your Modular Input is not working correctly, you can run a search that might help you figure out the issue. 

"index=_internal sourcetype=splunkd googleapps" will give you the logging outputs for this App.

If you have any questions/problems/concerns/fixes, please drop me a line!
I work independently, but will address your concerns as I can. Thanks!

Email: splunkapps@kyleasmith.info
Text or Call: (315) 775-8650
