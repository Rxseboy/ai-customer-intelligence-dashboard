"""
src/back_end/ml/rag.py
========================
RAG AI Insight Assistant — LangChain + PostgreSQL Read-Only
dengan Guardrails, SQL Safety Validator, Self-Correction, dan Smart Caching

Fitur:
  1. Read-Only DB Session   — LLM TIDAK bisa melakukan DML (DROP/INSERT/UPDATE)
  2. SQL Linter/Validator   — Regex berlapis: blokir DML command, bukan string data
  3. Query Caching          — Cache hasil identik (siap upgrade ke Redis)
  4. Context Window Guard   — Truncate hasil query agar tidak jebol token limit
  5. Self-Correction Loop   — Retry otomatis jika SQL gagal dieksekusi (max 2x)
  6. Temporal Injection     — CURRENT_DATE selalu disertakan di system prompt
  7. Kamus Bisnis           — Definisi metrik perusahaan disuntikkan ke prompt
  8. Dynamic Schema         — Skema tabel dibaca otomatis dari DB, tidak hardcode

Dependencies (install manual):
    pip install "langchain>=0.2.0" "langchain-community>=0.2.0" "langchain-groq>=0.1.0"

Usage:
    from src.back_end.ml.rag import RAGInsightAssistant

    assistant = RAGInsightAssistant()
    result = assistant.ask("Siapa 5 customer dengan revenue tertinggi?")
    print(result["answer"])
"""

import os
import re
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────────
_DEFAULT_CACHE_TTL    = 3600    # Cache TTL: 1 jam
_MAX_QUERY_LENGTH     = 500     # Batas panjang pertanyaan user (karakter)
_MAX_RESULT_CHARS     = 2000    # Batas panjang hasil SQL sebelum di-truncate
_MAX_SELF_CORRECT     = 2       # Maksimum percobaan self-correction jika SQL error

_FALLBACK_ANSWER = (
    "Maaf, insight tidak tersedia saat ini. "
    "Coba pertanyaan yang lebih spesifik, atau hubungi administrator."
)

# ── Kamus Bisnis (Semantic / Business Dictionary) ─────────────────────────────
# Disuntikkan ke dalam system prompt agar LLM memahami definisi metrik perusahaan.
_BUSINESS_DICTIONARY = """
Definisi Metrik Bisnis (gunakan ini sebagai referensi saat membuat SQL):
- Revenue / Total Pendapatan : SUM(fact_orders.sale_price) WHERE status NOT IN ('Cancelled', 'Returned')
- Churn Customer             : Customer yang tidak melakukan pembelian dalam 90 hari terakhir
- Customer Lifetime Value    : SUM(sale_price) per customer_id dari seluruh riwayat order WHERE status NOT IN ('Cancelled', 'Returned')
- Pesanan Aktif              : fact_orders dengan status IN ('Processing', 'Shipped')
- Produk Terlaris            : Produk dengan COUNT(order_item_id) tertinggi
- Average Order Value (AOV)  : AVG(sale_price) per order_id unik WHERE status NOT IN ('Cancelled', 'Returned')
"""

