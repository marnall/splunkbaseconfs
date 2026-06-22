================================================================================
                    SPLUNKLINT - ADVANCED DASHBOARD TOOLKIT
                                  Version 2.0.1
================================================================================

Author: Mher Saratikyan
License: MIT
GitHub: https://github.com/sarat1kyan/splunklint

================================================================================
DESCRIPTION
================================================================================

SplunkLint is a comprehensive Dashboard Toolkit for Splunk that goes far beyond
basic validation. It provides eight powerful tools that Splunk doesn't offer
natively, helping you build better, faster, and more accessible dashboards.

================================================================================
FEATURES
================================================================================

1. VALIDATE XML
   - Syntax validation with line numbers
   - Structure validation for dashboard/form
   - Element validation (panels, searches, drilldowns)
   - Deprecation warnings for outdated elements
   - Security checks (hardcoded credentials detection)
   - Best practices recommendations

2. COMPLEXITY ANALYZER (NEW!)
   - Dashboard complexity scoring (A-F grade)
   - Metrics: panels, searches, tokens, drilldowns, base searches
   - Identifies performance bottlenecks
   - Optimization recommendations
   - Impact analysis for each issue

3. SPL OPTIMIZER (NEW!)
   - Performance scoring for queries (0-100)
   - Automatic rewrite suggestions
   - Detects: leading wildcards, missing indexes, expensive commands
   - Best practices tips (transaction, join, subsearch alternatives)
   - Copy optimized queries with one click

4. TOKEN FLOW ANALYZER (NEW!)
   - Visualizes all token definitions
   - Shows token dependencies per query
   - Detects orphan tokens (used but not defined)
   - Detects unused tokens (defined but never used)
   - Identifies missing default values

5. DASHBOARD CONVERTER (NEW!)
   - Convert Simple XML to Dashboard Studio JSON
   - Minify XML for production deployment
   - Ready-to-use Dashboard Studio format
   - Preserves searches, visualizations, and structure

6. DASHBOARD DIFF/COMPARE (NEW!)
   - Side-by-side comparison of two dashboards
   - Shows added panels, queries, and tokens
   - Shows removed elements
   - Statistics comparison

7. DOCUMENTATION GENERATOR (NEW!)
   - Auto-generate docs from dashboard XML
   - Multiple formats: Markdown, HTML, Confluence Wiki
   - Includes: overview, inputs table, panel descriptions
   - Copy to clipboard for easy sharing

8. ACCESSIBILITY CHECKER (NEW!)
   - WCAG 2.1 compliance checking
   - Identifies missing labels and titles
   - Color contrast warnings
   - Accessibility score (0-100%)
   - Links to remediation resources

================================================================================
INSTALLATION
================================================================================

1. Download the TA-splunklint folder
2. Copy to $SPLUNK_HOME/etc/apps/
   - Linux/macOS: /opt/splunk/etc/apps/
   - Windows: C:\Program Files\Splunk\etc\apps\
3. Restart Splunk or refresh:
   https://<splunk-server>:8089/debug/refresh
4. Open SplunkLint from the Apps menu

================================================================================
USAGE
================================================================================

1. Open SplunkLint from Splunk's app navigation
2. Paste your dashboard XML in the Validate tab
3. Use the tabs to access different tools:
   - Validate: XML validation and SPL analysis
   - Complexity: Dashboard complexity scoring
   - SPL Optimizer: Query performance tuning
   - Token Flow: Token dependency visualization
   - Convert: Dashboard Studio conversion
   - Compare: Diff two dashboard versions
   - Generate Docs: Auto-documentation
   - A11y Check: Accessibility audit

================================================================================
KEYBOARD SHORTCUTS
================================================================================

- Ctrl/Cmd + Enter: Validate XML

================================================================================
WHAT SPLUNKLINT DOES THAT SPLUNK DOESN'T
================================================================================

| Feature                  | Native Splunk | SplunkLint |
|--------------------------|---------------|------------|
| XML Syntax Validation    | Partial       | Full       |
| Security Checks          | No            | Yes        |
| SPL Performance Scoring  | No            | Yes        |
| Query Optimization Tips  | No            | Yes        |
| Dashboard Complexity     | No            | Yes        |
| Token Flow Analysis      | No            | Yes        |
| Dashboard Studio Convert | Manual        | Automatic  |
| Dashboard Diff           | No            | Yes        |
| Auto Documentation       | No            | Yes        |
| Accessibility Audit      | No            | Yes        |

================================================================================
COMPATIBILITY
================================================================================

- Splunk Enterprise 7.x, 8.x, 9.x
- Splunk Cloud
- Modern browsers: Chrome, Firefox, Edge, Safari

================================================================================
CHANGELOG
================================================================================

v2.0.1 (2026-01-21)
- Added Dashboard Complexity Analyzer with A-F grading
- Added SPL Query Optimizer with rewrite suggestions
- Added Token Flow Analyzer with dependency visualization
- Added Dashboard Studio JSON converter
- Added Dashboard Diff/Compare tool
- Added Documentation Generator (Markdown, HTML, Confluence)
- Added Accessibility Checker with WCAG compliance
- Enhanced validation with more security checks
- New tabbed interface for all tools
- Improved example dashboards

v1.0.0 (2026-01-21)
- Initial release as Splunk Add-on
- XML validation for Splunk dashboards
- SPL query analysis
- Export functionality (JSON, TXT, HTML)

================================================================================
SUPPORT
================================================================================

Issues: https://github.com/sarat1kyan/splunklint/issues
Docs:   https://github.com/sarat1kyan/splunklint

================================================================================
DISCLAIMER
================================================================================

This is a community-maintained, non-official tool.
It is not affiliated with or endorsed by Splunk Inc.

================================================================================
