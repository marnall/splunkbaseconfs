# Introduction

This Splunk app allows users to simply create all sorts of graphs using the Graphviz library.

It adds a new type of visualization called Graphviz that interprets Splunk result set into a graph using a specific but simple syntax.

# Installation

From the SA-Graphviz.spl archive :
- Click on the Apps dropdown > Manage app > Install app from file and find the SA-Graphviz.spl archive.

From the repo :
- Simply copy the repo content under etc/apps in your Splunk home.


# Basic example

Once the add-on is installed, type this into your Splunk search bar :

        | makeresults | eval type="edge", origin="A", destination="B"

Then click on the visualization tab and choose the new Graphviz visualization and ... that's it, you drew your first graph!

To find more basic examples, launch the Graphviz app and click on the 'Step by step example'.

# Syntax

The Graphviz visualization requires a specific result set format.

For those who already know Graphviz, it should be quite straightforward as this syntax is as close as possible to dot language.
The biggest difference is that here, the graph is flatten into rows instead of being made of blocks between '{ }'.

## General

Basically, each row of the Splunk result set correspond to an element in the graph.
It can be a node, an edge, a subgraph or an attribute.

Only some specific field names are taken into account by the visualization, so you have to name the fields accordingly.
Note that the field names are case unsensitive and the other fields are just ignored.

Bellow is the list of all the field names currently taken into account. Note that some fields are available only for some types.

Field name | Signification | Notes 
---------|---------------|---
type	 | Type of the element | Valid types : graph, subgraph, cluster, node, edge and attr
subtype       | Subtype of the element | Usefull only for type graph or attr
id | Unique ID | An Id is any alphanumeric string not beginning with a digit, but possibly including underscores; or a number; or any quoted string possibly containing escaped quotes
attrlist | Used to specify attributes of the element like color, style, label, ... | list of key=value pairs.<br>Ex : <i>attrlist="style=filled,fillcolor=blue"</i><br>Complete list can be found here : https://www.graphviz.org/doc/info/attrs.html<br><br>If you are using a CSV lookup, use ';' instead of ','<br>If a key has several values and you are not using a lookup, escape the '"' like this :<br><i>attrlist="style=\\"dashed,filled\\",fillcolor=blue"</i>
parents | To put the element into subgraphs | List of subgraphs/clusters Ids separated by ','
rank | To force the position of the element vertically | The rank value can be anything. It is just a way to align all the elements with the same rank value. Exceptions : min and max which are dot special keywords.
position | To force the position of the element horizontally | By default, the order of the rows in the result set is preserved in the dot translation (from top to bottom), which means that Graphviz will draw the nodes in this order (from left to right), but you can use this field to change this behavior
origin | Starting node of an edge | If this node Id doesn't exist, Graphviz will automatically create it
destination | Ending node of an edge | If this node Id doesn't exist, Graphviz will automatically create it




The next chapters give a complete description of all the fields for each type.

## type=graph

Field    | Mandatory | Format  |  Default
---------|---------------|---|--
subtype	 | No | graph/digraph | digraph | graph for a non-oriented graph, digraph otherwise
id       | No | see § General | splunkGraphviz

Note : there can be only one graph in the whole result set and it is optional so it's only useful if you want to create a non-oriented graph.

## type=subgraph or type=cluster

Field    | Mandatory | Format  |  Default
---------|---------------|---|--
id	     | Yes | see § General | -
attrlist | No | see § General | -
Parent | No | List of subgraphs/clusters ids | -
Position | No | Integer | row number in the result set

### Difference between subgraph and cluster

In the dot syntax, subgraphs are not visible by default.
As is, they are useful to give some attributes to a group of elements.
But if you prefix them with "cluster_", then their borders become visible.

The type=cluster does just that : add a "cluster_" prefix to the subgraph name. It is just a shorter way to write the same graph.
Note that when you reference a cluster as parent of another object, you don't have to repeat the "cluster_" prefix with this method.


## type=node

Field    | Mandatory | Format  |  Default
---------|---------------|---|--
id	     | Yes | see § General | -
attrlist | No | see § General | -
parent | No | List of subgraphs/clusters ids | -
position | No | Integer | row number in the result set
rank | No | see § General | -

Note : you don't need to declare the nodes at the extremities of an edge.
It is only useful if you want to add some formatting to the nodes themselves.

## type=edge

Field    | Mandatory | Format  |  Default
---------|---------------|---|--
origin	 | Yes | node id | -
destination | Yes | node id | -
attrlist | No | see § General | -
parent | No | List of subgraphs/clusters ids | -
position | No | Integer | row number in the result set | -

## type=attr

This element allows to :
- define global options (no subtype) like <i>newrank=true</i> or <i>compound=false</i>
- add global formatting to all the specified elements below it (subtype : graph, node or edge)

Field    | Mandatory | Format  |  Default
---------|---------------|---|--
subtype	 | No | graph/node/edge/\<empty\> | -
attrlist | No | see § General | -
parent | No | List of subgraphs/clusters ids | -
position | No | Integer | row number in the result set


# How can I generate such a Splunk result set