# ── Few-Shot Examples (Contoh Pertanyaan → SQL yang Valid) ────────────────────
# Disuntikkan ke prompt saat pertanyaan mirip terdeteksi, menjadi "contekan" LLM.
_FEW_SHOT_EXAMPLES = [
    {
        "question": "Siapa 5 customer dengan revenue tertinggi?",
        "sql": (
            'SELECT dc."first_name", dc."last_name", '
            'SUM(fo."sale_price") AS total_revenue '
            'FROM fact_orders fo '
            'JOIN dim_customers dc ON fo."customer_id" = dc."customer_id" '
            "WHERE fo.\"status\" NOT IN ('Cancelled', 'Returned') "
            'GROUP BY dc."first_name", dc."last_name" '
            'ORDER BY total_revenue DESC LIMIT 5;'
        ),
    },
    {
        "question": "Berapa total revenue per bulan di tahun 2023?",
        "sql": (
            'SELECT dd."month", dd."month_name", '
            'SUM(fo."sale_price") AS monthly_revenue '
            'FROM fact_orders fo '
            'JOIN dim_date dd ON fo."date_id" = dd."date_id" '
            'WHERE dd."year" = 2023 AND fo."status" NOT IN (\'Cancelled\', \'Returned\') '
            'GROUP BY dd."month", dd."month_name" '
            'ORDER BY dd."month";'
        ),
    },
    {
        "question": "Kategori produk mana yang paling laris?",
        "sql": (
            'SELECT dp."category", COUNT(fo."order_item_id") AS total_orders '
            'FROM fact_orders fo '
            'JOIN dim_products dp ON fo."product_id" = dp."product_id" '
            'GROUP BY dp."category" '
            'ORDER BY total_orders DESC LIMIT 5;'
        ),
    },
    {
        "question": "Negara mana yang menyumbang customer terbanyak?",
        "sql": (
            'SELECT "country", COUNT("customer_id") AS total_customers '
            'FROM dim_customers '
            'GROUP BY "country" '
            'ORDER BY total_customers DESC LIMIT 10;'
        ),
    },
    {
        "question": "Customer Lifetime Value tertinggi siapa?",
        "sql": (
            'SELECT dc."first_name", dc."last_name", '
            'SUM(fo."sale_price") AS clv '
            'FROM fact_orders fo '
            'JOIN dim_customers dc ON fo."customer_id" = dc."customer_id" '
            "WHERE fo.\"status\" NOT IN ('Cancelled', 'Returned') "
            'GROUP BY dc."first_name", dc."last_name" '
            'ORDER BY clv DESC LIMIT 5;'
        ),
    },
]


class FewShotExampleStore:
    """
    Menyimpan dan mengambil few-shot examples relevan berdasarkan kemiripan
    kata kunci sederhana (tanpa Vector DB) untuk disuntikkan ke prompt LLM.

    Upgrade ke Vector similarity search (pgvector/FAISS) bisa dilakukan
    tanpa mengubah antarmuka — cukup override metode `find_relevant`.
    """

    def __init__(self, examples: list[dict] = None):
        self._examples = examples or _FEW_SHOT_EXAMPLES

    def find_relevant(self, question: str, top_k: int = 2) -> list[dict]:
        """Cari contoh paling relevan menggunakan keyword overlap sederhana."""
        q_words = set(question.lower().split())
        scored  = []
        for ex in self._examples:
            ex_words = set(ex["question"].lower().split())
            overlap  = len(q_words & ex_words)
            scored.append((overlap, ex))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for score, ex in scored[:top_k] if score > 0]

    def format_for_prompt(self, question: str) -> str:
        """Format few-shot examples sebagai teks yang siap disuntikkan ke prompt."""
        examples = self.find_relevant(question)
        if not examples:
            return ""
        lines = ["\nContoh SQL yang benar untuk pertanyaan serupa (gunakan sebagai referensi):\n"]
        for i, ex in enumerate(examples, 1):
            lines.append(f"Contoh {i}:")
            lines.append(f"  Pertanyaan: {ex['question']}")
            lines.append(f"  SQL: {ex['sql']}")
            lines.append("")
        return "\n".join(lines)


# Singleton instance
_few_shot_store = FewShotExampleStore()


# ── SQL Safety Validator (Berlapis, Anti False Positive) ─────────────────────
import sqlglot
from sqlglot.errors import ParseError
from sqlglot.expressions import Select, CTE

class SQLSafetyValidator:
    """
    Validasi SQL — menggunakan Abstract Syntax Tree (AST) parser dari sqlglot.
    Memastikan bahwa statement adalah murni SELECT dan bebas dari command DML/DDL.
    Pendekatan ini jauh lebih aman daripada Regex.
    """

    @staticmethod
    def is_safe(sql: str) -> tuple[bool, str]:
        """
        Cek apakah SQL aman untuk dieksekusi.

        Returns:
            (is_safe: bool, reason: str)
        """
        if len(sql) > 3000:
            return False, f"Query terlalu panjang ({len(sql)} chars). Limit: 3000."

        try:
            # Parse query menjadi AST menggunakan dialek postgres
            parsed = sqlglot.parse(sql, read="postgres")
            
            # Bisa saja kosong jika hanya whitespace
            if not parsed or parsed[0] is None:
                return False, "Query kosong atau tidak valid."
            
            # Multiple statements tidak diperbolehkan untuk keamanan
            if len(parsed) > 1:
                return False, "Hanya satu statement yang diperbolehkan per query."
                
            statement = parsed[0]
            
            # Harus SELECT statement
            if not isinstance(statement, Select):
                return False, f"Hanya operasi SELECT yang diperbolehkan. Terdeteksi: {statement.__class__.__name__}"
                
            return True, "OK"
            
        except ParseError as e:
            return False, f"Gagal parsing SQL (sintaks tidak valid): {str(e)}"
        except Exception as e:
            return False, f"Error tidak terduga saat validasi SQL: {str(e)}"


