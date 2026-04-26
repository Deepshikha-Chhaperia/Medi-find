"""POST /api/search — main search endpoint."""
from fastapi import APIRouter
from models.search import SearchRequest, SearchResponse
from pipeline.query_pipeline import run_query

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    """
    Agentic search across all indexed facility documents.
    Runs: QueryDecomposer → Retrieval → Reranker → Synthesizer.
    """
    return run_query(request)
