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
- Python 3.6 or higher

### Dependencies
- PyPDF2

### Installation

Install the required dependency:

```bash
pip install PyPDF2
```

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

### Output

The script will:
1. Display a summary table of all journeys in the terminal
2. Show total number of journeys and total cost
3. Prompt you to save the data to CSV

Example terminal output:

```
Processing: REJSEKORT_2026-01-02_vSulw3QXSQpGq55bH3.pdf
  DEBUG: Found 2 price entries
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

## CSV Export Format

The exported CSV file uses European formatting:
- **Delimiter**: Semicolon (`;`)
- **Decimal separator**: Comma (`,`)
- **Encoding**: UTF-8

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

## Supported Traveller Types

The script recognizes the following traveller types:

- **Young person** (Ungdomskort)
- **Adult** / **Voksen** (Standard adult fare)
- **Child** / **Barn** (Children's fare)
- **Senior** / **Pensionist** (Senior citizen fare)

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

### No journeys extracted

If the script reports `WARNING: No journeys extracted`, check:
1. The PDF is a valid Rejsekort receipt
2. The PDF contains actual journey data (not just account information)
3. The file is not corrupted

The script will display the first 500 characters of extracted text to help diagnose the issue.

### Wrong date extracted

The script tries multiple date format patterns:
- `Invoice – DD MMM YYYY`
- `Overview DD MMM YYYY`

If the date shows as "Unknown", the PDF may use a different format.

### Missing traveller information

Traveller information must appear between the price line (`Standard DKK XX.XX`) and the next journey or `Subtotal` section.

### Character encoding issues

The script automatically replaces non-breaking spaces (`0xa0`) with regular spaces. If you see other strange characters in the output, the PDF may have unusual encoding.

## Technical Details

### Parsing Strategy

The script uses a two-phase parsing approach:

1. **Price-based detection**: Finds all `Standard DKK XX.XX` entries
2. **Backward journey extraction**: For each price, searches backward to find the associated journey details
3. **Forward traveller extraction**: For each price, searches forward to extract traveller information

This approach is more robust than trying to match the entire journey pattern at once, especially when PDF text extraction introduces line breaks in unexpected places.

### Text Extraction

The script uses PyPDF2 to extract text from PDFs. Note that:
- Text extraction quality depends on how the PDF was created
- Some PDFs may have unusual spacing or line breaks
- Non-breaking spaces are automatically normalized

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

## Output File

Default output filename: `rejsekort_journeys.csv`

The file can be opened in:
- Microsoft Excel (automatically recognizes semicolon delimiter)
- Google Sheets (import with custom delimiter)
- LibreOffice Calc
- Any text editor

## Version History

### Current Version
- Extracts date, time, route, traveller name, traveller type, and price
- Handles multiple travelers per journey
- Handles multiple journeys per PDF
- European CSV formatting (semicolon delimiter, comma decimal)
- Automatic non-breaking space removal

## Support

For issues or questions, refer to the debug output provided by the script when processing files. The script includes detailed logging to help identify parsing issues.

## License

This script is licensed under the GNU General Public License v3.0.