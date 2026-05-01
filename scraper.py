import re
import json, os
from collections import defaultdict 
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
from utils.__init__ import get_logger
import hashlib
"""near duplicates use
-search
- discovery
discovery uses fingerprints
similarity = fingerprint intersection / fingerprint union (done by hashing)
define a threshold
if similarity >= threshold, they are near dupes"""

fingerprints = {}

def hash_helper_differences(h1,h2):
    #finds num bits differing between the hashes
    x = h1 ^ h2
    dist = 0
    while x:
        dist += 1
        x &= x-1
    return dist

def compute_fingerprint(tokens):
    #computes fingerprint by hashing
    v = [0] * 64
    for token in tokens:
        token_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
        for i in range(64):
            bit = (token_hash>>i) & 1
            if bit:
                v[i] +=1
            else:
                v[i]-=1
    fingerprint = 0
    for i in range(64):
        if v[i] >= 0:
            fingerprint |= (1<<i)
    return fingerprint

def is_near_dupe(new_fp, threshold = 3):
    #compares hash differences (or similairity) to threshold
    # to determine if it is a near duplicate
    for fp in fingerprints.keys():
        if hash_helper_differences(new_fp, fp) <= threshold:
            return True, fingerprints[fp]
    return False, None


seen_content_hashes = set()
pages_parsed = 0

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

def load_analytics():
    if os.path.exists("analytics.json"):
        with open("analytics.json", "r") as file:
            data = json.load(file)
            crawl_data["unique_pages"] = set(data["unique_pages"])
            crawl_data["longest_page"] = data["longest_page"]
    
            crawl_data["word_freq"] = defaultdict(int, data["word_freq"])
            crawl_data["subdomains"] = defaultdict(set, {k: set(v) for k, v in data["subdomains"].items()})


""" Document pages numbers, lengths, word frequencies etc. for generaing report """
def save_analytics():
    data = {
        "unique_pages": list(crawl_data["unique_pages"]),
        "longest_page": crawl_data["longest_page"],
        "word_freq": dict(crawl_data["word_freq"]),
        "subdomains": {key: list(value) for key, value in crawl_data["subdomains"].items()}
    }
    with open("analytics.json", "w") as file:
        json.dump(data, file)


""" Tokenize cleaned text, removing stop words, returns valid tokens """
def tokenizer(text):
    valid_tokens = []
    tokens = re.findall(r'[a-zA-Z0-9]+', text.lower())
    for token in tokens:
        if token not in STOP_WORDS and len(token) > 1:  
            valid_tokens.append(token)
    return valid_tokens

""" Prints the report """
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

""" Updates crawl data for each page """
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




""" Extract hyperlink, defragments them, returns a list of potential links to crawl """
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

    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    try:
        for link in soup.find_all("a"):
            ex_href = link.get('href')
            if ex_href:
    
                defrag_url, frag = urldefrag(urljoin(url, ex_href)) # Defragment the URL
                link_list.append(defrag_url)
    except Exception:
        print("ERROR: Failed to parse")

    return link_list

