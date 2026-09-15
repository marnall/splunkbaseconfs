# Splunk PSTree Nodaliser

This app is a fork of [splunk_pstree_app](https://github.com/murchisd/splunk_pstree_app) that
reconstructs a process tree from Sysmon-style parent/child events, but instead of rendering an
indented ASCII-art tree into a single multivalue `tree` field, it "nodalises" the result: one row
is emitted **per parent/child edge**, annotated with the node's depth and its full ancestor
lineage. That shape drops straight into node/link visualisations — force-directed graphs,
dendrograms, Sankey diagrams — without any reshaping in SPL.

By ingesting Sysmon events in Splunk and using this command you can quickly reconstruct process
lineage (similar to memory-forensics tools like Volatility's pstree) and visualise it as a graph
instead of a text block.

## Prerequisites

* Ingest Process Creation Events with Parent Process information in Splunk

## Installation

There are several ways to implement the command:
* Install from file - package this directory as a `.tgz`/`.spl` and use Splunk's "Install App from File"
* Copy `splunk_pstree_nodaliser_app` directory to `$SPLUNK_HOME/etc/apps`, then restart splunkd

## Usage

The `pstree_node` command requires two arguments, `child` and `parent`. It's intended for Sysmon
`EventCode=1` events but can be used for anything. (Named `pstree_node` rather than `pstree` to
avoid clashing with the unrelated `pstree` command shipped by other Splunkbase apps.)

**Note:** Fields passed as arguments to the `pstree_node` command must be referenced before calling
`pstree_node`. The simplest way to ensure this is to include `| fields *` prior to piping to `pstree_node`.

### Output fields

For every root process (a parent that never itself appears as a child), the command walks the
tree and yields one row per node, in preorder, with these fields:

| field          | description                                                                 |
|----------------|------------------------------------------------------------------------------|
| `root`         | the root value of the tree this node belongs to                              |
| `parent`       | the immediate parent of this node (empty for the root row itself)            |
| `child`        | this node's value                                                            |
| `depth`        | distance from the root (root = 0)                                            |
| `lineage`      | multivalue field: the ordered chain of ancestors from `root` down to `child` |
| `lineage_path` | the same chain joined into a single string with `" -> "`                     |
| `detail`       | value of the `detail` field for this node, if `detail=` was supplied         |

`parent`/`child` on each row are already a ready-made edge list; `child`/`parent`/`lineage` on
each row are already a ready-made adjacency list for building a hierarchy (e.g.
`d3.stratify().id(d => d.child).parentId(d => d.parent)`).

The `pstree_node` command uses an iterative algorithm to create the process tree. The legacy recursive
algorithm can be used by specifying `method="r"`.

### Simple Sysmon usage

```
index=sysmon EventCode=1 host=victim_machine
| fields *
| pstree_node child=Image parent=ParentImage
| table root parent child depth lineage_path
```

### Pretty Sysmon usage (with command-line detail)

```
index=sysmon EventCode=1 host=victim_machine
| rex field=ParentImage "\x5c(?<ParentName>[^\x5c]+)$"
| rex field=Image "\x5c(?<ProcessName>[^\x5c]+)$"
| eval parent = ParentName." (".ParentProcessId.")"
| eval child = ProcessName." (".ProcessId.")"
| eval detail=strftime(_time,"%Y-%m-%d %H:%M:%S")." ".CommandLine
| pstree_node child=child parent=parent detail=detail
| table root parent child depth lineage_path detail
```

### Feeding a force-directed graph

Each row is already an edge (`parent` -> `child`); just rename to whatever your viz expects
(e.g. Splunk's Force Directed custom visualization looks for `source`/`target`):

```
index=sysmon EventCode=1 host=victim_machine
| fields *
| pstree_node child=Image parent=ParentImage
| where parent!=""
| rename parent AS source, child AS target
| table source target root depth
```

### Feeding a dendrogram

Use `child` as the node id and `parent` as its parent id (adjacency list, e.g. for
`d3.stratify().id(d => d.child).parentId(d => d.parent)`), or use `lineage`/`lineage_path` directly
as a hierarchical path:

```
index=sysmon EventCode=1 host=victim_machine
| fields *
| pstree_node child=Image parent=ParentImage
| table root child parent depth lineage lineage_path
```

### Searching for a tree containing a specific process

```
index=sysmon EventCode=1 host=victim_machine
| fields *
| pstree_node child=Image parent=ParentImage
| search lineage_path=*<process name>*
| table root parent child depth lineage_path
```

### Use legacy recursive method

```
index=sysmon EventCode=1 host=victim_machine
| fields *
| pstree_node child=Image parent=ParentImage method="r"
| table root parent child depth lineage_path
```

To report problems with the original tree-based app, please go to the issues section on Github

https://github.com/murchisd/splunk_pstree_app/issues

Originally built by Donald Murchison; nodalised fork for node/link visualisation output.
