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
        resume_file = request.files['resume']
        jd_file = request.files.get('jd_file')
        jd_text = request.form.get('jd_text')
        job_title = request.form.get('job_title')

        if resume_file:
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(resume_file.filename))
            resume_file.save(resume_path)
            resume_text = extract_text_from_file(resume_path)
        else:
            resume_text = ""

        if jd_file and jd_file.filename != '':
            jd_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(jd_file.filename))
            jd_file.save(jd_path)
            jd_content = extract_text_from_file(jd_path)
        elif jd_text:
            jd_content = jd_text
        else:
            jd_content = ""

        if resume_text and jd_content:
            score, match_details = compute_fit_score(resume_text, jd_content)
            return render_template('result.html', score=round(score * 100, 2), details=match_details, job_title=job_title)
        else:
            return "Please upload both Resume and Job Description."

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
