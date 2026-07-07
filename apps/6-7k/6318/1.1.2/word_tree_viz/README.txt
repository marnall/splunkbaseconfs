Word Tree Viz
Daniel Spavin <daniel@spavin.net>

Version Support
9.2, 9.1, 9.0, 8.2, 8.1, 8.0, 7.3, 7.2, 7.1, 7.0

Who is this app for?
This app is for dashboard designers who want to explore common themes in a given text.

How does the app work?
This app provides a visualization that you can use in your own apps and dashboards.

To use it in your dashboards, simply install the app, and create a search that provides the text you want to display.



Usecases for the Word Tree Visualization:
 * Exploring common themes in App rating comments
 * Showing commonalities between ticket descriptions
 * Contrasting user reviews
 * Viewing trends in tweets related to your organisation


The following fields can be used in the search:
 * text (required, defaults to the first field): The text used for input, e.g. comments, descriptions, reviews.
 * focusword (optional, defaults to the second field): The word to place at the centre of the visualisation.
Options can be overwritten, so if type or color is set multiple times in the search results, the last value will be used.



Example Search
index=app_review source=appStore
| stats count by review_text
| rename review_text as text
| eval focusword="splunk"
| table text, focusword



Tokens
Tokens are generated each time you click an item. This can be useful if you want to populate another panel on the dashboard with a custom search, or link to a new dashboard with the tokens carying across.

Word : This is the value of the selected word. Default value: $wt_word$
Weighting : This is the weighting of the selected word. Default value: $wt_weight$


# Release Notes #
v 1.0.0
 * Initial version


Issues and Limitations
If you have a bug report or feature request, please contact daniel@spavin.net

Privacy and Legal
No personally identifiable information is logged or obtained in any way through this visualizaton.

For support
Send email to daniel@spavin.net

Support is not guaranteed and will be provided on a best effort basis.


3rd Party Libraries
 * Google Word Trees