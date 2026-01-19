# Retail Product Agent — Multimodal Product Discovery

**Find the perfect product by describing it—or just show a picture.**

An open-source, AI-powered conversational shopping assistant that lets users discover products through **natural language descriptions**, **uploaded images**, or **both at once**. No more endless scrolling through catalogs—get precise, relevant results instantly.

Imagine a user uploads a photo of a sweater or says:  
*"I'm looking for a cozy oversized sweater in earthy tones, like the one I saw on vacation"* 

The retail agent understands the text, the image, and/or their combined intent to return the closest matches from your product catalog.

This project brings cutting-edge multimodal AI to e-commerce search, making product discovery feel magical.

## Key Features

- **Multimodal Search**  
  Query with text, images, or both simultaneously. Powered by OpenCLIP for joint text-image embeddings and BLIP for automatic image captioning.

- **High-Precision Ranking**  
  Initial retrieval from a vector database, followed by CrossEncoder re-ranking for superior relevance.

- **Scalable Catalog Indexing**  
  Designed to handle 100K+ products efficiently with fast vector search and incremental updates to the index based on new inventory.
  
- **Conversational Interface**  
  Built via FastAPI and easy to integrate into web apps, mobile clients, or chatbots.

- **Open & Extensible**  
  Fully open-source, modular design. Swap models, add new data sources, or extend the API as needed.

## Tech Stack

- **Backend**: Python + FastAPI (async, lightweight, production-ready)
- **Embeddings**:
  - OpenCLIP (multimodal text + image embeddings)
  - BLIP (image auto-captioning for richer text representation)
- **Re-ranking**: CrossEncoder (transformer-based pairwise scoring)
- **Vector Database**: Qdrant (scalable, high-performance vector search)
- **Deployment**: Docker-ready, easy to run locally or scale in the cloud
