from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.models import db, Customer, AuditAction, User
from app.forms import CustomerForm
from app.services.crm_service import CRMService
from app.services.audit_service import AuditService

customer_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customer_bp.route('/')
@login_required
def list_customers():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    owner_id = request.args.get('owner_id', 0, type=int)

    query = CRMService.get_scoped_customers(current_user)

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                Customer.customer_name.ilike(search_fmt),
                Customer.email.ilike(search_fmt),
                Customer.phone.ilike(search_fmt),
                Customer.company_name.ilike(search_fmt),
                Customer.customer_code.ilike(search_fmt)
            )
        )

    if status:
        query = query.filter(Customer.status == status)

    if owner_id > 0:
        query = query.filter(Customer.owner_id == owner_id)

    customers_page = query.order_by(Customer.created_date.desc()).paginate(page=page, per_page=10, error_out=False)
    sales_users = User.query.filter(User.is_active == True).order_by(User.name).all()

    return render_template(
        'customers/index.html',
        customers_page=customers_page,
        search=search,
        status=status,
        owner_id=owner_id,
        sales_users=sales_users
    )

@customer_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = CustomerForm()
    if form.validate_on_submit():
        # Server-side duplicate check
        is_unique, err_msg = CRMService.check_duplicate_customer(form.email.data, form.phone.data)
        if not is_unique:
            flash(err_msg, 'danger')
            return render_template('customers/form.html', form=form, title='Create Customer')

        customer = Customer(
            customer_code=CRMService.generate_customer_code(),
            customer_name=form.customer_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip(),
            company_name=form.company_name.data.strip(),
            address=form.address.data.strip() if form.address.data else None,
            city=form.city.data.strip() if form.city.data else None,
            state=form.state.data.strip() if form.state.data else None,
            status=form.status.data,
            notes=form.notes.data.strip() if form.notes.data else None,
            owner_id=form.owner_id.data if form.owner_id.data > 0 else (current_user.id if current_user.is_sales_executive else None),
            created_by_id=current_user.id
        )
        db.session.add(customer)
        db.session.commit()

        AuditService.log(
            action=AuditAction.CREATE,
            entity_name='Customer',
            record_id=customer.id,
            new_value=customer.to_dict(),
            details=f"Created customer {customer.customer_code} ({customer.customer_name})",
            user_id=current_user.id
        )

        flash(f"Customer {customer.customer_name} ({customer.customer_code}) created successfully.", 'success')
        return redirect(url_for('customers.details', customer_id=customer.id))

    return render_template('customers/form.html', form=form, title='Create Customer')

@customer_bp.route('/<int:customer_id>')
@login_required
def details(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Scoping check
    if current_user.is_sales_executive and customer.owner_id != current_user.id:
        flash("You are not authorized to view this customer record.", "danger")
        abort(403)

    return render_template('customers/details.html', customer=customer)

@customer_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Scoping check
    if current_user.is_sales_executive and customer.owner_id != current_user.id:
        flash("You are not authorized to edit this customer record.", "danger")
        abort(403)

    form = CustomerForm(original_id=customer.id, obj=customer)
    if form.validate_on_submit():
        # Duplicate check excluding current customer
        is_unique, err_msg = CRMService.check_duplicate_customer(form.email.data, form.phone.data, exclude_id=customer.id)
        if not is_unique:
            flash(err_msg, 'danger')
            return render_template('customers/form.html', form=form, title='Edit Customer', customer=customer)

        old_val = customer.to_dict()

        customer.customer_name = form.customer_name.data.strip()
        customer.email = form.email.data.strip().lower()
        customer.phone = form.phone.data.strip()
        customer.company_name = form.company_name.data.strip()
        customer.address = form.address.data.strip() if form.address.data else None
        customer.city = form.city.data.strip() if form.city.data else None
        customer.state = form.state.data.strip() if form.state.data else None
        customer.status = form.status.data
        customer.notes = form.notes.data.strip() if form.notes.data else None
        if not current_user.is_sales_executive or current_user.is_admin or current_user.is_manager:
            customer.owner_id = form.owner_id.data if form.owner_id.data > 0 else None

        db.session.commit()

        AuditService.log(
            action=AuditAction.UPDATE,
            entity_name='Customer',
            record_id=customer.id,
            old_value=old_val,
            new_value=customer.to_dict(),
            details=f"Updated customer {customer.customer_code}",
            user_id=current_user.id
        )

        flash("Customer updated successfully.", "success")
        return redirect(url_for('customers.details', customer_id=customer.id))

    return render_template('customers/form.html', form=form, title='Edit Customer', customer=customer)

@customer_bp.route('/<int:customer_id>/delete', methods=['POST'])
@login_required
def delete(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Scoping check
    if current_user.is_sales_executive and customer.owner_id != current_user.id:
        flash("You are not authorized to delete this customer record.", "danger")
        abort(403)

    old_val = customer.to_dict()
    code = customer.customer_code
    name = customer.customer_name
    
    db.session.delete(customer)
    db.session.commit()

    AuditService.log(
        action=AuditAction.DELETE,
        entity_name='Customer',
        record_id=customer_id,
        old_value=old_val,
        details=f"Deleted customer {code} ({name})",
        user_id=current_user.id
    )

    flash(f"Customer {name} ({code}) has been deleted.", "info")
    return redirect(url_for('customers.list_customers'))

