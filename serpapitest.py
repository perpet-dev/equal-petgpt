from serpapi import GoogleSearch
search = GoogleSearch({
    "q": "시바 이누는 고양이와 잘 지낼 수 있나요?", 
    "location": "Seoul, South Korea",
    "api_key": "ac0d62b186a62ac8c28c7d85bfce6dc1a9a95e256e16a713106cc3c8ebd9e5c4"
  })
results = search.get_dict()


# `print(result)` is displaying the search result obtained from the Google Search API in a dictionary
# format. It will show information related to the query "시바 이누는 고양이와 잘 지낼 수 있나요?" conducted in Seoul,
# South Korea, such as search results, snippets, and other relevant data.
print(results)


# Iterate over all organic_results
for result in results["organic_results"]:
    position = result["position"]
    title = result["title"]
    link = result["link"]
    snippet = result["snippet"]
    #highlighted_words = ", ".join(result["snippet_highlighted_words"])

    # Print the extracted information
    print(f"Position: {position}, Title: {title}, Link: {link}")
    print(f"Snippet: {snippet}")
    #print(f"Highlighted Words: {highlighted_words}\n")

# Iterate over Related Questions
print("Related Questions:")
for question in results["related_questions"]:
    print(f"Question: {question['question']}")
    print(f"Snippet: {question['snippet']}")
    print(f"Link: {question['link']}\n")

# Iterate over Inline Images
print("Inline Images:")
for image in results["inline_images"]:
    print(f"Title: {image['title']}")
    print(f"Image Link: {image['link']}")
    print(f"Thumbnail: {image['thumbnail']}\n")

# Iterate over Local Results
print("Local Results:")
for place in results["local_results"]["places"]:
    print(f"Position: {place['position']}")
    print(f"Title: {place['title']}")
    print(f"Address: {place['address']}\n")