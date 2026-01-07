# Rejsekort Receipt Parser Documentation

## Overview

The Rejsekort Receipt Parser is a Python script that extracts travel information from Rejsekort PDF receipts and exports the data to CSV format for easy analysis.

## Features

- ✅ Extracts journey details (date, time, route, price)
- ✅ Parses traveller information (name and type)
- ✅ Handles multiple travelers per journey
- ✅ Processes multiple PDF files in batch
- ✅ Exports to CSV with European formatting (semicolon delimiter, comma decimal separator)
- ✅ Supports both single and multi-journey receipts
- ✅ Automatic date parsing in multiple formats
- ✅ Clean handling of non-breaking spaces from PDFs

## Background Information

The "Rejsekort" is a way to pay for public transportation in Denmark. Children under 18 can get their own app, but the payment is handled by the parents app. It is also possible to add additional travellers on a journey.

Rejsekortet has a website rejsekort.dk and a smartphone app. I created this script, because I wanted to get an overview of travels in our household, but I could not find anywhere to download the information. The script uses the PDF receipts, which rejsekort.dk will send to an email address.

The code is developed using Claude Code (using Sonnet 4.5), which proved to be very good at writing Python, but still needed multiple rounds of guidance and debugging before it worked correctly (the first checkin to github is version 27 of the code created by Claude).

## Requirements

### Python Version
- Python 3.6 or higher (tested with 3.6+)

### Dependencies
- **PyPDF2** - PDF text extraction
- **argparse** - Command-line argument parsing (included in Python standard library)

### Installation

Install the required dependency:

```bash
pip install PyPDF2
```

Note: `argparse` is part of Python's standard library since Python 3.2 and does not need separate installation.

## Usage

### Basic Usage

Place all your Rejsekort PDF files in the same directory as the script and run:

```bash
python rejsekort_parser.py
```

The script will automatically find and process all files matching the pattern `REJSEKORT_*.pdf`.

### Specify Files

You can also specify which files to process:

```bash
python rejsekort_parser.py REJSEKORT_2026-01-02_abc123.pdf REJSEKORT_2026-01-04_xyz789.pdf
```

### Verbose Mode

For troubleshooting or to see detailed processing information, use the `--verbose` or `-v` flag:

```bash
python rejsekort_parser.py --verbose
python rejsekort_parser.py -v
python rejsekort_parser.py -v REJSEKORT_2026-01-02_abc123.pdf
```

Verbose mode shows:
- Number of price entries found
- Number of journey patterns matched for each price
- Location of "Journeys" section in the document
- Traveller section parsing details
- Date extraction method used

### Help

View all available options:

```bash
python rejsekort_parser.py --help
```

### Output

The script will:
1. Display a summary table of all journeys in the terminal
2. Show total number of journeys and total cost
3. Prompt you to save the data to CSV

#### Normal Mode Output

```
Processing: REJSEKORT_2026-01-02_vSulw3QXSQpGq55bH3.pdf
  Found 2 journey(s)
  Date: 2026-01-01

==================================================================================================================================
Date         Time        Route                                    Traveller            Type                 Price     
==================================================================================================================================
2026-01-01   14:46-15:04 Hawkins Middle School → Downtown Hawki... Mike Wheeler         Young person         DKK 32.20
2026-01-01   15:43-16:02 Downtown Hawkins → Hawkins Middle School  Mike Wheeler         Young person         DKK 13.80
==================================================================================================================================
Total: 2 journey(s), Total cost: DKK 46.00

Save to CSV? (y/n):
```

#### Verbose Mode Output

When using `--verbose` or `-v`, you'll see additional debug information:

```
Processing: REJSEKORT_2026-01-02_vSulw3QXSQpGq55bH3.pdf
  DEBUG: Found 'Journeys' section at position 150
  DEBUG: Found 2 price entries
  DEBUG: For price DKK 32.20, found 1 journey patterns
  DEBUG: Traveller section length: 85 chars
  DEBUG: For price DKK 13.80, found 2 journey patterns
  DEBUG: Traveller section length: 75 chars
  Found 2 journey(s)
  Date: 2026-01-01
```

#### Warning and Error Messages

The script provides contextual warnings and errors:

- **WARNING** messages indicate potential issues but processing continues
- **ERROR** messages indicate critical failures

Examples:
```
WARNING: Suspicious date 2030-12-25 (date in future)
WARNING: Suspicious origin 'X@#$%...' : Too many special characters
WARNING: Journey suspiciously far from price (650 chars)
WARNING: Using date from filename: REJSEKORT_2026-01-02_abc.pdf
ERROR: Could not extract date from PDF
```

## CSV Export Format

The exported CSV file uses European formatting optimized for Excel compatibility:
- **Delimiter**: Semicolon (`;`)
- **Decimal separator**: Comma (`,`)
- **Encoding**: UTF-8 with BOM (Byte Order Mark)

