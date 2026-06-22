# Canadian Cyber Centre Splunk App - Complete Documentation
## Version 3.1.0 with Advanced Deduplication System

**Author**: Alexandre Argeris  
**Version**: 3.1.0  
**Release Date**: December 18, 2025  
**Package**: cccs_alerts_app_v3.1.tar.gz

---

# Table of Contents

1. [Overview & Features](#overview--features)
2. [Quick Start](#quick-start)
3. [Installation Guide](#installation-guide)
4. [Configuration](#configuration)
5. [MITRE ATT&CK Integration](#mitre-attck-integration)
6. [Data Structure](#data-structure)
7. [Dashboard Guide](#dashboard-guide)
8. [Search Examples](#search-examples)
9. [MITRE Usage Guide](#mitre-usage-guide)
10. [Alert Configuration](#alert-configuration)
11. [Use Cases & Best Practices](#use-cases--best-practices)
12. [Troubleshooting](#troubleshooting)
13. [Technical Architecture](#technical-architecture)
14. [Upgrade Guide](#upgrade-guide)
15. [Support & Resources](#support--resources)

---

# Overview & Features

## What is This App?

This Splunk app collects alerts and advisories from the Canadian Centre for Cyber Security (CCCS) and provides comprehensive dashboards with **MITRE ATT&CK threat intelligence enrichment** for monitoring.

## 🆕 Version 3.1 - Advanced Deduplication System

This version introduces **dual-layer event deduplication** to eliminate duplicate alerts:
- **Feed-level hash validation** for quick detection of unchanged feeds
- **Event-level JSON hashing** to prevent duplicate events
- **Timestamp-based tracking** with 31-day retention window
- **Automatic cleanup** of old event hashes
- **Smart detection** even if CCCS republishes the same alerts

## Previous Major Release: Version 3.0 - MITRE ATT&CK Integration

Automated MITRE ATT&CK framework mapping for all CCCS alerts, providing:
- **Automatic technique detection** from 185+ MITRE techniques
- **Tactical classification** across 14 MITRE tactics
