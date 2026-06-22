# DAG Viewer Visualization for Splunk Enterprise

**Version:** 1.0.0  
**Author:** Christian Haugan

## Overview

The DAG Viewer is a custom Splunk visualization that renders Directed Acyclic Graphs (DAG) using GraphViz DOT format. It provides an interactive, zoomable visualization of graph structures, ideal for displaying attack trees, workflow diagrams, dependency graphs, and other hierarchical or network structures.

## Features

- **Interactive Graph Visualization**: Zoom and pan support for large graphs
- **Two Data Input Modes**:
  - **Raw DOT Mode**: Direct GraphViz DOT format strings
  - **Structured Mode**: Automatic graph generation from source/target/edge data
- **Compatible with Splunk 10.x**: Works in Classic Dashboards (SimpleXML)
- **React-based Rendering**: Built on d3-graphviz and graphviz-react for high-quality graph rendering

## Installation

### Prerequisites

- Splunk Enterprise 10.x (on-premises)
- Node.js and npm (for building the visualization, if not pre-built)

### Installation Methods

#### Method 1: Upload via Splunk UI (Recommended for distribution)

1. **Build the visualization first:**
   ```bash
   cd viz_dag_viewer/appserver/static/visualizations/dag_viewer
   npm install
   npm run build
   ```

2. **Create a zip file** (exclude `node_modules` folder):
   ```bash
   # From the parent directory of viz_dag_viewer
   zip -r viz_dag_viewer.zip viz_dag_viewer -x "*/node_modules/*" "*/.git/*" "*/package-lock.json"
   ```

3. **Upload via Splunk UI:**
   - Go to **Apps > Manage Apps**
   - Click **Install app from file**
   - Select `viz_dag_viewer.zip`
   - Click **Upload**
   - Restart Splunk if prompted

See `PACKAGING.md` for detailed packaging instructions.

#### Method 2: Manual Installation

1. **Copy the app to Splunk:**
   ```bash
   cp -r viz_dag_viewer $SPLUNK_HOME/etc/apps/
   ```

2. **Build the visualization:**
   ```bash
   cd $SPLUNK_HOME/etc/apps/viz_dag_viewer/appserver/static/visualizations/dag_viewer
   npm install
   npm run build
   ```

3. **Restart Splunk:**
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

#### Method 3: Using Installation Script

Alternatively, use the provided installation script:
```bash
./install.sh
```

## Usage

### Data Format Requirements

The visualization supports two data input modes:

#### Mode 1: Raw DOT Format (Recommended for Complex Graphs)

Return a single field named `dot` containing the complete GraphViz DOT format string.

**Example SPL:**
```spl
| makeresults count=1
| eval dot="digraph {
    rankdir=\"TB\";
    node [shape=\"box\" style=\"filled\"];
    
    A [label=\"Start\" fillcolor=\"#2B303A\" fontcolor=\"white\"];
    B [label=\"Node 1\" fillcolor=\"#ED96AC\"];
    C [label=\"Node 2\" fillcolor=\"#ED96AC\"];
    D [label=\"End\" fillcolor=\"#DB2955\" fontcolor=\"white\"];
    
    A -> B;
    A -> C;
    B -> D;
    C -> D;
}"
```

#### Mode 2: Structured Edge Data (Easier for Dynamic Data)

Return fields:
- `source` (required): Source node ID
- `target` (required): Target node ID
- `label` (optional): Edge label text
- `node_label` (optional): Node label text (applied to both source and target)

**Example SPL:**
```spl
| makeresults count=5
| eval source=case(
    _serial=1, "A",
    _serial=2, "A",
    _serial=3, "B",
    _serial=4, "C",
    1=1, "B"
)
| eval target=case(
    _serial=1, "B",
    _serial=2, "C",
    _serial=3, "D",
    _serial=4, "D",
    1=1, "D"
)
| eval label=case(
    _serial=1, "Step 1",
    _serial=2, "Step 2",
    _serial=3, "Path B",
    _serial=4, "Path C",
    1=1, "Final"
)
| fields source target label
```

The visualization automatically detects which mode you're using:
- If a `dot` field exists, it uses Raw DOT mode
- Otherwise, it uses Structured mode (requires `source` and `target` fields)

### Using in Classic Dashboards (SimpleXML)

Add a visualization panel with the type `viz_dag_viewer.dag_viewer`:

