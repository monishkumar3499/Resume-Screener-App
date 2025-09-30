import re
from typing import Dict, List, Tuple, Set
import numpy as np
import shap
from sentence_transformers import SentenceTransformer, util

# Load a compact, fast model (already in your previous code)
_model_name = 'all-MiniLM-L6-v2'
model = SentenceTransformer(_model_name)

# -----------------------------
# Simple keyword extraction utils
# -----------------------------
_STOPWORDS = {
    # Articles
    "a", "an", "the",
    
    # Conjunctions
    "and", "or", "but", "if", "then", "than", "so", "because", "although", "though",
    
    # Pronouns (basic)
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    
    # Prepositions
    "in", "on", "for", "by", "at", "from", "to", "of", "with", "as", "about", "into", "onto", "over", "under", "between", "among",
    
    # Auxiliary verbs / modals
    "is", "are", "was", "were", "be", "been", "being", "can", "could", "shall", "should", "will", "would", "may", "might", "must", "do", "does", "did", "have", "has", "had",
    
    # Common small words
    "this", "that", "these", "those", "here", "there", "then", "again", "up", "down", "back", "forward"
}

_WORD_RE = re.compile(r"[A-Za-z0-9+#\-_/\.]+")

def _tokens(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())

def _extract_keywords(text: str, min_len: int = 3) -> Set[str]:
    kws = set()
    for w in _tokens(text):
        if len(w) >= min_len and w not in _STOPWORDS:
            kws.add(w)
    return kws

# -----------------------------
# SHAP explanation for similarity
# -----------------------------
def _predict_similarity(batch_texts: List[str], jd_text: str) -> np.ndarray:
    """
    Returns shape (N, 1) array of cosine similarities between each resume text in batch_texts and the jd_text.
    """
    embs_resume = model.encode(batch_texts, convert_to_tensor=True, normalize_embeddings=True)
    embs_jd = model.encode([jd_text] * len(batch_texts), convert_to_tensor=True, normalize_embeddings=True)
    # util.cos_sim yields (N, N) if both are lists; here both same length -> diagonal are what we want
    sims = util.cos_sim(embs_resume, embs_jd).cpu().numpy()
    # extract diagonal if square; otherwise it is already (N,1)
    if sims.ndim == 2 and sims.shape[0] == sims.shape[1]:
        sims = np.diag(sims).reshape(-1, 1)
    elif sims.ndim == 2 and sims.shape[1] == 1:
        pass
    else:
        sims = sims.reshape(-1, 1)
    return sims

def _shap_explain_resume_vs_jd(resume_text: str, jd_text: str, max_tokens: int = 220) -> Tuple[List[str], List[float]]:
    """
    Uses SHAP to attribute which tokens in the RESUME increased/decreased similarity to the JD.
    Returns tokens and their SHAP contribution values (positive => increases similarity).
    """
    # Word-level masker keeps things efficient and human-readable.
    masker = shap.maskers.Text(r"\W+")

    def predict_fn(batch_texts: List[str]) -> np.ndarray:
        return _predict_similarity(batch_texts, jd_text)

    # SHAP Explainer for text; link='identity' because output is similarity already in [-1,1]
    explainer = shap.Explainer(predict_fn, masker=masker, output_names=["similarity"])

    # Limit length for speed if extremely long
    if len(_tokens(resume_text)) > max_tokens:
        # Keep first ~max_tokens words; you can improve by selecting top sentences instead.
        words = _tokens(resume_text)
        truncated = " ".join(words[:max_tokens])
        shap_values = explainer([truncated])
    else:
        shap_values = explainer([resume_text])

    # Extract tokens and values
    tokens = list(shap_values.data[0])
    values = list(np.array(shap_values.values[0]).reshape(-1))

    return tokens, values

# -----------------------------
# Public API used by app.py
# -----------------------------
def compute_fit_score(resume_text: str, jd_text: str) -> Tuple[float, Dict]:
    """
    Computes:
      - cosine similarity score between resume and JD (Sentence-BERT)
      - matched keywords (intersection of JD and resume keywords)
      - missing keywords (JD keywords not present in resume)
      - SHAP token importance explaining the similarity decision
    Returns: (score, match_details)
    """
    # 1) Base similarity score
    emb_r = model.encode(resume_text, convert_to_tensor=True, normalize_embeddings=True)
    emb_j = model.encode(jd_text, convert_to_tensor=True, normalize_embeddings=True)
    score = float(util.cos_sim(emb_r, emb_j).item())  # scalar

    # 2) Simple keyword sets
    resume_kws = _extract_keywords(resume_text)
    jd_kws = _extract_keywords(jd_text)
    matched = sorted(list(resume_kws & jd_kws))
    missing = sorted(list(jd_kws - resume_kws))

    # 3) SHAP explanation
    tokens, shap_vals = _shap_explain_resume_vs_jd(resume_text, jd_text)

    # Aggregate token importance by normalized word form
    # (masker splits on non-word characters so tokens are word-like already)
    contrib: Dict[str, float] = {}
    for t, v in zip(tokens, shap_vals):
        w = t.strip().lower()
        if not w or w in _STOPWORDS:
            continue
        contrib[w] = contrib.get(w, 0.0) + float(v)

    # Rank top positive & negative contributors (helps UI)
    # Positive => boosts similarity; Negative => lowers similarity
    pos_tokens = sorted([(w, s) for w, s in contrib.items() if s > 0], key=lambda x: x[1], reverse=True)
    neg_tokens = sorted([(w, s) for w, s in contrib.items() if s < 0], key=lambda x: x[1])

    top_pos = pos_tokens[:20]
    top_neg = neg_tokens[:20]

    match_details = {
        "summary": "Compared resume and JD using Sentence-BERT similarity with SHAP token attributions.",
        "matched_keywords": matched,
        "missing_keywords": missing,
       # "top_positive_tokens": top_pos,  # list of (token, contribution)  #contribution display line
       # "top_negative_tokens": top_neg,  # list of (token, contribution)
    }
    return score, match_details
