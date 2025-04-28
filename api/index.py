from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def fetch_download_links(movie_url):
    """ Fetch download links from a movie's page. """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(movie_url, headers=headers)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the div with id "download"
    download_div = soup.find("div", id="download")
    if not download_div:
        return []

    # Extract download links (ignore <span> inside <a>)
    download_links = []
    for li in download_div.find_all("li"):
        a_tag = li.find("a")
        if a_tag:
            for span in a_tag.find_all("span"):
                span.extract()  # Remove span elements

            download_links.append({
                "title": a_tag.text.strip(),
                "url": a_tag["href"]
            })

    return download_links


def scrape_data(search_query, page_number=1):
    """ Scrape movie search results and fetch download links for each. """
    base_url = "https://mkvking.online/"
    search_url = f"{base_url}page/{page_number}/?s={search_query.replace(' ', '+')}&post_type%5B%5D=post&post_type%5B%5D=tv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        return {"error": "Failed to fetch the page"}

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the div with class "gmr-main-load"
    main_load_div = soup.find("div", id="gmr-main-load")
    if not main_load_div:
        return {"error": "No results found in gmr-main-load"}

    # Find all <article> tags inside this div
    articles = main_load_div.find_all("article")

    results = []
    movie_id = 1  # Unique ID for each movie

    for article in articles:
        # Extract movie data
        content_thumbnail = article.find("div", class_="content-thumbnail")
        url, poster, poster_alt = None, None, None

        if content_thumbnail:
            a_tag = content_thumbnail.find("a")
            img_tag = content_thumbnail.find("img")

            url = a_tag["href"] if a_tag else None
            poster = img_tag["src"] if img_tag else None
            poster_alt = img_tag["alt"] if img_tag else None

        # Extract title
        item_article = article.find("div", class_="item-article")
        title = item_article.find("h2", class_="entry-title").text.strip() if item_article and item_article.find("h2", class_="entry-title") else "No Title"

        # Extract tags
        gmr_movie_on = item_article.find("div", class_="gmr-movie-on") if item_article else None
        tags = []
        if gmr_movie_on:
            for a in gmr_movie_on.find_all("a"):
                tags.append({
                    "label": a.text.strip(),
                    "url": a["href"]
                })

        # Fetch download links from the movie's detail page
        download_links = fetch_download_links(url) if url else []

        # Append data in required format
        results.append({
            "id": movie_id,
            "url": url,
            "poster": poster,
            "poster_alt": poster_alt,
            "title": title,
            "tags": tags,
            "download_links": download_links
        })
        movie_id += 1  # Increment ID for next movie

    return results


@app.route('/api/movies', methods=['POST'])
def get_movies():
    """ API endpoint to fetch movie search results with pagination. """
    data = request.get_json()
    search_query = data.get("query")
    page_number = data.get("page", 1)  # Default to page 1

    if not search_query or not isinstance(search_query, str):
        return jsonify({"error": "Invalid search query"}), 400

    if not isinstance(page_number, int) or page_number < 1:
        return jsonify({"error": "Invalid page number"}), 400

    return jsonify(scrape_data(search_query, page_number))


if __name__ == '__main__':
    app.run(debug=True)
