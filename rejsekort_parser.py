import re
import sys
from pathlib import Path
from datetime import datetime
import csv

try:
    import PyPDF2
except ImportError:
    print("PyPDF2 not installed. Install with: pip install PyPDF2")
    sys.exit(1)


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    
    # Replace non-breaking spaces (0xa0) with regular spaces
    text = text.replace('\xa0', ' ')
    
    return text


def parse_rejsekort_receipt(text):
    """Parse Rejsekort receipt text and extract journey information."""
    journeys = []
    
    # Extract invoice date - try multiple patterns
    invoice_date = "Unknown"
    
    # Try standard format
    date_match = re.search(r'Invoice\s*[–-]\s*(\d{2}\s+\w{3}\s+\d{4})', text)
    if date_match:
        try:
            date_str = date_match.group(1)
            invoice_date = datetime.strptime(date_str, '%d %b %Y').strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    # Try alternative format in overview
    if invoice_date == "Unknown":
        overview_match = re.search(r'Overview\s+(\d{2}\s+\w{3}\s+\d{4})', text)
        if overview_match:
            try:
                date_str = overview_match.group(1)
                invoice_date = datetime.strptime(date_str, '%d %b %Y').strftime('%Y-%m-%d')
            except ValueError:
                pass
    
    # Find all price entries
    price_pattern = r'Standard\s+DKK\s+([\d.]+)'
    price_matches = list(re.finditer(price_pattern, text))
    
    print(f"  DEBUG: Found {len(price_matches)} price entries")
    
    # For each price, work backwards to find the journey details
    for price_match in price_matches:
        price = price_match.group(1)
        
        # Get text before this price
        text_before_price = text[:price_match.start()]
        
        # Find the most recent journey pattern before this price
        journey_pattern = r'(\d{2}:\d{2})\s+([^→]+?)\s*→\s*([^S]+?)(\d{2}:\d{2})'
        
        # Search from the end backwards
        matches = list(re.finditer(journey_pattern, text_before_price))
        if not matches:
            continue
            
        # Take the last match
        match = matches[-1]
        
        departure_time = match.group(1)
        origin = match.group(2).strip()
        destination_raw = match.group(3).strip()
        arrival_time = match.group(4)
        
        # Clean up destination
        destination = re.sub(r'^\d{2}:\d{2}\s+', '', destination_raw)
        
        # Clean up location names
        origin = re.sub(r'\s+', ' ', origin).strip()
        destination = re.sub(r'\s+', ' ', destination).strip()
        
        # Find traveller info AFTER this price (not before)
        # Travellers section starts after "Standard DKK XX.XX"
        traveller_start = price_match.end()
        
        # Find where this journey's traveller section ends
        # It should end at the next journey time pattern (HH:MM at start of line)
        traveller_section_text = text[traveller_start:]
        
        # Look for the next time pattern that indicates a new journey
        # Pattern: newline followed by time HH:MM
        next_journey_match = re.search(r'\n\d{2}:\d{2}\s+\S', traveller_section_text)
        
        if next_journey_match:
            traveller_end = traveller_start + next_journey_match.start()
        else:
            # No next journey found, look for Subtotal
            subtotal_pos = text.find("Subtotal", traveller_start)
            if subtotal_pos != -1:
                traveller_end = subtotal_pos
            else:
                traveller_end = len(text)
        
        traveller_section = text[traveller_start:traveller_end]
        
        # Debug: show what we're searching in
        print(f"  DEBUG: Traveller section text: {traveller_section[:200]}")
        
        traveller_pattern = r'Travellers\s+(.+)'
        traveller_match = re.search(traveller_pattern, traveller_section, re.DOTALL)
        
        if not traveller_match:
            traveller_display = "N/A"
            traveller_type_display = "Unknown"
        else:
            traveller_info = traveller_match.group(1).strip()
            
            # Parse traveller information
            traveller_lines = [line.strip() for line in traveller_info.split('\n') if line.strip()]
            
            travellers = []
            for line in traveller_lines:
                if not line or 'Standard' in line or 'DKK' in line:
                    break
                    
                traveller_type = "Unknown"
                traveller_name = line
                
                if "Young person" in line:
                    traveller_type = "Young person"
                    traveller_name = line.replace("Young person", "").strip()
                elif "Voksen" in line or "Adult" in line:
                    traveller_type = "Adult"
                    traveller_name = line.replace("Voksen", "").replace("Adult", "").strip()
                elif "Child" in line:
                    traveller_type = "Child"
                    traveller_name = line.replace("Child", "").strip()
                elif "Barn" in line:
                    traveller_type = "Child"
                    traveller_name = line.replace("Barn", "").strip()
                elif "Senior" in line or "Pensionist" in line:
                    traveller_type = "Senior"
                    traveller_name = line.replace("Senior", "").replace("Pensionist", "").strip()
                
                if not traveller_name:
                    traveller_name = "N/A"
                
                travellers.append({
                    'name': traveller_name,
                    'type': traveller_type
                })
            
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
            journeys = parse_rejsekort_receipt(text)
            
            if not journeys:
                print(f"  WARNING: No journeys extracted. First 500 chars of text:")
                print(f"  {text[:500]}")
            
            all_journeys.extend(journeys)
            print(f"  Found {len(journeys)} journey(s)")
            
            if journeys:
                print(f"  Date: {journeys[0]['date']}")
                
        except Exception as e:
            print(f"  Error processing {pdf_path}: {e}")
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
    """Save journey data to a CSV file."""
    if not journeys:
        print("No journeys to save.")
        return
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
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
    if len(sys.argv) > 1:
        pdf_paths = [Path(arg) for arg in sys.argv[1:] if arg.endswith('.pdf')]
    else:
        pdf_paths = list(Path('.').glob('REJSEKORT_*.pdf'))
    
    if not pdf_paths:
        print("No Rejsekort PDF files found.")
        print("Usage: python script.py [file1.pdf file2.pdf ...]")
        print("   or: Place REJSEKORT_*.pdf files in the current directory")
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
