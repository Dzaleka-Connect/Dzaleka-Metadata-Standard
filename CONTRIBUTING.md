# Contributing to the Dzaleka Metadata Standard

Thank you for your interest in contributing to DMS! This project is built by and for the Dzaleka community, and your help makes a real difference.

## Ways to Contribute

### 📝 Add Heritage Records
- Create metadata records for Dzaleka heritage items
- Share stories, photographs, or event documentation
- Always obtain consent from people featured in records

### 🌐 Translate Documentation
- Translate docs into Swahili, French, Kinyarwanda, or other community languages
- Help make the tools accessible to non-English speakers

### 🔧 Improve the Tools
- Fix bugs or add features to the Python CLI
- Improve validation error messages
- Add new import/export formats

### 📖 Write Documentation
- Create guides for specific use cases
- Improve existing documentation
- Add examples for different heritage item types

### 🐛 Report Issues
- Report bugs through GitHub Issues
- Suggest improvements to the schema
- Share your experience using DMS

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Dzaleka-Connect/Dzaleka-Metadata-Standard.git
cd dzaleka-metadata-standard

# Install in development mode with test dependencies
pip install -e ".[dev]"

# Run the test suite
pytest tests/ -v

# Validate all examples
dms validate --dir examples/
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your changes: `git checkout -b my-feature`
3. **Make your changes** and add tests if applicable
4. **Run the tests**: `pytest tests/ -v`
5. **Validate examples**: `dms validate --dir examples/`
6. **Submit a pull request** with a clear description of your changes

## Code Style

- Python code follows PEP 8 conventions
- Use type hints where practical
- Add docstrings to functions and classes
- Keep functions focused and readable

## Schema Changes

Changes to the DMS schema (`schema/dms.json`) require extra care:

1. Discuss the change in a GitHub Issue first
2. Ensure backward compatibility when possible
3. Update the YAML and JSON-LD files to match
4. Update the Field Guide documentation
5. Update or add example records
6. Add test cases for the new fields

## Community Guidelines

- Be respectful and inclusive
- Value diverse perspectives and experiences
- Handle community heritage with care and sensitivity
- Give credit where credit is due
- Protect privacy and obtain consent

## Questions?

Open a GitHub Issue or reach out to the Dzaleka Digital Heritage Project team.

---

*Thank you for helping preserve and share Dzaleka's digital heritage!*
