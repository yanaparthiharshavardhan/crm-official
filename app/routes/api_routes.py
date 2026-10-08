import jwt
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_user, logout_user
from app.models import (
    db, User, Role, Customer, Lead, LeadStatus, Opportunity, OpportunityStage, 
    OpportunityStatus, FollowUp, FollowUpStatus, AuditAction
)
from app.services.crm_service import CRMService
from app.services.report_service import ReportService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

api_bp = Blueprint('api', __name__, url_prefix='/api')

def generate_jwt_token(user):
    payload = {
        'sub': user.id,
        'email': user.email,
        'role': user.role,
        'name': user.name,
        'exp': datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def api_auth_required(f):
    """Authenticates API via either existing session or Bearer JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. Check Flask session
        if current_user and current_user.is_authenticated:
            request.api_user = current_user
            return f(*args, **kwargs)

        # 2. Check Authorization Header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized', 'message': 'Authentication token or session required.'}), 401

        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(payload['sub'])
            if not user or not user.is_active:
                return jsonify({'error': 'Unauthorized', 'message': 'User account inactive or not found.'}), 401
            request.api_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Unauthorized', 'message': 'Token has expired.'}), 401
        except Exception:
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid token.'}), 401

        return f(*args, **kwargs)
    return decorated

# ----------------------------------------------------
# Auth API Endpoints
# ----------------------------------------------------
@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Bad Request', 'message': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        if not user.is_active:
            return jsonify({'error': 'Forbidden', 'message': 'Account is deactivated.'}), 403
        if user.is_locked_out:
            return jsonify({'error': 'Locked', 'message': 'Account is temporarily locked.'}), 423
        if user.check_password(password):
            AuthService.handle_successful_login(user)
            token = generate_jwt_token(user)
            return jsonify({
                'message': 'Login successful',
                'token': token,
                'user': user.to_dict()
            }), 200
        else:
            locked, msg = AuthService.handle_failed_login(user, email)
            return jsonify({'error': 'Unauthorized', 'message': msg}), 401
    else:
        AuthService.handle_failed_login(None, email)
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid email or password.'}), 401

@api_bp.route('/auth/logout', methods=['POST'])
@api_auth_required
def api_logout():
    user = request.api_user
    AuditService.log(
        action=AuditAction.LOGOUT,
        entity_name='Auth',
        record_id=user.id,
        details=f"API User {user.email} logged out.",
        user_id=user.id
    )
    return jsonify({'message': 'Logged out successfully.'}), 200

# ----------------------------------------------------
# Customers API
# ----------------------------------------------------
@api_bp.route('/customers', methods=['GET'])
@api_auth_required
def get_customers():
    user = request.api_user
    search = request.args.get('search', '').strip()
    query = CRMService.get_scoped_customers(user)
    if search:
        s = f"%{search}%"
        query = query.filter(
            Customer.customer_name.ilike(s) | Customer.email.ilike(s) | 
            Customer.company_name.ilike(s) | Customer.customer_code.ilike(s)
        )
    customers = query.order_by(Customer.created_date.desc()).all()
    return jsonify([c.to_dict() for c in customers]), 200

@api_bp.route('/customers/<int:id>', methods=['GET'])
@api_auth_required
def get_customer(id):
    user = request.api_user
    customer = Customer.query.get(id)
    if not customer:
        return jsonify({'error': 'Not Found', 'message': 'Customer not found.'}), 404
    if user.is_sales_executive and customer.owner_id != user.id:
        return jsonify({'error': 'Forbidden', 'message': 'Access denied to this record.'}), 403
    return jsonify(customer.to_dict()), 200

@api_bp.route('/customers', methods=['POST'])
@api_auth_required
def create_customer():
    user = request.api_user
    data = request.get_json() or {}

    name = data.get('customer_name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    company = data.get('company_name', '').strip()

    if not name or not email or not phone or not company:
        return jsonify({'error': 'Bad Request', 'message': 'Customer name, email, phone, and company name are required.'}), 400

    # Duplicate check
    is_unique, err_msg = CRMService.check_duplicate_customer(email, phone)
    if not is_unique:
        return jsonify({'error': 'Conflict', 'message': err_msg}), 409

    owner_id = data.get('owner_id')
    if user.is_sales_executive:
        owner_id = user.id

    customer = Customer(
        customer_code=CRMService.generate_customer_code(),
        customer_name=name,
        email=email,
        phone=phone,
        company_name=company,
        address=data.get('address'),
        city=data.get('city'),
        state=data.get('state'),
        status=data.get('status', 'Active'),
        notes=data.get('notes'),
        owner_id=owner_id,
        created_by_id=user.id
    )
    db.session.add(customer)
    db.session.commit()

    AuditService.log(
        action=AuditAction.CREATE,
        entity_name='Customer',
        record_id=customer.id,
        new_value=customer.to_dict(),
        details=f"API: Created customer {customer.customer_code}",
        user_id=user.id
    )

    return jsonify(customer.to_dict()), 201

@api_bp.route('/customers/<int:id>', methods=['PUT'])
@api_auth_required
def update_customer(id):
    user = request.api_user
    customer = Customer.query.get(id)
    if not customer:
        return jsonify({'error': 'Not Found', 'message': 'Customer not found.'}), 404
    if user.is_sales_executive and customer.owner_id != user.id:
        return jsonify({'error': 'Forbidden', 'message': 'Access denied.'}), 403

    data = request.get_json() or {}
    email = data.get('email', customer.email).strip().lower()
    phone = data.get('phone', customer.phone).strip()

    is_unique, err_msg = CRMService.check_duplicate_customer(email, phone, exclude_id=customer.id)
    if not is_unique:
        return jsonify({'error': 'Conflict', 'message': err_msg}), 409

    old_val = customer.to_dict()
    if 'customer_name' in data: customer.customer_name = data['customer_name'].strip()
    if 'email' in data: customer.email = email
    if 'phone' in data: customer.phone = phone
    if 'company_name' in data: customer.company_name = data['company_name'].strip()
    if 'address' in data: customer.address = data['address']
    if 'city' in data: customer.city = data['city']
    if 'state' in data: customer.state = data['state']
    if 'status' in data: customer.status = data['status']
    if 'notes' in data: customer.notes = data['notes']
    if 'owner_id' in data and not user.is_sales_executive: customer.owner_id = data['owner_id']

    db.session.commit()

    AuditService.log(
        action=AuditAction.UPDATE,
        entity_name='Customer',
        record_id=customer.id,
        old_value=old_val,
        new_value=customer.to_dict(),
        details=f"API: Updated customer {customer.customer_code}",
        user_id=user.id
    )

    return jsonify(customer.to_dict()), 200

@api_bp.route('/customers/<int:id>', methods=['DELETE'])
@api_auth_required
def delete_customer(id):
    user = request.api_user
    customer = Customer.query.get(id)
    if not customer:
        return jsonify({'error': 'Not Found', 'message': 'Customer not found.'}), 404
    if user.is_sales_executive and customer.owner_id != user.id:
        return jsonify({'error': 'Forbidden', 'message': 'Access denied.'}), 403

    old_val = customer.to_dict()
    code = customer.customer_code
    db.session.delete(customer)
    db.session.commit()

    AuditService.log(
        action=AuditAction.DELETE,
        entity_name='Customer',
        record_id=id,
        old_value=old_val,
        details=f"API: Deleted customer {code}",
        user_id=user.id
    )

    return jsonify({'message': f'Customer {code} deleted successfully.'}), 200

# ----------------------------------------------------
# Leads API
# ----------------------------------------------------
@api_bp.route('/leads', methods=['GET'])
@api_auth_required
def get_leads():
    user = request.api_user
    leads = CRMService.get_scoped_leads(user).order_by(Lead.created_date.desc()).all()
    return jsonify([l.to_dict() for l in leads]), 200

@api_bp.route('/leads', methods=['POST'])
@api_auth_required
def create_lead():
    user = request.api_user
    data = request.get_json() or {}

    name = data.get('lead_name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    company = data.get('company_name', '').strip()

    if not name or not email or not phone or not company:
        return jsonify({'error': 'Bad Request', 'message': 'Lead name, email, phone, and company are required.'}), 400

    lead = Lead(
        lead_code=CRMService.generate_lead_code(),
        lead_name=name,
        email=email,
        phone=phone,
        company_name=company,
        source=data.get('source', 'Website'),
        status=data.get('status', LeadStatus.NEW),
        priority=data.get('priority', 'Medium'),
        expected_value=float(data.get('expected_value', 0.0)),
        notes=data.get('notes'),
        assigned_to_id=data.get('assigned_to_id') or (user.id if user.is_sales_executive else None)
    )
    db.session.add(lead)
    db.session.commit()

    AuditService.log(
        action=AuditAction.CREATE,
        entity_name='Lead',
        record_id=lead.id,
        new_value=lead.to_dict(),
        details=f"API: Created lead {lead.lead_code}",
        user_id=user.id
    )

    return jsonify(lead.to_dict()), 201

# ----------------------------------------------------
# Opportunities API
# ----------------------------------------------------
@api_bp.route('/opportunities', methods=['GET'])
@api_auth_required
def get_opportunities():
    user = request.api_user
    opps = CRMService.get_scoped_opportunities(user).order_by(Opportunity.created_date.desc()).all()
    return jsonify([o.to_dict() for o in opps]), 200

@api_bp.route('/opportunities', methods=['POST'])
@api_auth_required
def create_opportunity():
    user = request.api_user
    data = request.get_json() or {}

    name = data.get('opportunity_name', '').strip()
    cust_id = data.get('customer_id')
    amount = data.get('amount')
    prob = data.get('probability', 20)
    stage = data.get('stage', OpportunityStage.QUALIFICATION)
    close_date_str = data.get('expected_close_date')

    if not name or not cust_id or amount is None or not close_date_str:
        return jsonify({'error': 'Bad Request', 'message': 'Opportunity name, customer ID, amount, and close date are required.'}), 400

    try:
        amount = float(amount)
        prob = int(prob)
        close_date = datetime.strptime(close_date_str, '%Y-%m-%d').date()
    except Exception as e:
        return jsonify({'error': 'Bad Request', 'message': f'Invalid data format: {e}'}), 400

    # Business Validations
    is_valid, err_msg = CRMService.validate_opportunity(amount, prob, close_date, stage)
    if not is_valid:
        return jsonify({'error': 'Unprocessable Entity', 'message': err_msg}), 422

    status = OpportunityStatus.OPEN
    if stage == OpportunityStage.WON: status = OpportunityStatus.WON
    elif stage == OpportunityStage.LOST: status = OpportunityStatus.LOST

    opp = Opportunity(
        opportunity_code=CRMService.generate_opportunity_code(),
        opportunity_name=name,
        customer_id=cust_id,
        amount=amount,
        stage=stage,
        probability=prob,
        expected_close_date=close_date,
        status=status,
        source=data.get('source'),
        notes=data.get('notes'),
        assigned_to_id=data.get('assigned_to_id') or (user.id if user.is_sales_executive else None)
    )
    db.session.add(opp)
    db.session.commit()

    AuditService.log(
        action=AuditAction.CREATE,
        entity_name='Opportunity',
        record_id=opp.id,
        new_value=opp.to_dict(),
        details=f"API: Created opportunity {opp.opportunity_code}",
        user_id=user.id
    )

    return jsonify(opp.to_dict()), 201

# ----------------------------------------------------
# Follow-Ups API
# ----------------------------------------------------
@api_bp.route('/followups', methods=['GET'])
@api_auth_required
def get_followups():
    user = request.api_user
    followups = CRMService.get_scoped_followups(user).order_by(FollowUp.followup_date.asc()).all()
    return jsonify([f.to_dict() for f in followups]), 200

@api_bp.route('/followups', methods=['POST'])
@api_auth_required
def create_followup():
    user = request.api_user
    data = request.get_json() or {}

    subject = data.get('subject', '').strip()
    fu_date_str = data.get('followup_date')
    status = data.get('status', FollowUpStatus.PLANNED)

    if not subject or not fu_date_str:
        return jsonify({'error': 'Bad Request', 'message': 'Subject and follow-up date are required.'}), 400

    try:
        fu_date = datetime.strptime(fu_date_str, '%Y-%m-%d').date()
    except Exception as e:
        return jsonify({'error': 'Bad Request', 'message': f'Invalid date format: {e}'}), 400

    is_valid, err_msg = CRMService.validate_followup_date(fu_date, status)
    if not is_valid:
        return jsonify({'error': 'Unprocessable Entity', 'message': err_msg}), 422

    fu = FollowUp(
        subject=subject,
        followup_type=data.get('followup_type', 'Call'),
        followup_date=fu_date,
        status=status,
        remarks=data.get('remarks'),
        customer_id=data.get('customer_id'),
        lead_id=data.get('lead_id'),
        opportunity_id=data.get('opportunity_id'),
        assigned_to_id=data.get('assigned_to_id') or (user.id if user.is_sales_executive else None)
    )
    db.session.add(fu)
    db.session.commit()

    AuditService.log(
        action=AuditAction.CREATE,
        entity_name='FollowUp',
        record_id=fu.id,
        new_value=fu.to_dict(),
        details=f"API: Scheduled follow-up {fu.subject}",
        user_id=user.id
    )

    return jsonify(fu.to_dict()), 201

# ----------------------------------------------------
# Pipeline Report API
# ----------------------------------------------------
@api_bp.route('/reports/pipeline', methods=['GET'])
@api_auth_required
def get_pipeline_report():
    user = request.api_user
    report = ReportService.get_pipeline_report(user)
    return jsonify({
        'by_stage': report['by_stage'],
        'by_owner': report['by_owner'],
        'opportunities': [o.to_dict() for o in report['opportunities']]
    }), 200

