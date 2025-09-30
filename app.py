from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
import os
from utils.parser import extract_text_from_file
from utils.scorer import compute_fit_score

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'app/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        resume_file = request.files.get('resume')
        jd_file = request.files.get('jd_file')
        jd_text = request.form.get('jd_text', '').strip()
        job_title = request.form.get('job_title', '').strip()

        # --- Resume text ---
        resume_text = ""
        if resume_file and resume_file.filename:
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(resume_file.filename))
            resume_file.save(resume_path)
            resume_text = extract_text_from_file(resume_path)

        # --- JD text ---
        if jd_file and jd_file.filename:
            jd_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(jd_file.filename))
            jd_file.save(jd_path)
            jd_content = extract_text_from_file(jd_path)
        else:
            jd_content = jd_text

        if resume_text and jd_content:
            score, match_details = compute_fit_score(resume_text, jd_content)
            # If you have templates, this will render nicely.
            # Otherwise, you can return JSON or a simple string for quick testing.
            try:
                return render_template(
                    'result.html',
                    score=round(score * 100, 2),
                    details=match_details,
                    job_title=job_title
                )
            except Exception:
                # Fallback plain text if templates are not set up
                return {
                    "score_percent": round(score * 100, 2),
                    **match_details
                }
        else:
            return "Please upload both Resume and Job Description or paste the JD text."

    return render_template('index.html') if os.path.exists('templates/index.html') else "Upload a resume and JD to begin."


if __name__ == '__main__':
    # Set host/port as you like. debug=True for development only.
    app.run(debug=True)
