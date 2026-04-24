import re
import json, 
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
from utils.__init__ import get_logger


STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's",
    "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll",
    "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
    "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
    "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why",
    "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves"
}

crawl_data = {
    "unique_pages": set(),
    "longest_page": {"url": "", "word_count": 0},
    "word_freq": defaultdict(int),
    "subdomains": defaultdict(set)
}

def save_analytics():
    data = {
        "unique_pages": list(crawl_data["unique_pages"]),
        "longest_page": crawl_data["longest_page"],
        "word_freq": dict(crawl_data["word_freq"]),
        "subdomains": {key: list(value) for key, value in crawl_data["subdomains"].items()}
    }
    with open("analytics.json", "w") as file:
        json.dump(data, file)


def tokenizer(text):
    valid_tokens = []
    tokens = re.findall(r'[a-zA-Z0-9]+', text.lower()) # Extract only valid alphanumeric words
    for token in tokens:
        if token not in STOP_WORDS:
            valid_tokens.append(token)

def generate_report():
    print(f"UNIQUE PAGES: {len(crawl_data['unique_pages'])}")
    page = crawl_data["longest_page"]
    print(f"LONGEST PAGE: {page['url']} ({page['word_count']} words)")
    print("TOP 50 WORDS:")
    sorted_words = sorted(crawl_data["word_freq"].items(), key=lambda x: x[1], reverse=True)
    for i, (word, count) in enumerate(sorted_words[:50], 1):
        print(f"   {i}. {word} - {count}")
    print("SUBDOMAINS:")
    for subdomain in sorted(crawl_data["subdomains"].keys()):
        print(f"   {subdomain}, {len(crawl_data['subdomains'][subdomain])}")

def update_analytics(url, words):
    url = urldefrag(url)[0]
    if url in crawl_data["unique_pages"]:
        return
    crawl_data["unique_pages"].add(url)
    if len(words) > crawl_data["longest_page"]["word_count"]:
        crawl_data["longest_page"] = {"url": url, "word_count": len(words)}
    for word in words:
        crawl_data["word_freq"][word] += 1
    host = urlparse(url).netloc.lower()
    if host.endswith(".uci.edu"):
        crawl_data["subdomains"][host].add(url)

    #store word counts for analysis questions


            
    num_words = len(tokenizer(text))


def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    link_list = []
    
    if resp.status != 200:
        get_logger(resp.error)
        return link_list
    if not resp.raw_response:
        return link_list
    if not resp.raw_response.content:
        return link_list

    soup = BeautifulSoup(resp.raw_response.content, 'xml')
    try:
        for link in soup.find_all("a"):
            ex_href = link.get('href')
            if ex_href:
                
                defrag_url, frag = urldefrag(urljoin(url, ex_href))
                link_list.append(defrag_url)
    except Exception:
        print("ERROR: Failed to parse")

    return link_list

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.


    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]): 
            return False
        given_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
        allowed_subdomains = any(parsed.netloc == p.strip(".") or parsed.netloc.endswith(p) for p in given_domains)
        if parsed.netloc not in allowed_subdomains: # check subdomain
            return False
        
        if len(url) > 150: #likely an infinite loop
            return False
            
        return not re.match(
                r".*\.(css|js|bmp|gif|jpe?g|ico"
                + r"|png|tiff?|mid|mp2|mp3|mp4"
                + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                + r"|epub|dll|cnf|tgz|sha1"
                + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def scraper(url, resp):
    if resp.status != 200 or not resp.raw_response or not resp.raw_response.content:
        return []
    links = extract_next_links(url, resp)
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    for element in soup(["script", "style"]):
        element.decompose()
    clean_txt = soup.get_text(separator=" ", strip=True)
    update_analytics(url, clean_txt)
    return [link for link in links if is_valid(link)]
