import urllib.request
import base64
import zlib
import sys
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

mermaid_graph = """
graph TD
    subgraph 1. Data Ingestion
        A[Social Media] -->|Scrape| B(Raw Data)
        B -->|PII Removal| C{Cleaned Data}
        C -->|Extract| D[LLM Persona Extractor]
        D -->|Save| E[(Base Profile DB)]
    end

    subgraph 2. Memory Stream
        C -->|Embed| F[Vectorization]
        F --> G[(ChromaDB)]
        G -.->|Query Past| H{RAG Engine}
    end

    subgraph 3. Environment
        I((New Event)) --> J[Platform Hub]
        J -->|Broadcast| K{Agent Perception}
        L[Network Graph] -.->|Emotional Contagion| M[Dynamic State]
    end

    subgraph 4. Action Core
        E -->|Inject Profile| N[Prompt Builder]
        H -.->|Inject Memories| N
        M -->|Inject Emotion| N
        K -->|Pass Event| N
        
        N -->|Context Prompt| O[LLM API]
        O -->|JSON Output| P{Action Engine}
        P -->|1. Post| J
        P -->|2. Update Emotion| M
        P -->|3. Save Memory| F
    end
"""

compressed = zlib.compress(mermaid_graph.encode('utf-8'))
encoded = base64.urlsafe_b64encode(compressed).decode('utf-8')

url = f"https://kroki.io/mermaid/png/{encoded}"
output_path = sys.argv[1]

print(f"Downloading diagram from {url}")
urllib.request.urlretrieve(url, output_path)
print(f"Diagram saved to {output_path}")