The BOM ensures that Excel on Windows correctly recognizes the UTF-8 encoding and displays Danish characters (æ, ø, å) properly.

### CSV Columns

| Column | Description | Example |
|--------|-------------|---------|
| date | Journey date in YYYY-MM-DD format | 2026-01-01 |
| departure_time | Departure time in HH:MM format | 14:46 |
| arrival_time | Arrival time in HH:MM format | 15:04 |
| origin | Starting location | Hawkins Middle School |
| destination | Ending location | Downtown Hawkins |
| traveller_name | Name(s) of traveller(s) | Mike Wheeler or Mike Wheeler + Eleven |
| traveller_type | Type(s) of traveller(s) | Young person or Young person + Child |
| price | Journey price with comma decimal | 32,20 |

### Multiple Travelers

When multiple travelers are on the same journey, they are separated with ` + `:
- Names: `Mike Wheeler + Dustin Henderson`
- Types: `Young person + Child`

### Excel Compatibility

The CSV format is optimized for direct opening in Excel:
- **Windows Excel**: Opens correctly with automatic delimiter detection
- **Mac Excel**: Opens correctly
- **LibreOffice Calc**: Opens correctly
- **Google Sheets**: Import with semicolon delimiter

If you see garbled characters (Ã¦ instead of æ) when opening in Excel:
1. Go to **Data → Get Data → From Text/CSV**
2. Select the file
3. Choose encoding: **65001: Unicode (UTF-8)**
4. Delimiter should be automatically detected as semicolon

## Supported Traveller Types

The script recognizes the following traveller types (case-insensitive):