You are free to use all the tools of Splunk language to generate your graphs, but but here are some methods to generate the Splunk result set needed for the visualization :
- use the <i>makeresult</i> command to create the graph from scratch. Luckily, you don't have to declare the graph itself or the extremities of the edges, so it can be quite simple.
Use the append command to add elements to the graph.

	Ex :

        | makeresults | eval Type="edge",Origin="A",Destination="B"
        | append [| makeresults | eval Type="edge",Origin="A",Destination="C"]
        | append [| makeresults | eval Type="edge",Origin="C",Destination="D"]

	
	You can find more examples of this in the 'Step by step example' or 'Randomly generated graphs' dashboards

- use one or more lookups if the graph is static : See the 'Dot manual examples' dashboards for an example of this method.

- Generate the graph on the fly based on some real-time data :

	Let's say for example that you have logs where each row contains a transmission between a sender and a receiver for a certain amount.
	
	You could easily graph those exchanges by formatting them into Graphviz like that :

        ... | table sender,receiver,amount
		| rename sender as origin, receiver as destination
		| eval type="edge", attrlist="label=".amount
	
- Use of a mix of the last two methods :

	Store the structure of the graph into some lookups and compute the status of the elements with real-time data.
	See the 'Execution graph' dashboard for an example of this.


# Shortcuts over the dot syntax

## Group attributes

In dot syntax, the attributes of a group are declared as elements inside the group and not in between '[ ]' like you would do with a node or an edge :

        ...
        subgraph cluster_A {
          label="group A";
		  ...
		}
		...

And not 

        ...
        subgraph cluster_A [label="group A"]
		{
		  ...
		}

Which is quite annoying sometimes...

Here, you can simply add an attrlist to the subgraph like for a node or an edge.

So in the end, both writings generate exactly the same graph in the dot language :

        | makeresults | eval Type="cluster",Id="C1",AttrList="label=Cluster1"
        | append [| makeresults | eval Type="edge", Origin="A",Destination="B",Parents="C1"]

		
        | makeresults | eval Type="cluster",Id="C1"
        | append [|makeresults | eval Type="attr",AttrList="label=Cluster1",Parents="C1"]
        | append [| makeresults | eval Type="edge", Origin="A",Destination="B",Parents="C1"]


## Ranking

To align nodes in the dot syntax, you need to put them into a subgraph with an attribute rank=same.
This can be quite long to write and can lead to some crashes that can be avoided if the ranking is done at the end of the graph.

For those reasons, the <i>rank</i> field has been added and will automatically create the corresponding subgraphs at the end of the graph so it is recommanded to use it.
 
For example, this SPL :
        
        | makeresults | eval Type="node",Id="A",Rank="R1"
        | append [| makeresults | eval Type="node",Id="B",Rank="R1"]
        | append [| makeresults | eval Type="edge",Origin="A",Destination="B"]

will produce the same visualization (but not the same graph in dot language) as this one :

        | makeresults | eval Type="subgraph",Id="rankingGroup"
        | append [|makeresults | eval Type="attr",AttrList="rank=same",Parents="rankingGroup"]
        | append [| makeresults | eval Type="node",Id="A",Parents="rankingGroup"]
        | append [| makeresults | eval Type="node",Id="B",Parents="rankingGroup"]
        | append [| makeresults | eval Type="edge",Origin="A",Destination="B"]

Note : the use of the <i>rank</i> field automatically adds the dot global option <i>newrank=true</i> for a better drawing of the graph.
	  

# Limitations

This add-on has some limitations over the dot syntax :
- edges can't be described in a chain like <i>A -> B -> C</i>. They have to be described one by one in separate rows.
- edges extremities can't be subgraphs, only nodes. That doesn't mean you can't draw edges on clusters (see 'dot manual examples' dashboard), but you can't declare a group of edges like you would do using the dot syntax : <i>A -> { B C }</i>
- a node can only be declared once. This shouldn't matter much, especially with the <i>rank</i> field, but there could be some weird cases where it limits the possibilities.


# ComputeAttrList macro

This Splunk macro makes writing the attribute lists of each element much easier.

You normally have to write the attribute list at once like that :

        ... | eval attrlist="attr1=value11,attr2=\"value21,value22\",..."

And it's quite annoying if for example you want to add another attribute later in your SPL.

But with this macro, you can instead declare each attribute separately and call the macro at the end to "compile" them.

To do that, you have to prefix the attribute field names by "Attr_" :

        ... | eval Attr_attr1=value1,Attr_attr2="value21,value22"
        ... | `computeAttrList`

Note : since this macro puts quotes (") around each attribute, you can't declare HTML-like labels with it (they are enclosed within < and > in dot syntax). Just use the normal syntax in that case.


# Tips on drawing big graphs

The Graphviz library can sometimes crash, especially when using a lot of clusters.

To avoid that, here are some recommendations :
- put all the edges outside of any cluster (i.e. don't give them any parent)
- put the ranking at the end in specific subgraphs, not in the subgraphes/clusters defining the nodes ==> use the Rank field instead of the dot syntax with an attribute 'rank=same'
- put every node in a cluster (add a default invisible cluster if needed)

If it still doesn't work, change the engine options :
- increase memory allowed (in bytes, power of 2 ; default of 8 Mo)
- use another engine


# Credits

Graphviz : http://www.graphviz.org/

d3-graphviz : https://github.com/magjac/d3-graphviz
