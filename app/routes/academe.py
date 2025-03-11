from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, AcademeGraduateReport
from app.utils import get_user_data, exclude_fields, update_expired_job_postings, update_expired_training_postings, update_expired_scholarship_postings
from datetime import datetime, timedelta

auth = HTTPBasicAuth()

academe = Blueprint("academe", __name__)

@auth.verify_password
def verify_password(username_or_token, password):
    # Try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # If token authentication fails, try username/password authentication
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ACADEME GRADUATE REPORTS. POST, GET, PUT, DELETE
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Create a new graduate report
@academe.route('/add-graduate-reports', methods=['POST'])
@auth.login_required
def create_graduate_report():
    data = request.get_json()
    
    # Validate required fields
    required_fields = [
        'degree_or_qualification', 'education_level', 'field_of_study', 
        'year', 'number_of_enrollees', 'number_of_graduates', 
        'start_year', 'end_year'
    ]
    
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Create new graduate report
    new_report = AcademeGraduateReport(
        user_id=g.user.user_id,
        degree_or_qualification=data['degree_or_qualification'],
        education_level=data['education_level'],
        field_of_study=data['field_of_study'],
        major=data.get('major'),  # Optional field
        year=data['year'],
        number_of_enrollees=data['number_of_enrollees'],
        number_of_graduates=data['number_of_graduates'],
        start_year=data['start_year'],
        end_year=data['end_year']
    )
    
    db.session.add(new_report)
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Graduate report created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get all graduate reports
@academe.route('/get-graduate-reports', methods=['GET'])
@auth.login_required
def get_all_graduate_reports():
    reports = AcademeGraduateReport.query.filter_by(user_id=g.user.user_id).all()
    
    result = []
    for report in reports:
        # Convert SQLAlchemy model to dictionary
        report_dict = {
            'graduate_report_id': report.graduate_report_id,
            'user_id': report.user_id,
            'degree_or_qualification': report.degree_or_qualification,
            'education_level': report.education_level,
            'field_of_study': report.field_of_study,
            'major': report.major,
            'year': report.year,
            'number_of_enrollees': report.number_of_enrollees,
            'number_of_graduates': report.number_of_graduates,
            'start_year': report.start_year,
            'end_year': report.end_year,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'updated_at': report.updated_at.isoformat() if report.updated_at else None
        }
        result.append(report_dict)
    
    return jsonify({
        "success": True,
        'graduate_reports': result
        }), 200

@academe.route('/graduate-reports/<int:report_id>', methods=['PUT'])
@auth.login_required
def update_graduate_report(report_id):
    report = AcademeGraduateReport.query.filter_by(
        graduate_report_id=report_id, 
        user_id=g.user.user_id
    ).first()
    
    if not report:
        return jsonify({'error': 'Graduate report not found'}), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if 'degree_or_qualification' in data:
        report.degree_or_qualification = data['degree_or_qualification']
    if 'education_level' in data:
        report.education_level = data['education_level']
    if 'field_of_study' in data:
        report.field_of_study = data['field_of_study']
    if 'major' in data:
        report.major = data['major']
    if 'year' in data:
        report.year = data['year']
    if 'number_of_enrollees' in data:
        report.number_of_enrollees = data['number_of_enrollees']
    if 'number_of_graduates' in data:
        report.number_of_graduates = data['number_of_graduates']
    if 'start_year' in data:
        report.start_year = data['start_year']
    if 'end_year' in data:
        report.end_year = data['end_year']
    
    report.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            "sucess": True,
            'message': 'Graduate report updated successfully',
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Delete a specific graduate report
@academe.route('/graduate-reports/<int:report_id>', methods=['DELETE'])
@auth.login_required
def delete_graduate_report(report_id):
    report = AcademeGraduateReport.query.filter_by(
        graduate_report_id=report_id, 
        user_id=g.user.user_id
    ).first()
    
    if not report:
        return jsonify({'error': 'Graduate report not found'}), 404
    
    try:
        db.session.delete(report)
        db.session.commit()
        return jsonify({
            "suceess": True,
            'message': 'Graduate report deleted successfully'
            }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
            }), 500

# Get summary statistics for graduate reports
@academe.route('/graduate-reports/summary', methods=['GET'])
@auth.login_required
def get_graduate_reports_summary():
    # Get total number of reports
    total_reports = AcademeGraduateReport.query.filter_by(user_id=g.user.user_id).count()
    
    # Get summary by education level
    education_levels = db.session.query(
        AcademeGraduateReport.education_level,
        db.func.count(AcademeGraduateReport.graduate_report_id)
    ).filter_by(user_id=g.user.user_id).group_by(AcademeGraduateReport.education_level).all()
    
    education_level_summary = {level: count for level, count in education_levels}
    
    # Get summary by field of study
    fields_of_study = db.session.query(
        AcademeGraduateReport.field_of_study,
        db.func.count(AcademeGraduateReport.graduate_report_id)
    ).filter_by(user_id=g.user.user_id).group_by(AcademeGraduateReport.field_of_study).all()
    
    field_of_study_summary = {field: count for field, count in fields_of_study}
    
    # Get total enrollees and graduates
    totals = db.session.query(
        db.func.sum(AcademeGraduateReport.number_of_enrollees),
        db.func.sum(AcademeGraduateReport.number_of_graduates)
    ).filter_by(user_id=g.user.user_id).first()
    
    total_enrollees, total_graduates = totals
    
    return jsonify({
        'total_reports': total_reports,
        'education_level_summary': education_level_summary,
        'field_of_study_summary': field_of_study_summary,
        'total_enrollees': total_enrollees or 0,
        'total_graduates': total_graduates or 0,
        'graduation_rate': (total_graduates / total_enrollees * 100) if total_enrollees else 0
    }), 200
