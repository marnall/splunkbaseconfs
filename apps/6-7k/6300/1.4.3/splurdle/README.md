PLEASE NOTE: This app uses a third party dictionary. The dictionary selects words from the dictionary at random and some of these words may be offensive to certain users. User discretion is advised.

* description * 

A random word is selected from a word list each time that the dashboard is loaded. You have a limited number of chances to correctly guesses the word:

Splurdle = 5
Splurdle 4 = 4
Splurdle 6 = 6
Splurdle 7 = 7
Splurdle 8 = 8
Splurdle 9 = 9
Splurdle =(Hard) 5


Each attempt must be a word that is in the word list. This means that you cannot try all vowels in one turn, you will be presented with an error message. You will also see an error message if you do not have the correct number of letters in your guess.

Hit the enter button to submit your guess.

After each attempt, the color of the tiles will change to show reveal information about your guess:

Green = It is the correct letter, in the correct position
Yellow = It is the correct letter, in the wrong position
Orange = (Hard) mode: It is the correct letter, no position information


The game was written in Splunk for entertainment purposes only. All of the code is there for you to play with and you are encouraged to make your own variant! This is also why I chose not to use Javascript or HTML based dashboards, just simple XML. This should make is easier to reuse.

For instance, this App can be used in quizzes as an entry method for the answer (see the dashboards under the Sample Quizes menu). Similar to using jumbled letters as the base for the correct answer that the student must decode to select the right answer.
 
* Setup *

None, just install it on any Search Head and go!
 
* Privacy *

No privacy concerns with thie App.  It uses a publically available word list from https://www.wordgamedictionary.com/word-lists/.

* Help *

While this app is not formally supported, the developer can be reached at jim@splunk.com. Responses are made on a best effort basis. Feedback is always welcome and appreciated!

* Troubleshooting *

This App should work with all versions of Splunk. However, using version="1.1" in XMl seems to have surfaced a bug in Splunk 8.2.2106. With 8.2.2106, the font sizes increase from 33 to 66 point font, making them unusable. To correct this either update to 8.2.6 or follow these steps to update the dashboards:

Edit the dashboard by adding "editxml" to the end of the base URL (http://localhost:8000/en-US/app/splurdle/splurdle/editxml)
In the first line of code, change version="1.1" to version="1.0"
Save your changes and empty out your browser cache
Refresh the dashboard
That should clear up the only issue reported with this App.
