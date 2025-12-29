import os
from dotenv import load_dotenv
import nest_asyncio
from bs4 import BeautifulSoup

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import RecursiveUrlLoader
#from langchain_community.document_loaders.sitemap import SitemapLoader


# Load environment variables from .env file
load_dotenv()

nest_asyncio.apply()

def extract_spring_boot_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Find the article with class "doc"
    article = soup.find('article', {'class': 'doc'})

    if article:
        # Remove breadcrumbs and pagination navigation
        for element in article.find_all(['nav']):
            element.decompose()

        # Also remove breadcrumbs-container div if you don't want it
        breadcrumbs = article.find('div', {'class': 'breadcrumbs-container'})
        if breadcrumbs:
            breadcrumbs.decompose()

        # Get clean text
        return article.get_text(separator='\n', strip=True)

    # Fallback if article not found
    return ""


def split_and_store_documents(sitemap_url: str):

    loader = RecursiveUrlLoader(
        url=sitemap_url,
        max_depth=3,
        extractor=extract_spring_boot_content,
        prevent_outside=True,
        # Remove link_regex to allow all links within the same domain
        # Or use a more permissive pattern that matches the domain
        #link_regex=r"https://docs\.spring\.io/spring-boot/.*",
        timeout=10
    )

    print("Loading Spring Boot 4 documentation pages...")
    documents = loader.load()
    print(f"Successfully loaded {len(documents)} pages.")

    # Just for testing
    for doc in documents:
        print(doc.metadata.get('source'))
        if(doc.metadata.get('source') == 'https://docs.spring.io/spring-boot/community.html'):
            print(doc.page_content)

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        chunk_size=1000
    )

    vector_store = Chroma(
        collection_name = "spring_boot_4_document_collection",
        embedding_function = embeddings,
        persist_directory = "../data/vector_store"
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # chunk size (characters)
        chunk_overlap=200,  # chunk overlap (characters)
        add_start_index=True,  # track index in original document
    )


    all_splits = text_splitter.split_documents(documents)

    print(f"Split blog post into {len(all_splits)} sub-documents.")

    # To load 5000 document at once to avoid chromaDB limitation of loading >5,461 documents at once.
    batch_size=5000
    # To store VectorIDs after adding documents to vector DB
    vector_ids = []
    for i in range(0, len(all_splits),batch_size):
        batch_docs = all_splits[i:i+batch_size]
        vec_ids = vector_store.add_documents(documents=batch_docs)
        vector_ids.extend(vec_ids)

    vect_id_range = vector_ids[:4]
    print(vect_id_range)


    
if __name__ == "__main__":
    print("Extracting relevant and required documents from Spring Boot 4 documentation...")
    sitemap_url = "https://docs.spring.io/spring-boot/index.html"
    split_and_store_documents(sitemap_url)
    print("Successfully extracted and stored documents.")
