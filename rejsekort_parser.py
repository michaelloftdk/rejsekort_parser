import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
import csv

try:
    import PyPDF2
except ImportError:
    print("PyPDF2 not installed. Install with: pip install PyPDF2")
    sys.exit(1)

# Global verbose flag
VERBOSE = False

# Pre-compile regex patterns for performance
PRICE_PATTERN = re.compile(r'Standard\s+DKK\s+([\d.]+)')
JOURNEY_PATTERN = re.compile(r'(\d{2}:\d{2})\s+([^→]+?)\s*→\s*([^S]+?)(\d{2}:\d{2})')
NEXT_JOURNEY_PATTERN = re.compile(r'\n\d{2}:\d{2}\s+\S')

# Traveller types with case-insensitive matching
TRAVELLER_TYPES = {
    'young person': 'Young person',
    'voksen': 'Adult',
    'adult': 'Adult',
    'child': 'Child',
    'barn': 'Child',
    'senior': 'Senior',
    'pensionist': 'Senior'
}


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    
    # Replace non-breaking spaces with regular spaces
    text = text.replace('\xa0', ' ')
    
    return text


def validate_location(location):
    """
    Validate that a location string is reasonable.
    
    Returns:
        tuple: (is_valid, reason)
    """
    if not location or len(location) < 3:
        return False, "Too short"
    if len(location) > 100:
        return False, "Too long"
    
    # Check for too many special characters (might be parsing garbage)
    special_chars = sum(1 for c in location if not (c.isalnum() or c.isspace() or c in '()-/,æøåÆØÅ'))
    if special_chars > len(location) * 0.3:
        return False, "Too many special characters"
    
    return True, "OK"


def extract_date_robust(text, filename=None):
    """
    Extract date with multiple fallback strategies.
    
    Supports:
    - English month names (Jan, Feb, etc.)
    - Danish month names (jan, feb, mar, etc.)
    - Date from filename as last resort
    
    Returns:
        str: Date in YYYY-MM-DD format or "Unknown"
    """
    # Try multiple date patterns
    patterns = [
        r'Invoice\s*[–-]\s*(\d{2}\s+\w{3,}\s+\d{4})',
        r'Overview\s+(\d{2}\s+\w{3,}\s+\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            
            # Try English month format
            for fmt in ['%d %b %Y', '%d. %b %Y']:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    # Validate date is reasonable
                    current_year = datetime.now().year
                    if date_obj.year < 2020 or date_obj.year > current_year + 1:
                        print(f"  WARNING: Suspicious date {date_obj.strftime('%Y-%m-%d')}")
                    if VERBOSE:
                        print(f"  DEBUG: Extracted date {date_obj.strftime('%Y-%m-%d')} from pattern")
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
    
    # Try Danish month names
    danish_pattern = r'(\d{2})\s+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)\s+(\d{4})'
    danish_match = re.search(danish_pattern, text, re.IGNORECASE)
    if danish_match:
        danish_months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'maj': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12
        }
        day = danish_match.group(1)
        month = danish_months.get(danish_match.group(2).lower())
        year = danish_match.group(3)
        
        if month:
            date_str = f"{year}-{month:02d}-{day}"
            try:
                # Validate the date
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                current_year = datetime.now().year
                if date_obj.year < 2020 or date_obj.year > current_year + 1:
                    print(f"  WARNING: Suspicious date {date_str}")
                if VERBOSE:
                    print(f"  DEBUG: Extracted date {date_str} from Danish month pattern")
                return date_str
            except ValueError:
                pass
    
    # Last resort: extract from filename
    if filename:
        file_date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(filename))
        if file_date_match:
            print(f"  WARNING: Using date from filename: {filename}")
            return f"{file_date_match.group(1)}-{file_date_match.group(2)}-{file_date_match.group(3)}"
    
    print("  ERROR: Could not extract date from PDF")
    return "Unknown"


def parse_travellers_flexible(traveller_info):
    """
    Parse traveller info with flexible format support.
    
    Supports:
    - Name and type on same line: "Mike Wheeler Young person"
    - Name and type on separate lines
    - Case-insensitive type matching
    """
    lines = [line.strip() for line in traveller_info.split('\n') if line.strip()]
    
    travellers = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Skip noise
        if 'Standard' in line or 'DKK' in line or 'Subtotal' in line or 'Amount' in line:
            break
        
        # Check if this line contains a type (case-insensitive)
        found_type = None
        for type_key, type_value in TRAVELLER_TYPES.items():
            if type_key in line.lower():
                found_type = type_value
                # Extract name by removing the type
                name = re.sub(type_key, '', line, flags=re.IGNORECASE).strip()
                break
        
        if found_type:
            # Name and type on same line
            travellers.append({'name': name if name else "N/A", 'type': found_type})
        else:
            # Might be name on one line, type on next
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_type = None
                
                for type_key, type_value in TRAVELLER_TYPES.items():
                    if type_key in next_line.lower():
                        next_type = type_value
                        break
                
                if next_type:
                    # Name on this line, type on next
                    travellers.append({'name': line, 'type': next_type})
                    i += 1  # Skip next line
                else:
                    # Just a name, type unknown
                    travellers.append({'name': line, 'type': "Unknown"})
            else:
                # Last line, just a name
                travellers.append({'name': line, 'type': "Unknown"})
        
        i += 1
    
    return travellers