- **Young person** (Ungdomskort)
- **Adult** / **Voksen** (Standard adult fare)
- **Child** / **Barn** (Children's fare)
- **Senior** / **Pensionist** (Senior citizen fare)

The script performs case-insensitive matching, so "Young Person", "young person", and "YOUNG PERSON" are all recognized.

## Data Validation

The script performs several validation checks to ensure data quality:

### Location Validation
- Minimum length: 3 characters
- Maximum length: 100 characters
- Special character ratio: Warns if >30% are special characters (potential garbage data)

### Date Validation
- Must be between 2020 and current year + 1
- Supports multiple formats:
  - English month names: "01 Jan 2026", "01. Jan 2026"
  - Danish month names: "01 jan 2026", "01 maj 2026"
- Fallback: Extracts date from filename pattern `REJSEKORT_YYYY-MM-DD_*.pdf`

### Journey Validation
- Distance check: Warns if journey details are >500 characters from price entry
- Ensures journey patterns are within the "Journeys" section of the document

All validation warnings are displayed during processing and can be reviewed to identify potential parsing issues.

## PDF File Format

The script is designed to parse Rejsekort PDF receipts with the following structure:

```
Overview
[Date]

Payment Summary
Invoice – [Date]
[Account details]

Journeys              Ticket    Amount
HH:MM Location1 →     
      Location2 HH:MM Standard  DKK XX.XX
Travellers
Name Type
Name Type

[Additional journeys...]

Subtotal              DKK XX.XX
Amount charged        DKK XX.XX
```

## Troubleshooting

### First Step: Enable Verbose Mode

For any parsing issues, always run with verbose mode first:

```bash
python rejsekort_parser.py --verbose
```

This will show detailed debug information about:
- Where the script is searching
- How many patterns it's finding
- What sections it's extracting

### No journeys extracted

If the script reports `WARNING: No journeys extracted`:

1. **Run in verbose mode** to see what's being extracted
2. Check that the PDF is a valid Rejsekort receipt (not account summary)
3. Verify the PDF contains actual journey data
4. Check if the file is corrupted

In verbose mode, the script will display the first 500 characters of extracted text to help diagnose the issue.

### Wrong date extracted

The script tries multiple date format patterns:
- `Invoice – DD MMM YYYY`
- `Overview DD MMM YYYY`
- Danish months: `DD jan/feb/maj/okt YYYY`
- Filename: `REJSEKORT_YYYY-MM-DD_*.pdf`

If the date shows as "Unknown", the PDF may use a different format. Check verbose output to see what date extraction methods were attempted.

### Missing traveller information

Traveller information must appear between the price line (`Standard DKK XX.XX`) and the next journey or `Subtotal` section.

The script supports two formats:
- Name and type on same line: `Mike Wheeler Young person`
- Name and type on separate lines:
  ```
  Mike Wheeler
  Young person
  ```

Run with `--verbose` to see the extracted traveller section.

### Character encoding issues

The script automatically:
- Replaces non-breaking spaces (`0xa0`) with regular spaces
- Uses UTF-8 encoding with BOM for CSV export

If you see strange characters in the output, the PDF may have unusual encoding. The CSV file should display correctly in Excel.

### Suspicious warnings

The script may display warnings about:
- **Suspicious dates**: Dates before 2020 or in the future
- **Suspicious locations**: Very short, very long, or containing many special characters
- **Journey-price distance**: Journey details far from their price entry

These warnings indicate potential parsing issues but don't stop processing. Review the output data for accuracy.

## Technical Details

### Parsing Strategy

The script uses a robust multi-phase parsing approach:

1. **"Journeys" section detection**: Limits search area to avoid false positives from headers/footers
2. **Price-based detection**: Finds all `Standard DKK XX.XX` entries (reliable anchors)
3. **Backward journey extraction**: For each price, searches backward to find the associated journey details
4. **Forward traveller extraction**: For each price, searches forward to extract traveller information
5. **Validation**: Checks location quality, date range, and journey-price proximity

This approach is more robust than trying to match the entire journey pattern at once, especially when PDF text extraction introduces line breaks in unexpected places.

### Performance Optimizations

- **Pre-compiled regex patterns**: All patterns compiled at module level for better performance
- **Limited search scope**: Only searches within "Journeys" section when available
- **Early validation**: Filters out invalid data before full processing

### Text Extraction

The script uses PyPDF2 to extract text from PDFs. Note that:
- Text extraction quality depends on how the PDF was created
- Some PDFs may have unusual spacing or line breaks
- Non-breaking spaces are automatically normalized
- The script handles multi-line location names

### Data Quality Checks

The script validates:
- **Locations**: Length (3-100 chars) and special character ratio (<30%)
- **Dates**: Range (2020 to current year + 1) and format matching
- **Journey-price proximity**: Warns if >500 characters apart
- **Traveller types**: Case-insensitive matching with normalization

## Examples

### Single Journey Receipt

```
12:15 Mirkwood Forest → The Lab 12:19
Standard DKK 23.00
Travellers
Eleven Young person
```

Extracts as:
- Date: 2026-01-03
- Time: 12:15-12:19
- Route: Mirkwood Forest → The Lab
- Traveller: Eleven
- Type: Young person
- Price: 23,00

### Multiple Travelers

```
12:15 Palace Arcade → Benny's Burgers 12:19
Standard DKK 23.00
Travellers
Lucas Sinclair Young person
Barn
```

Extracts as:
- Traveller: Lucas Sinclair
- Type: Young person + Child

### Multiple Journeys

The script correctly separates multiple journeys in the same PDF and associates each traveller section with its corresponding journey.

### Troubleshooting with Verbose Mode

If journeys aren't being extracted correctly:

```bash
python rejsekort_parser.py --verbose problem_file.pdf
```

Output will show:
```
Processing: problem_file.pdf
  DEBUG: Found 'Journeys' section at position 180
  DEBUG: Found 2 price entries
  DEBUG: For price DKK 23.00, found 1 journey patterns
  DEBUG: Traveller section length: 95 chars
  WARNING: Suspicious origin 'X@#$%^...' : Too many special characters
  Found 1 journey(s)
  Date: 2026-01-03
```

This reveals that one journey had an invalid origin, helping identify the parsing issue.

## Output File

Default output filename: `rejsekort_journeys.csv`

The file can be opened in:
- Microsoft Excel (automatically recognizes semicolon delimiter)
- Google Sheets (import with custom delimiter)
- LibreOffice Calc
- Any text editor

## Version History

### Current Version (v28+)
Major refactoring and robustness improvements:

**Core Features:**
- Extracts date, time, route, traveller name, traveller type, and price
- Handles multiple travelers per journey
- Handles multiple journeys per PDF
- European CSV formatting (semicolon delimiter, comma decimal)
- Automatic non-breaking space removal

**Robustness & Validation:**
- Location validation (length, special character detection)
- Date validation with multiple format support (English/Danish months)
- Filename-based date fallback
- Case-insensitive traveller type matching
- Distance validation between journey and price entries
- "Journeys" section detection for focused parsing

**User Experience:**
- Verbose mode (`--verbose` or `-v`) for detailed debug output
- Conditional debug/warning/error messages
- Better error handling with contextual information
- Command-line argument parsing with `--help`
- UTF-8 with BOM for Excel compatibility

**Performance:**
- Pre-compiled regex patterns
- Optimized search scope

### Version 27 (Baseline)
Initial working version with basic functionality:
- Basic PDF text extraction
- Simple journey pattern matching
- CSV export with comma delimiter
- Manual processing of multiple travelers

For detailed changelog, see git commit history.

## Support

For issues or questions:

1. **Run in verbose mode** to see detailed processing information:
   ```bash
   python rejsekort_parser.py --verbose
   ```

2. **Check the troubleshooting section** in this documentation

3. **Review warning and error messages** - they provide specific information about what went wrong

4. **Examine the debug output** - shows exactly what the script found and where it's looking

The script includes comprehensive logging to help identify parsing issues without needing to modify the code.

## License

This script is licensed under the GNU General Public License v3.0.