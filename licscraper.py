import argparse
import getpass
import re
import requests
import signal
import sys
import time
from linkedin_api import Linkedin
import configparser

EXAMPLE_TEXT = """example:
    python3 ./licscraper.py --oxylabs-user YOUR_OXYLABS_USERNAME --oxylabs-password YOUR_OXYLABS_PASSWORD --linkedin-user YOUR_LINKEDIN_USERNAME --linkedin-password YOUR_LINKEDIN_PASSWORD --runs 3 --pages 5 --start-page 1 --query "site:linkedin.com software engineer"
    """

SCRIPT_URL = (
    "https://raw.githubusercontent.com/steelproxy/licscraper/main/licscraper.py"
)

#1sTheBest

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

def get_credentials_from_config():
    """Read credentials from config file."""
    config = configparser.ConfigParser()
    config.read("credentials.ini")

    oxylabs_user = config.get("Oxylabs", "username", fallback=None)
    oxylabs_password = config.get("Oxylabs", "password", fallback=None)
    linkedin_user = config.get("LinkedIn", "username", fallback=None)
    linkedin_password = config.get("LinkedIn", "password", fallback=None)

    return oxylabs_user, oxylabs_password, linkedin_user, linkedin_password

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
            'source': 'google_search',
            'user_agent_type': 'desktop_chrome',
            'parse': "true",
            'limit': '100',
            'query': "site:linkedin.com " + query,
            #"start_page": str(start),
            #"pages": str(pages),
            'locale': 'en-us',
            'context': [ 
                {'key': 'filter', "value": 1}, 
                {'key': 'results_language', "value": 'en'}, 
                {'key': 'nfpr', "value": True}
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
            
        run_results = search_serp_results(response)    
        for result in run_results:
            profile_names.add(result)
        
        run_time = time.time() - run_start_time
        print(f"run {run} completed in {run_time:.2f} seconds. ")
        start = int(start) + pages

    print(
        f"all runs completed in {(time.time() - start_time):.2f} seconds."
    )
    return profile_names

def get_credentials(prompt):
    """Prompt user for credentials."""
    return getpass.getpass(prompt)

def get_input(prompt, default):
    """Prompt user for input with default value."""
    value = input(prompt).strip()
    if not value:
        return default
    return int(value) if value else 1

def save_credentials_to_config(oxylabs_user, oxylabs_password, linkedin_user, linkedin_password):
    """Save credentials to config file."""
    try:
        config = configparser.ConfigParser()
        config["Oxylabs"] = {"username": oxylabs_user, "password": oxylabs_password}
        config["LinkedIn"] = {"username": linkedin_user, "password": linkedin_password}

        with open("credentials.ini", "w") as configfile:
            config.write(configfile)
        print("Credentials saved successfully.")
    except Exception as e:
        print(f"Error occurred while saving credentials: {str(e)}")

def main():
    """Main function."""
    args = parse_arguments()
    signal.signal(signal.SIGINT, handle_interrupt)
    
    # Check if credentials are provided via command line arguments
    if args.oxylabs_user and args.oxylabs_password and args.linkedin_user and args.linkedin_password:
        oxylabs_user = args.oxylabs_user
        oxylabs_password = args.oxylabs_password
        linkedin_user = args.linkedin_user
        linkedin_password = args.linkedin_password
    else:
        # Read credentials from config file
        oxylabs_user, oxylabs_password, linkedin_user, linkedin_password = get_credentials_from_config()

        # If not found in config, prompt the user for credentials
        if not (oxylabs_user and oxylabs_password and linkedin_user and linkedin_password):
            print("Credentials not found in config file. Please enter them manually.")
            oxylabs_user = input("Enter Oxylabs username: ")
            oxylabs_password = getpass.getpass("Enter Oxylabs password: ")
            linkedin_user = input("Enter LinkedIn username: ")
            linkedin_password = getpass.getpass("Enter LinkedIn password: ")
            
            save_credentials = input("Do you want to save these credentials? (yes/no): ")
            if save_credentials.lower() == "yes":
                save_credentials_to_config(oxylabs_user, oxylabs_password, linkedin_user, linkedin_password)

        # If not found in config, prompt the user for credentials
        if not (oxylabs_user and oxylabs_password and linkedin_user and linkedin_password):
            print("Credentials not found in config file. Please enter them manually.")
            oxylabs_user = input("Enter Oxylabs username: ")
            oxylabs_password = getpass.getpass("Enter Oxylabs password: ")
            linkedin_user = input("Enter LinkedIn username: ")
            linkedin_password = getpass.getpass("Enter LinkedIn password: ")

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

    serp_results = run_serp_scraper(oxylabs_user, oxylabs_password, runs, pages, start_page, query)
    linkedin_results = set()
    for profile in serp_results:
        contact_info = client.get_profile_contact_info(profile)
        if contact_info:
                print(profile)
                if contact_info["email_address"]:
                    print("\tEmail: " + str(contact_info["email_address"]))
                    
                if contact_info["websites"]:
                    print("\tWebsites: ")
                    for website in contact_info["websites"]:
                        print("\t\t" + website["url"])
                if contact_info["twitter"]:
                    print("\tTwitter: " + str(contact_info["twitter"]))
                if contact_info["ims"]:
                    print("\tIMS: " + str(contact_info["ims"]))
                if contact_info["phone_numbers"]:
                    print("\tPhone numbers: ")
                    for phone in contact_info["phone_numbers"]:
                        print("\t\t" + str(phone))
                print("end. \n")
    #linkedin_results = scrape_linkedin(client, serp_results)
    
    for result in linkedin_results:
        print(str(result))


if __name__ == "__main__":
    main()