def parse_rejsekort_receipt(text, filename=None):
    """Parse Rejsekort receipt text and extract journey information."""
    journeys = []
    
    # Extract invoice date with robust fallbacks
    invoice_date = extract_date_robust(text, filename)
    
    # Find the Journeys section to limit search area
    journeys_section_start = text.find("Journeys")
    if journeys_section_start == -1:
        if VERBOSE:
            print("  DEBUG: No 'Journeys' section found, searching entire document")
        journeys_section_start = 0
    else:
        if VERBOSE:
            print(f"  DEBUG: Found 'Journeys' section at position {journeys_section_start}")
    
    # Find all price entries
    price_matches = list(PRICE_PATTERN.finditer(text))
    
    # Only consider prices after the Journeys section
    price_matches = [m for m in price_matches if m.start() > journeys_section_start]
    
    if VERBOSE:
        print(f"  DEBUG: Found {len(price_matches)} price entries")
    
    # For each price, work backwards to find the journey details
    for price_match in price_matches:
        price = price_match.group(1)
        
        # Get text before this price
        text_before_price = text[journeys_section_start:price_match.start()]
        
        # Find the most recent journey pattern before this price
        matches = list(JOURNEY_PATTERN.finditer(text_before_price))
        
        if VERBOSE:
            print(f"  DEBUG: For price DKK {price}, found {len(matches)} journey patterns")
        
        if not matches:
            print(f"  WARNING: No journey pattern found for price DKK {price}")
            continue
        
        # Take the last match
        match = matches[-1]
        
        # Validate distance between journey and price (should be close)
        distance = price_match.start() - (journeys_section_start + match.end())
        if distance > 500:
            print(f"  WARNING: Journey suspiciously far from price ({distance} chars)")
        
        departure_time = match.group(1)
        origin = match.group(2).strip()
        destination_raw = match.group(3).strip()
        arrival_time = match.group(4)
        
        # Clean up destination (remove any stray time stamps)
        destination = re.sub(r'^\d{2}:\d{2}\s+', '', destination_raw)
        
        # Clean up location names
        origin = re.sub(r'\s+', ' ', origin).strip()
        destination = re.sub(r'\s+', ' ', destination).strip()
        
        # Validate locations
        origin_valid, origin_reason = validate_location(origin)
        if not origin_valid:
            print(f"  WARNING: Suspicious origin '{origin[:50]}...': {origin_reason}")
        
        dest_valid, dest_reason = validate_location(destination)
        if not dest_valid:
            print(f"  WARNING: Suspicious destination '{destination[:50]}...': {dest_reason}")
        
        # Find traveller info AFTER this price
        traveller_start = price_match.end()
        traveller_section_text = text[traveller_start:]
        
        # Find where this journey's traveller section ends
        next_journey_match = NEXT_JOURNEY_PATTERN.search(traveller_section_text)
        
        if next_journey_match:
            traveller_end = traveller_start + next_journey_match.start()
        else:
            # No next journey, look for Subtotal
            subtotal_pos = text.find("Subtotal", traveller_start)
            if subtotal_pos != -1:
                traveller_end = subtotal_pos
            else:
                traveller_end = len(text)
        
        traveller_section = text[traveller_start:traveller_end]
        
        if VERBOSE:
            print(f"  DEBUG: Traveller section length: {len(traveller_section)} chars")
        
        # Extract traveller info
        traveller_pattern = r'Travellers\s+(.+)'
        traveller_match = re.search(traveller_pattern, traveller_section, re.DOTALL)
        
        if not traveller_match:
            traveller_display = "N/A"
            traveller_type_display = "Unknown"
        else:
            traveller_info = traveller_match.group(1).strip()
            
            # Parse traveller information with flexible format support
            travellers = parse_travellers_flexible(traveller_info)
            
            # Create formatted string of travelers
            if len(travellers) == 0:
                traveller_display = "N/A"
                traveller_type_display = "Unknown"
            elif len(travellers) == 1:
                traveller_display = travellers[0]['name']
                traveller_type_display = travellers[0]['type']
            else:
                # Filter out empty names before joining
                names = [t['name'] for t in travellers if t['name'] and t['name'] != "N/A"]
                types = [t['type'] for t in travellers if t['type']]
                
                traveller_display = " + ".join(names) if names else "N/A"
                traveller_type_display = " + ".join(types) if types else "Unknown"
        
        journey = {
            'date': invoice_date,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'origin': origin,
            'destination': destination,
            'traveller_name': traveller_display,
            'traveller_type': traveller_type_display,
            'price': float(price),
            'route': f"{origin} → {destination}"
        }
        journeys.append(journey)
    
    return journeys