```xml
<panel>
    <title>My DAG Visualization</title>
    <viz type="viz_dag_viewer.dag_viewer">
        <search>
            <query>
                <!-- Your SPL query here -->
                | makeresults count=1
                | eval dot="digraph { A -> B; }"
            </query>
        </search>
    </viz>
</panel>
```

See `examples/classic_example.xml` for a complete example.

## GraphViz DOT Format Reference

The visualization uses GraphViz DOT format. Key elements:

- **Graph declaration**: `digraph { ... }` (for directed graphs)
- **Nodes**: `node_id [label="Node Label" fillcolor="#color"]`
- **Edges**: `source -> target [label="Edge Label"]`
- **Graph attributes**: `rankdir="TB"` (top-to-bottom), `rankdir="LR"` (left-to-right)
- **Node attributes**: `shape`, `fillcolor`, `fontcolor`, `style`
- **Edge attributes**: `label`, `color`, `style`

For complete DOT syntax documentation, see: https://graphviz.org/doc/info/lang.html

## Formatting Options

Currently, the visualization does not expose formatting options through the Splunk UI. All graph styling must be specified in the DOT format string itself.

## Troubleshooting

### Visualization Not Appearing

1. **Check installation**: Ensure the app is in `$SPLUNK_HOME/etc/apps/viz_dag_viewer/`
2. **Verify build**: Ensure `visualization.js` exists in `appserver/static/visualizations/dag_viewer/`
3. **Check permissions**: Verify `metadata/default.meta` allows visualization export
4. **Restart Splunk**: After installation, restart Splunk

### Graph Not Rendering

1. **Check data format**: Ensure your search returns either:
   - A `dot` field with valid DOT syntax, OR
   - `source` and `target` fields for structured mode
2. **Validate DOT syntax**: Test your DOT string in an online GraphViz viewer
3. **Check browser console**: Look for JavaScript errors in the browser developer console

### GraphViz WASM Issues

The visualization uses WebAssembly (WASM) for GraphViz rendering. If you encounter issues:

1. **Browser compatibility**: Ensure you're using a modern browser (Chrome, Firefox, Edge, Safari)
2. **WASM support**: Verify your browser supports WebAssembly
3. **Network issues**: Ensure WASM files can load (check network tab in browser dev tools)

### React Compatibility

The visualization uses React 16.10.2. If you encounter React-related errors:

1. **Check for conflicts**: Ensure no other visualizations are loading conflicting React versions
2. **Clear browser cache**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R) to reload JavaScript

### Performance Issues

For large graphs (1000+ nodes):

1. **Simplify the graph**: Reduce the number of nodes/edges in your DOT string
2. **Use structured mode**: More efficient than raw DOT for very large datasets
3. **Limit search results**: Use `head` or `limit` in your SPL to reduce data volume

## Development

### Building from Source

```bash
cd appserver/static/visualizations/dag_viewer
npm install
npm run build
```

### Development Build (with source maps)

```bash
npm run devbuild
```

### Watch Mode (for development)

```bash
npm run watch
```

### Project Structure

```
viz_dag_viewer/
├── default/
│   ├── app.conf                 # App configuration
│   └── visualizations.conf      # Visualization registration
├── metadata/
│   └── default.meta             # Permissions and exports
├── appserver/
│   └── static/
│       └── visualizations/
│           └── dag_viewer/
│               ├── src/
│               │   ├── visualization_source.js  # Splunk wrapper
│               │   ├── DAGViewerAdapter.js      # React adapter
│               │   └── DAGViewer.js             # GraphViz component
│               ├── visualization.js             # Built bundle (generated)
│               ├── visualization.css            # Styles
│               ├── package.json                 # Dependencies
│               └── webpack.config.js            # Build config
└── examples/
    ├── classic_example.xml      # SimpleXML example
```

## Limitations

- Maximum recommended graph size: ~500 nodes for optimal performance
- GraphViz WASM rendering may be slower than native for very large graphs
- Formatting options are currently limited to DOT syntax (no UI controls)
- Requires modern browser with WebAssembly support

## Support

For issues, questions, or contributions, please contact the author or refer to the Splunk custom visualization documentation:

- Splunk Custom Visualization Guide: https://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/CustomVizDevOverview

## License

MIT License - See LICENSE file for details.

## Credits

- Built with React, d3-graphviz, and graphviz-react
- Based on Splunk Visualization Template
- GraphViz DOT format: https://graphviz.org/
