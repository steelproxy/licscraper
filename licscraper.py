import argparse
import getpass
import re
import requests
import signal
import sys
import time
from linkedin_api import Linkedin

EXAMPLE_TEXT = """example:
    python3 ./licscraper.py --oxylabs-user YOUR_OXYLABS_USERNAME --oxylabs-password YOUR_OXYLABS_PASSWORD --linkedin-user YOUR_LINKEDIN_USERNAME --linkedin-password YOUR_LINKEDIN_PASSWORD --runs 3 --pages 5 --start-page 1 --query "site:linkedin.com software engineer"
    """

SCRIPT_URL = (
    "https://raw.githubusercontent.com/steelproxy/licscraper/main/licscraper.py"
)

def handle_interrupt(sig, frame):
    """Handle SIGINT signal."""
    print("\nCaught SIGINT, ending search.")
    sys.exit(0)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="licscraper",
        description="Linkedin scraper using OxyLabs SERP scraping API",
        epilog=EXAMPLE_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--oxylabs-user", help="Oxylabs username")
    parser.add_argument("--oxylabs-password", help="Oxylabs password")
    parser.add_argument("--linkedin-user", help="LinkedIn username")
    parser.add_argument("--linkedin-password", help="LinkedIn password")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs (default: 1)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages (default: 1)")
    parser.add_argument("--start-page", type=int, default=1, help="Starting page (default: 1)")
    parser.add_argument("--query", help="Search query")
    return parser.parse_args()

def clean_linkedIn_profile_name(profile_url):
    """Extract profile names from LinkedIn URLs."""
    linkedin_regex = r"(?i)https?://(?:www\.)?linkedin\.com/in/([^\s/]+)"
    match = re.search(linkedin_regex, profile_url)
    if match:
        profile_name = match.group(1)
        cleaned_profile_name = re.sub(r'[^a-zA-Z0-9-_]', '', profile_name)
        return cleaned_profile_name
    else:
        return None

def search_serp_results(response):
    """Search for pattern in response JSON."""
    unique_matches = set()
    for page in response.json()["results"]:
        for result in page.get("content", {}).get("results", {}).get("organic", {}):
            profile_url = str(result.get("url", {}))
            profile_name = clean_linkedIn_profile_name(profile_url)
            if profile_name:
                if profile_name not in unique_matches:
                    unique_matches.add(profile_name)
                    print(profile_name + ", " + profile_url)
    return unique_matches

def run_serp_scraper(user, password, runs, pages, start, query):
    """Main function to execute the SERP scraper."""
    profile_names = set()
    start_time = time.time()
    print("Starting requests...")

    for run in range(1, runs + 1):
        run_start_time = time.time()
        print(
            f"Running request with query: '{query}', starting page: {str(start)}, run: {str(run)}..."
        )
        payload = {
            "source": "google_search",
            "user_agent_type": "desktop_chrome",
            "parse": True,
            "locale": "en-us",
            "query": query,
            "start_page": str(start),
            "pages": str(pages),
            "context": [
                {"key": "filter", "value": 1},
                {"key": "results_language", "value": "en"},
            ],
        }
        response = requests.post(
            "https://realtime.oxylabs.io/v1/queries",
            auth=(user, password),
            json=payload,
        )
        if not response.ok:
            print("ERROR! Bad response received.")
            print(response.text)
            sys.exit(1)
        profile_names.add(search_serp_results(response))
        run_time = time.time() - run_start_time
        print(f"run {run} completed in {run_time:.2f} seconds. ")
        start = int(start) + pages

    print(
        f"all runs completed in {(time.time() - start_time):.2f} seconds."
    )
    return profile_names

def scrape_linkedin(client, queries):
    results = set()
    for profile in queries:
        contact_info = client.get_profile_contact_info(profile)
        if contact_info:
            results.add(contact_info)
    return results

def get_credentials(prompt):
    """Prompt user for credentials."""
    return getpass.getpass(prompt)

def get_input(prompt, default):
    """Prompt user for input with default value."""
    value = input(prompt).strip()
    if not value:
        return default
    return int(value) if value else 1

def main():
    """Main function."""
    args = parse_arguments()
    signal.signal(signal.SIGINT, handle_interrupt)
    
    # Prompt for Oxylabs credentials if not provided
    oxylabs_user = args.oxylabs_user if args.oxylabs_user else input("Enter Oxylabs username: ")
    oxylabs_password = args.oxylabs_password if args.oxylabs_password else get_credentials("Enter Oxylabs password: ")

    # Prompt for LinkedIn credentials if not provided
    linkedin_user = args.linkedin_user if args.linkedin_user else input("Enter LinkedIn username: ")
    linkedin_password = args.linkedin_password if args.linkedin_password else get_credentials("Enter LinkedIn password: ")

    # Prompt for runs, pages, and start_page if not provided
    runs = args.runs if args.runs else get_input("Enter number of runs (default: 1): ", 1)
    pages = args.pages if args.pages else get_input("Enter number of pages (default: 1): ", 1)
    start_page = args.start_page if args.start_page else get_input("Enter starting page (default: 1): ", 1)

    # Prompt for query if not provided
    query = args.query if args.query else input("Enter search query: ")

    # Login to linkedin
    try:
        client = Linkedin(linkedin_user, linkedin_password)
    except:
        print("error! unable to connect or authenticate with LinkedIn")
        exit(1)

    serp_results = run_serp_scraper(oxylabs_user, oxylabs_password, runs, pages, start_page, "site:linkedin.com ohio mayor")

    for run in serp_results:
        linkedin_results = scrape_linkedin(client, run)
        for contact in linkedin_results:
            print(str(contact))    

    client.logout()

if __name__ == "__main__":
    main()