def process_pdfs(pdf_paths):
    """Process multiple PDF files and extract all journey information."""
    all_journeys = []
    
    for pdf_path in pdf_paths:
        print(f"\nProcessing: {pdf_path}")
        try:
            text = extract_text_from_pdf(pdf_path)
            journeys = parse_rejsekort_receipt(text, pdf_path)
            
            if not journeys:
                print(f"  WARNING: No journeys extracted.")
                if VERBOSE:
                    print(f"  DEBUG: First 500 chars of text:")
                    print(f"  {text[:500]}")
            
            all_journeys.extend(journeys)
            print(f"  Found {len(journeys)} journey(s)")
            
            if journeys:
                print(f"  Date: {journeys[0]['date']}")
                
        except Exception as e:
            print(f"  ERROR processing {pdf_path}: {e}")
            if VERBOSE:
                import traceback
                traceback.print_exc()
    
    return all_journeys


def display_journeys(journeys):
    """Display journeys in a formatted table."""
    if not journeys:
        print("\nNo journeys found.")
        return
    
    print("\n" + "="*130)
    print(f"{'Date':<12} {'Time':<11} {'Route':<40} {'Traveller':<20} {'Type':<20} {'Price':<10}")
    print("="*130)
    
    for journey in journeys:
        time_str = f"{journey['departure_time']}-{journey['arrival_time']}"
        price_str = f"DKK {journey['price']:.2f}"
        route = journey['route']
        if len(route) > 40:
            route = route[:37] + "..."
        
        date_str = journey['date'] if journey['date'] else "Unknown"
        traveller_name = journey.get('traveller_name', 'N/A')
        traveller_type = journey.get('traveller_type', 'N/A')
        
        if len(traveller_type) > 20:
            traveller_type = traveller_type[:17] + "..."
        
        print(f"{date_str:<12} {time_str:<11} {route:<40} {traveller_name:<20} {traveller_type:<20} {price_str:<10}")
    
    print("="*130)
    print(f"Total: {len(journeys)} journey(s), Total cost: DKK {sum(j['price'] for j in journeys):.2f}")


def save_to_csv(journeys, output_file='rejsekort_journeys.csv'):
    """
    Save journey data to CSV file.
    
    Uses UTF-8 with BOM for better Excel compatibility on Windows.
    Uses semicolon delimiter and comma decimal separator for European format.
    """
    if not journeys:
        print("No journeys to save.")
        return
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['date', 'departure_time', 'arrival_time', 'origin', 'destination', 'traveller_name', 'traveller_type', 'price']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        
        writer.writeheader()
        for journey in journeys:
            # Format price with comma as decimal separator
            price_formatted = str(journey.get('price', 0.0)).replace('.', ',')
            
            row = {
                'date': journey.get('date', 'Unknown'),
                'departure_time': journey.get('departure_time', ''),
                'arrival_time': journey.get('arrival_time', ''),
                'origin': journey.get('origin', ''),
                'destination': journey.get('destination', ''),
                'traveller_name': journey.get('traveller_name', 'N/A'),
                'traveller_type': journey.get('traveller_type', 'N/A'),
                'price': price_formatted
            }
            writer.writerow(row)
    
    print(f"\nData saved to {output_file}")


def main():
    """Main function to run the script."""
    global VERBOSE
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Extract journey information from Rejsekort PDF receipts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python rejsekort_parser.py                    # Process all REJSEKORT_*.pdf in current directory
  python rejsekort_parser.py file1.pdf file2.pdf # Process specific files
  python rejsekort_parser.py --verbose          # Show detailed debug output
  python rejsekort_parser.py -v file1.pdf       # Verbose mode with specific file
        '''
    )
    
    parser.add_argument('files', nargs='*', help='PDF files to process')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed debug output')
    
    args = parser.parse_args()
    VERBOSE = args.verbose
    
    # Get PDF files
    if args.files:
        pdf_paths = [Path(f) for f in args.files if f.endswith('.pdf')]
    else:
        pdf_paths = list(Path('.').glob('REJSEKORT_*.pdf'))
    
    if not pdf_paths:
        print("No Rejsekort PDF files found.")
        print("\nUsage: python rejsekort_parser.py [options] [file1.pdf file2.pdf ...]")
        print("   or: Place REJSEKORT_*.pdf files in the current directory")
        print("\nRun with --help for more information")
        return
    
    journeys = process_pdfs(pdf_paths)
    
    journeys.sort(key=lambda x: (x['date'], x['departure_time']))
    
    display_journeys(journeys)
    
    if journeys:
        save_choice = input("\nSave to CSV? (y/n): ").strip().lower()
        if save_choice == 'y':
            save_to_csv(journeys)


if __name__ == "__main__":
    main()
