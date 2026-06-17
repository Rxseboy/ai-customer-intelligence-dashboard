from fastapi import APIRouter, HTTPException, Depends, Request
from src.back_end.api.schemas.contracts import RAGQueryRequest, RAGQueryResponse
from src.back_end.api.dependencies import get_api_key
from src.back_end.api.services.model_cache import ModelCache

router = APIRouter(prefix="/insights", tags=["AI Assistant"])
_model_cache = ModelCache()

@router.post("/ask", response_model=RAGQueryResponse, dependencies=[Depends(get_api_key)])
def ask_insight(request: RAGQueryRequest, req: Request = None):
    rag = _model_cache.get_rag_assistant()
    if rag is None:
        raise HTTPException(
            status_code=503,
            detail="RAG Assistant tidak tersedia. Pastikan GROQ_API_KEY dan library langchain-groq sudah terpasang."
        )

    context_parts = []
    if request.d_from and request.d_to:
        context_parts.append(f"Hanya analisis data transaksi dari tanggal {request.d_from} sampai {request.d_to}.")
    if request.segments:
        segs_joined = ', '.join(request.segments)
        context_parts.append(f"Hanya analisis customer yang termasuk dalam segment RFM berikut: {segs_joined}.")
    
    ctx_str = " ".join(context_parts)
    
    result = rag.ask(request.question, language=request.language, context_str=ctx_str)
    return RAGQueryResponse(
        answer=result.get("answer", ""),
        sql=result.get("sql"),
        cached=result.get("cached", False),
        error=result.get("error"),
    )

@router.get("/tables")
def get_rag_tables():
    rag = _model_cache.get_rag_assistant()
    if rag is None:
        raise HTTPException(status_code=503, detail="RAG Assistant tidak tersedia.")
    tables = rag.available_tables()
    return {"accessible_tables": tables, "total": len(tables)}

@router.post("/evaluate", dependencies=[Depends(get_api_key)])
def evaluate_rag(num_questions: int = 7):
    try:
        from src.back_end.ml.rag_eval import RAGEvaluator, GROUND_TRUTH
        rag       = _model_cache.get_rag_assistant()
        evaluator = RAGEvaluator(
            rag_assistant=rag,
            ground_truth=GROUND_TRUTH[:num_questions]
        )
        report = evaluator.run(verbose=False)
        return {
            "success": True,
            "summary": report["summary"],
            "details": report["details"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluasi gagal: {e}")
