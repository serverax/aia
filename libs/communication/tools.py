import httpx
from datetime import datetime
from services.analyst_agent.milvus_manager import MilvusManager

async def web_search(query: str, num_results: int = 10) -> list[dict]:
    """Search web using DuckDuckGo API."""
    print(f"Searching web for: {query}")
    async with httpx.AsyncClient() as client:
        # Note: Using DuckDuckGo's informal API as a placeholder
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json"},
            timeout=10
        )
        data = response.json()
        
        results = []
        # DuckDuckGo's API results structure varies, this is a simplification
        topics = data.get("RelatedTopics", [])
        for topic in topics[:num_results]:
            if "Text" in topic and "FirstURL" in topic:
                results.append({
                    "title": topic.get("Text")[:50] + "...",
                    "url": topic.get("FirstURL"),
                    "snippet": topic.get("Text"),
                    "retrieved_at": datetime.utcnow().isoformat()
                })
        return results

async def fetch_document(client_id: str, doc_id: str) -> str:
    """Retrieve document from client vault (Milvus placeholder)."""
    print(f"Fetching document {doc_id} for client {client_id}")
    # In a real implementation, this would query Milvus
    # For now, return a placeholder string
    return f"Content of document {doc_id} from client vault."

async def lookup_cvss_score(cve_id: str) -> dict:
    """Look up CVE severity score using NVD API."""
    print(f"Looking up CVSS for: {cve_id}")
    async with httpx.AsyncClient() as client:
        try:
            # Using NVD API v2
            response = await client.get(
                f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}",
                timeout=10
            )
            data = response.json()
            
            cve_items = data.get("vulnerabilities", [])
            if not cve_items:
                return {"error": "CVE not found"}
            
            cve_data = cve_items[0].get("cve", {})
            metrics = cve_data.get("metrics", {})
            # Prefer CVSS v3.1 if available
            cvss_v31 = metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {})
            
            return {
                "cve_id": cve_id,
                "cvss_score": cvss_v31.get("baseScore", "N/A"),
                "severity": cvss_v31.get("baseSeverity", "UNKNOWN"),
                "description": cve_data.get("descriptions", [{}])[0].get("value", "No description available.")
            }
        except Exception as e:
            return {"error": str(e)}
