from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

def compute_fit_score(resume_text, jd_text):
    resume_emb = model.encode(resume_text, convert_to_tensor=True)
    jd_emb = model.encode(jd_text, convert_to_tensor=True)
    score = util.cos_sim(resume_emb, jd_emb).item()

    # Optional: Extract some basic analysis
    match_details = {
        'summary': 'Your resume has been compared to the job description using Sentence-BERT',
        'tips': 'Include keywords and relevant experiences from the job description to improve your match score'
    }

    return score, match_details
