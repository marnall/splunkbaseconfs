# How to Run Commands - Quick Reference

**TL;DR: Always `cd` to `bin/` first, then use `python -m` (no `.py`!)**

---

## The Two Methods

### Method 1: `python -m` (Standard Python)

```bash
# Step 1: cd to bin/
cd src/main/resources/splunk/bin

# Step 2: Run with python -m (use dots, no .py!)
python -m core.similarity.calculator 'your query' -m tfidf_enhanced -n 10
python -m cli.dump_records --output data.jsonl
python -m cli.explain 'query1' 'query2'
python -m examples.demo_tfidf_corpus
```

### Method 2: Wrapper Scripts (Works from anywhere!)

```bash
# From repo root - use full path
python src/main/resources/splunk/bin/similarity_calc.py 'query' -m tfidf_enhanced
python src/main/resources/splunk/bin/dump_records.py --output data.jsonl

# From bin/ - short path
cd src/main/resources/splunk/bin
python similarity_calc.py 'query' -m tfidf_enhanced
python dump_records.py --output data.jsonl
```

---

## Common Commands

```bash
cd src/main/resources/splunk/bin

# Find similar searches
python -m core.similarity.calculator 'search error' -m tfidf_enhanced -n 10

# Export all search records
python -m cli.dump_records --output all_searches.jsonl

# Explain similarity between two queries
python -m cli.explain 'query1' 'query2'

# Run TF-IDF demo
python -m examples.demo_tfidf_corpus

# Run tests
python -m pytest tests/ -v
```

---

## ❌ Common Mistakes

```bash
# ❌ WRONG: Using file path with python -m
python -m src/main/resources/splunk/bin/core/similarity/calculator.py

# ❌ WRONG: Using slashes instead of dots
python -m core/similarity/calculator

# ❌ WRONG: Including .py extension
python -m core.similarity.calculator.py

# ❌ WRONG: Not in bin/ directory
cd packages/searchbase/
python -m core.similarity.calculator  # ModuleNotFoundError!

# ✅ CORRECT: cd to bin/, use module name with dots, no .py
cd src/main/resources/splunk/bin
python -m core.similarity.calculator
```

---

## Need More Help?

- **Detailed Guide:** [docs/RUNNING_CODE.md](docs/RUNNING_CODE.md)
- **Common Mistakes:** [docs/COMMON_MISTAKES.md](docs/COMMON_MISTAKES.md)
- **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Refactoring Summary:** [docs/FINAL_REFACTORING.md](docs/FINAL_REFACTORING.md)

---

**Remember:** `cd` to `bin/`, use `python -m`, use dots not slashes, no `.py` extension! 🎯

