import logging

from app.rag.faiss_store import faiss_store

logger = logging.getLogger("medintel")


class RAGPipeline:
    async def retrieve_context(
        self,
        query: str,
        user_id: int,
        top_k: int = 5,
        report_id: int | None = None,
    ) -> str:
        results = await faiss_store.search(query, user_id, top_k, report_id)
        if not results:
            return ""

        context_parts = ["=== Relevant Medical History ==="]
        for r in results:
            context_parts.append(
                f"[Report #{r['report_id']} | {r['chunk_type']}]\n{r['text']}"
            )
        return "\n\n".join(context_parts)

    async def index_report(
        self,
        text: str,
        user_id: int,
        report_id: int,
        chunk_size: int = 1000,
    ) -> None:
        from app.utils.auth import chunk_text

        chunks = chunk_text(text, chunk_size)
        if chunks:
            await faiss_store.add_documents(chunks, user_id, report_id)


rag_pipeline = RAGPipeline()
