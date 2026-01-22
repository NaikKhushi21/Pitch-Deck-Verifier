#!/usr/bin/env python3
"""
Flask Web Application for Sago Pitch Deck Verifier
"""
import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import threading
from pathlib import Path

from src.agent import SagoPitchVerifier
from src.models import InvestorProfile
from src.config import config

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['REPORTS_FOLDER'] = 'reports'

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

# Store analysis jobs
jobs = {}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start analysis"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    file.save(filepath)
    
    # Get optional parameters
    email = request.form.get('email', '').strip()
    investor_name = request.form.get('investor_name', config.investor_name)
    focus_areas = request.form.get('focus_areas', config.investor_focus_areas)
    investment_stage = request.form.get('investment_stage', config.investment_stage)
    
    # Initialize job status
    jobs[job_id] = {
        'status': 'processing',
        'progress': 0,
        'message': 'Starting analysis...',
        'filepath': filepath,
        'filename': filename,
        'email': email,
        'result': None,
        'error': None
    }
    
    # Start analysis in background thread
    thread = threading.Thread(
        target=process_analysis,
        args=(job_id, filepath, email, investor_name, focus_areas, investment_stage)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'message': 'Analysis started'
    })


def process_analysis(job_id, filepath, email, investor_name, focus_areas, investment_stage):
    """Process the pitch deck analysis in background"""
    try:
        jobs[job_id]['progress'] = 10
        jobs[job_id]['message'] = 'Initializing agent...'
        
        # Create investor profile
        investor_profile = InvestorProfile(
            name=investor_name,
            focus_areas=focus_areas.split(',') if focus_areas else config.investor_focus_areas.split(', '),
            investment_stage=investment_stage
        )
        
        # Initialize agent
        agent = SagoPitchVerifier(investor_profile=investor_profile)
        
        jobs[job_id]['progress'] = 20
        jobs[job_id]['message'] = 'Analyzing pitch deck...'
        
        # Run analysis
        analysis = agent.analyze(
            pdf_path=filepath,
            max_claims=25,
            max_questions=10
        )
        
        jobs[job_id]['progress'] = 80
        jobs[job_id]['message'] = 'Generating report...'
        
        # Generate report paths
        report_filename = f"{job_id}_report.pdf"
        report_path = os.path.join(app.config['REPORTS_FOLDER'], report_filename)
        html_path = os.path.join(app.config['REPORTS_FOLDER'], f"{job_id}_report.html")
        
        # Save HTML report using the same method as PDF/email (full detailed report)
        agent._save_full_html_report(analysis, html_path)
        
        # Generate PDF report from the same HTML
        try:
            from weasyprint import HTML
            HTML(html_path).write_pdf(report_path)
        except Exception as e:
            print(f"PDF generation error: {e}")
            report_path = None
        
        jobs[job_id]['progress'] = 100
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['message'] = 'Analysis complete!'
        jobs[job_id]['result'] = {
            'company_name': analysis.company_name,
            'verification_score': analysis.overall_verification_score,
            'num_claims': len(analysis.verified_claims),
            'num_questions': len(analysis.generated_questions),
            'report_path': report_path if report_path and os.path.exists(report_path) else None,
            'html_path': html_path
        }
        
        # Send email if provided
        if email:
            try:
                agent.send_via_email(analysis, email, analysis.company_name)
                jobs[job_id]['result']['email_sent'] = True
            except Exception as e:
                jobs[job_id]['result']['email_sent'] = False
                jobs[job_id]['result']['email_error'] = str(e)
        
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['message'] = f'Error: {str(e)}'
        import traceback
        traceback.print_exc()


@app.route('/status/<job_id>')
def get_status(job_id):
    """Get analysis job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    return jsonify({
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'result': job.get('result'),
        'error': job.get('error')
    })


@app.route('/download/<job_id>')
def download_report(job_id):
    """Download the analysis report"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Analysis not complete'}), 400
    
    report_path = job['result']['report_path']
    if not os.path.exists(report_path):
        return jsonify({'error': 'Report file not found'}), 404
    
    return send_file(
        report_path,
        as_attachment=True,
        download_name=f"{job['result']['company_name']}_Analysis_Report.pdf",
        mimetype='application/pdf'
    )


@app.route('/view/<job_id>')
def view_report(job_id):
    """View the HTML report"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Analysis not complete'}), 400
    
    html_path = job['result']['html_path']
    if not os.path.exists(html_path):
        return jsonify({'error': 'Report file not found'}), 404
    
    return send_file(html_path)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