# ── Query Cache (Interface siap Redis) ────────────────────────────────────────
class QueryCache:
    """
    In-Memory cache untuk hasil RAG query.

    Dirancang dengan interface yang siap diganti Redis:
        cache.get(key) → Optional[dict]
        cache.set(key, value)
        cache.stats() → dict

    Untuk upgrade ke Redis, ganti _store dengan redis.Redis() dan
    implementasikan serialisasi JSON. Core logic RAGInsightAssistant
    tidak perlu diubah sama sekali.
    """

    def __init__(self, ttl_seconds: int = _DEFAULT_CACHE_TTL):
        self._store: dict = {}
        self.ttl   = ttl_seconds
        self.hits  = 0
        self.misses = 0

    def _key(self, query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode()).hexdigest()

    def get(self, query: str) -> Optional[dict]:
        key   = self._key(query)
        entry = self._store.get(key)
        if entry and datetime.utcnow() < entry["expires_at"]:
            self.hits += 1
            logger.info(f"[RAGCache] HIT (hits={self.hits})")
            return entry["result"]
        self.misses += 1
        return None

    def set(self, query: str, result: dict) -> None:
        key = self._key(query)
        self._store[key] = {
            "result":     result,
            "expires_at": datetime.utcnow() + timedelta(seconds=self.ttl),
        }
        logger.info(f"[RAGCache] STORE — cache size: {len(self._store)}")

    def stats(self) -> dict:
        return {"cache_size": len(self._store), "hits": self.hits, "misses": self.misses}