""" Validates a URL + decides if its worth crawling """
def is_valid(url):
    try:
        parsed = urlparse(url)
        
        # Must be http or https
        if parsed.scheme not in {"http", "https"}:
            return False
        
        # Allowed domains
        given_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
        allowed = any(
            parsed.netloc == d or parsed.netloc.endswith("." + d)
            for d in given_domains
        )
        if not allowed:
            return False

        # Avoid overly long URLs (likely traps)
        if len(url) > 200:
            return False
        

        # Avoid URLs with too many query parameters (likely traps)
        if len(parsed.query) > 100:
            return False
        
        path_lower = parsed.path.lower()
        query_lower = parsed.query.lower()

        # Path depth 
        path_parts = [p for p in path_lower.split('/') if p]
        if len(path_parts) > 6:
            return False
        
        # Repeated path segments (loop trap)
        if len(path_parts) != len(set(path_parts)):
            return False
        
        # DokuWiki-specific trap: block all action/revision/index params
        if 'doku.php' in parsed.path:
            if re.search(r'(rev|do|idx)=', query_lower):
                return False
        
        #Avoid sorting
        query_lower = parsed.query.lower()
        if re.search(r'(filter|sort|order|limit|action|replytocom|share)=', query_lower):
            return False
            
        # Avoid filters
        if "%5b" in query_lower or "[" in query_lower:
            return False

        
        
        #  Calendar / date traps (
        DATE_PATH_PATTERNS = [
            r'/\d{4}/\d{2}',           # /2024/05 or /2024/05/12
            r'/\d{4}-\d{2}',           # /2024-05
            r'\d{4}-\d{2}-\d{2}',      # any full ISO date anywhere in path
            r'/day/\d',                # /day/2024-...
            r'/page/\d+',              # pagination
        ]
        if any(re.search(p, path_lower) for p in DATE_PATH_PATTERNS):
            return False

        DATE_QUERY_PATTERNS = [
            r'tribe-bar-date', r'\bical\b', r'outlook-ical',
        ]
        if any(re.search(p, query_lower) for p in DATE_QUERY_PATTERNS):
            return False
        
        #  Query param traps 
        TRAP_QUERY_PARAMS = re.compile(
            r'(filter|sort|order|limit|action|replytocom|share|'
            r'attachment_id|keywords|s|search|tag|author|'
            r'sessionid|token|sid)='
        )
        if TRAP_QUERY_PARAMS.search(query_lower):
            return False
        
        # ── Low-value path patterns
        
        LOW_VALUE_PATHS = re.compile(
            r'/(feed|rss|atom|tag|category|author|wp-login|wp-admin|'
            r'wp-json|xmlrpc\.php|comment-page-\d+)(/|$)'
        )
        if LOW_VALUE_PATHS.search(path_lower):
            return False
        
        if 'wp-login' in path_lower:
            return False
        
        if re.search(r'\bC=[DMNS];O=[AD]\b', parsed.query):
            return False


        # Avoid fake links
        if "%20" in url or "http" in parsed.path:
            return False

    
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpg|avi|rm|m4v|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|ppsx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$",
            parsed.path.lower()
        )

    except TypeError:
        print("TypeError for", parsed)
        raise

""" Scrapes page """

def scraper(url, resp):
    if resp.status != 200 or not resp.raw_response or not resp.raw_response.content:
        return []
    
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

    for element in soup(["script", "style"]):
        element.decompose()
    
    # clean the text from HTML format    
    clean_txt = soup.get_text(separator=" ", strip=True)

    """ Exact Duplicate """
    page_hash = hashlib.md5(clean_txt.encode('utf-8')).hexdigest()
    if page_hash in seen_content_hashes:
        return []
    

    """Excessively long pages"""
    content_length = resp.raw_response.headers.get('content-length')
    if content_length and int(content_length) > 10_000_000:  # 10MB
            return []
    
    """ Tokenize clean text"""
    tokenized_text = tokenizer(clean_txt)
    if len(tokenized_text) < 50:
        return []
    
    """Near Duplicate"""
    curr_fp = compute_fingerprint(tokenized_text)
    is_near, original_urls = is_near_dupe(curr_fp)
    if is_near:
        print(f"SKIP: Near-duplicate of {original_urls[0]}")
        return []

    seen_content_hashes.add(page_hash)
    if curr_fp not in fingerprints:
        fingerprints[curr_fp] = []
    fingerprints[curr_fp].append(url)

    update_analytics(url, tokenized_text)
    
    global pages_parsed
    pages_parsed += 1

    # Save analytics every 50 pages to avoid I/O overload

    if pages_parsed % 50 == 0:
        save_analytics()

    links = extract_next_links(url,resp)
    return [link for link in links if is_valid(link)]