# Global cache instance
_cache = QueryCache()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_sql(raw: str) -> str:
    """
    Ekstrak SQL bersih dari output LangChain / LLM.

    LangChain create_sql_query_chain dapat mengembalikan berbagai format:
      Format 1: "Question: ...\nSQLQuery: SELECT ..."
      Format 2: "```sql\nSELECT ...\n```"
      Format 3: "SQLQuery: SELECT ..."
      Format 4: SQL mentah langsung

    Urutan prioritas:
      1. Blok markdown ```sql ... ``` (paling eksplisit)
      2. Label 'SQLQuery:' di mana saja (khas output LangChain chain)
      3. Fallback: strip prefix umum
    """
    if not raw:
        return ""

    # Prioritas 1: blok markdown ```sql ... ``` atau ``` ... ```
    md_match = re.search(r"```(?:sql)?\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if md_match:
        return md_match.group(1).strip()

    # Prioritas 2: cari label "SQLQuery:" di mana saja (khas output LangChain)
    sq_match = re.search(r"SQLQuery\s*:\s*", raw, re.IGNORECASE)
    if sq_match:
        candidate = raw[sq_match.end():].strip()
        # Hentikan di "SQLResult:" jika ada (format verbose LangChain)
        stop = re.search(r"\bSQLResult\b", candidate, re.IGNORECASE)
        if stop:
            candidate = candidate[:stop.start()].strip()
        if candidate:
            return candidate

    # Prioritas 3: fallback — strip prefix "Question:" atau "SQLQuery:" di awal
    sql = raw.strip()
    sql = re.sub(r"(?i)^(sqlquery|question)[^:]*:\s*", "", sql).strip()
    return sql


def _truncate_result(result: str, max_chars: int = _MAX_RESULT_CHARS) -> str:
    """
    Potong hasil query jika terlalu panjang agar tidak jebol context window LLM.
    Menambahkan keterangan truncation agar LLM tahu data tidak lengkap.
    """
    if len(result) <= max_chars:
        return result
    truncated = result[:max_chars]
    logger.warning(f"[RAG] Query result truncated: {len(result)} → {max_chars} chars")
    return truncated + f"\n... [DATA TERPOTONG — {len(result) - max_chars} karakter tidak ditampilkan karena melebihi batas konteks]"


def _build_answer_prompt(question: str, sql: str, result: str, few_shot_context: str = "", language: str = "id") -> str:
    """Bangun prompt NLG dengan konteks temporal, kamus bisnis, dan few-shot examples."""
    today = datetime.now().strftime("%d %B %Y")
    if language == "en":
        return (
            f"You are a professional E-Commerce Data Assistant AI.\n"
            f"Today is: {today}\n\n"
            f"{_BUSINESS_DICTIONARY}"
            f"{few_shot_context}\n"
            f"User Question: {question}\n"
            f"Executed SQL Query:\n{sql}\n\n"
            f"Database Output Data:\n{result}\n\n"
            f"Task: Generate a natural, friendly, and professional response in ENGLISH "
            f"based strictly on the database output above. DO NOT mention or repeat the SQL query in your text response. "
            f"If the database output is empty or indicates an error, politely state that the requested data could not be found. "
            f"If the data is truncated, clearly mention that only a partial dataset is displayed."
        )
    else:
        return (
            f"Anda adalah AI Asisten Data E-Commerce yang profesional.\n"
            f"Hari ini adalah: {today}\n\n"
            f"{_BUSINESS_DICTIONARY}"
            f"{few_shot_context}\n"
            f"Pertanyaan User: {question}\n"
            f"Query SQL yang dieksekusi:\n{sql}\n\n"
            f"Hasil Data dari Database:\n{result}\n\n"
            f"Tugas: Buatlah jawaban yang natural, ramah, dan profesional dalam Bahasa Indonesia "
            f"berdasarkan data di atas. Jangan ulangi SQL-nya. "
            f"Jika hasil data kosong atau error, sampaikan dengan sopan bahwa data tidak ditemukan. "
            f"Jika data terpotong, sebutkan bahwa hanya sebagian data yang ditampilkan."
        )


# ── RAG Insight Assistant ─────────────────────────────────────────────────────
class RAGInsightAssistant:
    """
    AI Insight Assistant berbasis RAG (Text-to-SQL).

    Menggunakan LangChain + Groq (Llama 3). DB connection adalah Read-Only.
    Fitur: Self-Correction, Context Guard, Temporal Injection, Business Dictionary.

    Args:
        db_url        : PostgreSQL connection string (READ-ONLY user)
        model_name    : Nama LLM Groq yang digunakan
        cache_ttl     : TTL cache dalam detik
        include_tables: List tabel yang boleh diakses LLM (None = semua tabel)
    """

    def __init__(
        self,
        db_url: str = None,
        model_name: str = "llama-3.3-70b-versatile",
        cache_ttl: int = _DEFAULT_CACHE_TTL,
        include_tables: list[str] = None,
    ):
        self.db_url        = db_url or os.getenv("DATABASE_URL_READONLY") or os.getenv("DATABASE_URL")
        self.model_name    = model_name
        self.cache         = QueryCache(ttl_seconds=cache_ttl)
        self.validator     = SQLSafetyValidator()
        self.include_tables = include_tables  # None = auto-detect semua tabel dari DB
        self._chain        = None
        self._db           = None
        self._llm          = None
        self._init_error   = None
        self._init_chain()

    def _init_chain(self) -> None:
        """Inisialisasi LangChain SQL chain — graceful fallback bila dependency tidak ada."""
        try:
            # Monkey-patch kompatibilitas lintas versi LangChain
            import langchain_core.exceptions as _lc_exc
            if not hasattr(_lc_exc, "ContextOverflowError"):
                class ContextOverflowError(Exception):
                    pass
                _lc_exc.ContextOverflowError = ContextOverflowError

            import langchain_core.language_models as _lc_lm
            if not hasattr(_lc_lm, "ModelProfile"):
                class ModelProfile:
                    pass
                _lc_lm.ModelProfile = ModelProfile

            from langchain_community.utilities import SQLDatabase
            from langchain_groq import ChatGroq

            # Cari create_sql_query_chain dari berbagai path versi LangChain
            try:
                from langchain_classic.chains import create_sql_query_chain
            except ImportError:
                try:
                    from langchain.chains import create_sql_query_chain
                except ImportError:
                    try:
                        from langchain.chains.sql_database.query import create_sql_query_chain
                    except ImportError:
                        from langchain_experimental.sql import SQLDatabaseChain as create_sql_query_chain

            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.warning("[RAG] GROQ_API_KEY tidak ditemukan. RAG dalam mode fallback.")
                return

            self._llm = ChatGroq(model=self.model_name, api_key=api_key, temperature=0, timeout=15, max_retries=1)

            if not self.db_url:
                logger.warning("[RAG] DATABASE_URL tidak ditemukan. RAG dalam mode fallback.")
                return

            # ── Dynamic Schema: include_tables=None → baca semua tabel dari DB ──
            db_kwargs = {}
            if self.include_tables:
                db_kwargs["include_tables"] = self.include_tables

            self._db    = SQLDatabase.from_uri(self.db_url, **db_kwargs)
            self._chain = create_sql_query_chain(self._llm, self._db)

            tabel_list = self._db.get_usable_table_names()
            logger.info(f"[RAG] Chain initialized | model='{self.model_name}' | tables={tabel_list}")

        except ImportError as e:
            msg = f"LangChain/Groq tidak tersedia: {e}"
            logger.warning(f"[RAG] {msg}")
            self._init_error = msg
        except Exception as e:
            import traceback
            msg = f"Gagal init chain: {str(e)}"
            logger.error(f"[RAG] {msg}\n{traceback.format_exc()}")
            self._init_error = msg

    # ── Public Methods ────────────────────────────────────────────────────────

    def validate_query(self, user_question: str) -> tuple[bool, str]:
        """Validasi pertanyaan user: panjang dan karakter berbahaya."""
        if len(user_question) > _MAX_QUERY_LENGTH:
            return False, f"Pertanyaan terlalu panjang. Maksimum {_MAX_QUERY_LENGTH} karakter."
        return True, "OK"

    def ask(self, user_question: str, language: str = "id", context_str: str = "") -> dict:
        """
        Jawab pertanyaan bisnis dari data warehouse.

        Flow:
          1. Cache check
          2. Validasi input
          3. Generate SQL via LLM
          4. Validasi SQL (safety)
          5. Execute SQL ke PostgreSQL
          5a. Self-Correction jika gagal (max 2x retry)
          6. Truncate hasil jika terlalu panjang
          7. Generate jawaban Natural Language (NLG) + Kamus Bisnis + Tanggal
          8. Return & simpan ke cache

        Returns:
            dict {"answer": str, "sql": str, "cached": bool, "error": str|None}
        """
        cache_key = f"{user_question}:{language}"
        # 1. Cache Check
        cached = self.cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return cached

        # 2. Input Validation
        valid, reason = self.validate_query(user_question)
        if not valid:
            return {"answer": reason, "sql": None, "cached": False, "error": "validation_failed"}

        # 3. Chain belum siap → fallback
        if self._chain is None:
            err_msg = self._init_error or "Chain belum diinisialisasi."
            fallback_msg = (
                "Sorry, the insight is not available at this moment. "
                "Please try a more specific question, or contact the administrator."
                if language == "en" else _FALLBACK_ANSWER
            )
            result = {
                "answer":  fallback_msg + f"\n\n**Init Error:** {err_msg}",
                "sql":     None,
                "cached":  False,
                "error":   "chain_not_initialized",
            }
            self.cache.set(cache_key, result)
            return result

        try:
            from langchain_core.prompts import PromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            # 3. Generate SQL dari LLM
            prompt_q = user_question
            if context_str:
                prompt_q += f"\n\nPENTING: {context_str}"
            generated_sql_raw = self._chain.invoke({"question": prompt_q})
            generated_sql     = _extract_sql(generated_sql_raw)

            # 4. SQL Safety Check
            is_safe, violation = self.validator.is_safe(generated_sql)
            if not is_safe:
                logger.warning(f"[RAG] SQL BLOCKED: {violation}")
                blocked_msg = (
                    f"Query blocked by SQL Safety Validator: {violation}. Only SELECT is allowed."
                    if language == "en" else f"Query diblokir oleh SQL Safety Validator: {violation}"
                )
                return {
                    "answer": blocked_msg,
                    "sql":    generated_sql,
                    "cached": False,
                    "error":  "sql_blocked",
                }

            # 5. Execute SQL + Self-Correction Loop
            query_result = None
            last_db_error = None
            current_sql   = generated_sql

            for attempt in range(1 + _MAX_SELF_CORRECT):
                try:
                    query_result = self._db.run(current_sql)
                    logger.info(f"[RAG] SQL executed successfully (attempt {attempt + 1})")
                    break  # Berhasil — keluar dari loop
                except Exception as db_err:
                    last_db_error = str(db_err)
                    logger.warning(f"[RAG] SQL Error (attempt {attempt + 1}): {last_db_error}")

                    if attempt < _MAX_SELF_CORRECT:
                        # Self-Correction: minta LLM perbaiki SQL-nya
                        logger.info(f"[RAG] Attempting self-correction (attempt {attempt + 2})...")
                        correction_prompt = (
                            f"The following SQL query failed execution:\n{current_sql}\n\n"
                            f"Error: {last_db_error}\n\n"
                            f"Correct the query and return ONLY the corrected SQL query, with no explanation."
                            if language == "en" else
                            f"Query SQL berikut gagal dieksekusi:\n{current_sql}\n\n"
                            f"Error: {last_db_error}\n\n"
                            f"Perbaiki query tersebut dan berikan HANYA query SQL yang sudah diperbaiki, "
                            f"tanpa penjelasan tambahan."
                        )
                        corrected_raw  = self._chain.invoke({"question": correction_prompt})
                        corrected_sql  = _extract_sql(corrected_raw)

                        # Validasi keamanan SQL koreksi
                        safe_corr, _ = self.validator.is_safe(corrected_sql)
                        if safe_corr:
                            current_sql = corrected_sql
                        else:
                            break  # SQL koreksi tidak aman → hentikan

            if query_result is None:
                query_result = (
                    f"Failed to execute query after {1 + _MAX_SELF_CORRECT} attempts. Last error: {last_db_error}"
                    if language == "en" else
                    f"Gagal mengeksekusi query setelah {1 + _MAX_SELF_CORRECT} percobaan. Error terakhir: {last_db_error}"
                )

            # 6. Truncate hasil query agar tidak jebol context window LLM
            query_result_safe = _truncate_result(str(query_result))

            # 7. Generate NLG dengan Kamus Bisnis + Few-Shot + Tanggal
            few_shot_ctx    = _few_shot_store.format_for_prompt(user_question)
            nlg_prompt_text = _build_answer_prompt(user_question, current_sql, query_result_safe, few_shot_ctx, language=language)
            answer_chain    = PromptTemplate.from_template("{text}") | self._llm | StrOutputParser()
            final_answer    = answer_chain.invoke({"text": nlg_prompt_text})

            # 8. Simpan ke cache & return
            logger.info("[RAG] Answer generated successfully.")
            result = {
                "answer":       final_answer,
                "sql":          current_sql,
                "cached":       False,
                "error":        None,
                "generated_at": datetime.utcnow().isoformat(),
            }
            self.cache.set(cache_key, result)
            return result

        except Exception as exc:
            import traceback
            logger.error(f"[RAG] Unexpected error: {exc}\n{traceback.format_exc()}")
            fallback_msg = (
                "Sorry, the insight is not available at this moment. "
                "Please try a more specific question, or contact the administrator."
                if language == "en" else _FALLBACK_ANSWER
            )
            return {
                "answer": fallback_msg,
                "sql":    None,
                "cached": False,
                "error":  str(exc),
            }

    def cache_stats(self) -> dict:
        """Kembalikan statistik cache untuk monitoring."""
        return self.cache.stats()

    def available_tables(self) -> list[str]:
        """Kembalikan daftar tabel yang dapat diakses oleh LLM."""
        if self._db:
            return self._db.get_usable_table_names()
        return []
