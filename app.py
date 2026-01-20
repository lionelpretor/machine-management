from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///machine_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # operator, maintenance, management, exco
    email = db.Column(db.String(120))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='operational')  # operational, down, maintenance
    purchase_date = db.Column(db.Date)
    purchase_cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Breakdown(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved
    downtime_start = db.Column(db.DateTime, default=datetime.utcnow)
    downtime_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    machine = db.relationship('Machine', backref='breakdowns')
    reporter = db.relationship('User', backref='reported_breakdowns')

class MaintenanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    maintenance_type = db.Column(db.String(50))  # preventive, corrective, emergency
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, completed
    estimated_cost = db.Column(db.Float, default=0.0)
    actual_cost = db.Column(db.Float, default=0.0)
    scheduled_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    machine = db.relationship('Machine', backref='maintenance_requests')
    requester = db.relationship('User', backref='maintenance_requests')

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    maintenance_request_id = db.Column(db.Integer, db.ForeignKey('maintenance_request.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    vendor = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    maintenance_request = db.relationship('MaintenanceRequest', backref='quotes')
    uploader = db.relationship('User', foreign_keys=[uploaded_by], backref='uploaded_quotes')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_quotes')

class CostEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    cost_type = db.Column(db.String(50), nullable=False)  # maintenance, downtime, repair, parts
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, default=datetime.utcnow)
    breakdown_id = db.Column(db.Integer, db.ForeignKey('breakdown.id'))
    maintenance_request_id = db.Column(db.Integer, db.ForeignKey('maintenance_request.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    machine = db.relationship('Machine', backref='costs')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    machines = Machine.query.all()
    breakdowns = Breakdown.query.filter_by(status='open').order_by(
        db.case(
            (Breakdown.priority == 'critical', 1),
            (Breakdown.priority == 'high', 2),
            (Breakdown.priority == 'medium', 3),
            (Breakdown.priority == 'low', 4)
        )
    ).all()
    
    pending_maintenance = MaintenanceRequest.query.filter_by(status='pending').all()
    pending_quotes = Quote.query.filter_by(status='pending').all()
    
    # Calculate statistics
    total_machines = len(machines)
    machines_down = len([m for m in machines if m.status == 'down'])
    open_breakdowns = len(breakdowns)
    
    # Calculate total costs
    total_maintenance_cost = db.session.query(db.func.sum(CostEntry.amount)).filter_by(cost_type='maintenance').scalar() or 0
    total_downtime_cost = db.session.query(db.func.sum(CostEntry.amount)).filter_by(cost_type='downtime').scalar() or 0
    
    return render_template('dashboard.html',
                         machines=machines,
                         breakdowns=breakdowns,
                         pending_maintenance=pending_maintenance,
                         pending_quotes=pending_quotes,
                         total_machines=total_machines,
                         machines_down=machines_down,
                         open_breakdowns=open_breakdowns,
                         total_maintenance_cost=total_maintenance_cost,
                         total_downtime_cost=total_downtime_cost)

@app.route('/machines')
@login_required
def machines():
    machines = Machine.query.all()
    return render_template('machines.html', machines=machines)

@app.route('/machine/add', methods=['GET', 'POST'])
@login_required
def add_machine():
    if current_user.role not in ['management', 'exco']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            purchase_date = None
            if request.form.get('purchase_date'):
                purchase_date = datetime.strptime(request.form.get('purchase_date'), '%Y-%m-%d').date()
            
            purchase_cost = float(request.form.get('purchase_cost', 0))
            
            machine = Machine(
                name=request.form.get('name'),
                model=request.form.get('model'),
                serial_number=request.form.get('serial_number'),
                location=request.form.get('location'),
                purchase_date=purchase_date,
                purchase_cost=purchase_cost
            )
            db.session.add(machine)
            db.session.commit()
            flash('Machine added successfully', 'success')
            return redirect(url_for('machines'))
        except ValueError as e:
            flash('Invalid date or cost format', 'error')
            return redirect(request.url)
    
    return render_template('add_machine.html')

@app.route('/machine/<int:machine_id>')
@login_required
def machine_detail(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    breakdowns = Breakdown.query.filter_by(machine_id=machine_id).order_by(Breakdown.created_at.desc()).all()
    maintenance_requests = MaintenanceRequest.query.filter_by(machine_id=machine_id).order_by(MaintenanceRequest.created_at.desc()).all()
    costs = CostEntry.query.filter_by(machine_id=machine_id).order_by(CostEntry.date.desc()).all()
    
    total_cost = sum(cost.amount for cost in costs)
    
    return render_template('machine_detail.html',
                         machine=machine,
                         breakdowns=breakdowns,
                         maintenance_requests=maintenance_requests,
                         costs=costs,
                         total_cost=total_cost)

@app.route('/breakdown/log', methods=['GET', 'POST'])
@login_required
def log_breakdown():
    if request.method == 'POST':
        machine_id = request.form.get('machine_id')
        breakdown = Breakdown(
            machine_id=machine_id,
            reported_by=current_user.id,
            title=request.form.get('title'),
            description=request.form.get('description'),
            priority=request.form.get('priority', 'medium')
        )
        
        # Update machine status
        machine = Machine.query.get(machine_id)
        if machine:
            machine.status = 'down'
        
        db.session.add(breakdown)
        db.session.commit()
        flash('Breakdown logged successfully', 'success')
        return redirect(url_for('dashboard'))
    
    machines = Machine.query.filter_by(status='operational').all()
    return render_template('log_breakdown.html', machines=machines)

@app.route('/breakdown/<int:breakdown_id>/update', methods=['POST'])
@login_required
def update_breakdown(breakdown_id):
    if current_user.role not in ['maintenance', 'management', 'exco']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    breakdown = Breakdown.query.get_or_404(breakdown_id)
    status = request.form.get('status')
    
    if status:
        breakdown.status = status
        
        if status == 'resolved':
            breakdown.downtime_end = datetime.utcnow()
            # Calculate downtime cost if applicable
            if breakdown.downtime_start and breakdown.downtime_end:
                hours_down = (breakdown.downtime_end - breakdown.downtime_start).total_seconds() / 3600
                downtime_cost = hours_down * 100  # $100 per hour example rate
                
                cost_entry = CostEntry(
                    machine_id=breakdown.machine_id,
                    cost_type='downtime',
                    amount=downtime_cost,
                    description=f'Downtime cost for breakdown: {breakdown.title}',
                    breakdown_id=breakdown.id
                )
                db.session.add(cost_entry)
            
            # Update machine status
            machine = Machine.query.get(breakdown.machine_id)
            if machine:
                machine.status = 'operational'
    
    db.session.commit()
    flash('Breakdown updated successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/maintenance/request', methods=['GET', 'POST'])
@login_required
def request_maintenance():
    if request.method == 'POST':
        try:
            scheduled_date = None
            if request.form.get('scheduled_date'):
                scheduled_date = datetime.strptime(request.form.get('scheduled_date'), '%Y-%m-%d').date()
            
            estimated_cost = float(request.form.get('estimated_cost', 0))
            
            maintenance_request = MaintenanceRequest(
                machine_id=request.form.get('machine_id'),
                requested_by=current_user.id,
                title=request.form.get('title'),
                description=request.form.get('description'),
                maintenance_type=request.form.get('maintenance_type'),
                estimated_cost=estimated_cost,
                scheduled_date=scheduled_date
            )
            db.session.add(maintenance_request)
            db.session.commit()
            flash('Maintenance request submitted successfully', 'success')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Invalid date or cost format', 'error')
            return redirect(request.url)
    
    machines = Machine.query.all()
    return render_template('request_maintenance.html', machines=machines)

@app.route('/maintenance/<int:request_id>/update', methods=['POST'])
@login_required
def update_maintenance(request_id):
    if current_user.role not in ['management', 'exco']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    maintenance_request = MaintenanceRequest.query.get_or_404(request_id)
    status = request.form.get('status')
    
    if status:
        maintenance_request.status = status
        
        if status == 'approved':
            machine = Machine.query.get(maintenance_request.machine_id)
            if machine:
                machine.status = 'maintenance'
        elif status == 'completed':
            maintenance_request.completed_date = datetime.utcnow().date()
            actual_cost_str = request.form.get('actual_cost')
            if actual_cost_str:
                try:
                    actual_cost = float(actual_cost_str)
                    maintenance_request.actual_cost = actual_cost
                    cost_entry = CostEntry(
                        machine_id=maintenance_request.machine_id,
                        cost_type='maintenance',
                        amount=actual_cost,
                        description=f'Maintenance: {maintenance_request.title}',
                        maintenance_request_id=request_id
                    )
                    db.session.add(cost_entry)
                except ValueError:
                    flash('Invalid cost value', 'error')
                    return redirect(url_for('dashboard'))
            
            machine = Machine.query.get(maintenance_request.machine_id)
            if machine:
                machine.status = 'operational'
    
    db.session.commit()
    flash('Maintenance request updated successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/quote/upload/<int:request_id>', methods=['GET', 'POST'])
@login_required
def upload_quote(request_id):
    if current_user.role not in ['maintenance', 'management']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    maintenance_request = MaintenanceRequest.query.get_or_404(request_id)
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            
            # Validate file extension
            allowed_extensions = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'}
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in allowed_extensions:
                flash('Invalid file type. Allowed: PDF, Word, Images', 'error')
                return redirect(request.url)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                amount = float(request.form.get('amount', 0))
            except ValueError:
                flash('Invalid amount value', 'error')
                os.remove(filepath)  # Clean up uploaded file
                return redirect(request.url)
            
            quote = Quote(
                maintenance_request_id=request_id,
                uploaded_by=current_user.id,
                filename=filename,
                amount=amount,
                vendor=request.form.get('vendor')
            )
            db.session.add(quote)
            db.session.commit()
            flash('Quote uploaded successfully', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('upload_quote.html', maintenance_request=maintenance_request)

@app.route('/quote/<int:quote_id>/approve', methods=['POST'])
@login_required
def approve_quote(quote_id):
    if current_user.role not in ['management', 'exco']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    quote = Quote.query.get_or_404(quote_id)
    action = request.form.get('action')
    
    if action == 'approve':
        quote.status = 'approved'
        quote.approved_by = current_user.id
        flash('Quote approved successfully', 'success')
    elif action == 'reject':
        quote.status = 'rejected'
        flash('Quote rejected', 'info')
    
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    # Validate filename to prevent path traversal
    filename = secure_filename(filename)
    # Verify file exists in quotes table to ensure authorized access
    quote = Quote.query.filter_by(filename=filename).first()
    if not quote:
        flash('File not found', 'error')
        return redirect(url_for('dashboard'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/reports')
@login_required
def reports():
    if current_user.role not in ['management', 'exco']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    # Cost summary by machine
    machines = Machine.query.all()
    machine_costs = []
    for machine in machines:
        total_cost = db.session.query(db.func.sum(CostEntry.amount)).filter_by(machine_id=machine.id).scalar() or 0
        breakdown_count = Breakdown.query.filter_by(machine_id=machine.id).count()
        machine_costs.append({
            'machine': machine,
            'total_cost': total_cost,
            'breakdown_count': breakdown_count
        })
    
    # Overall statistics
    total_maintenance = db.session.query(db.func.sum(CostEntry.amount)).filter_by(cost_type='maintenance').scalar() or 0
    total_downtime = db.session.query(db.func.sum(CostEntry.amount)).filter_by(cost_type='downtime').scalar() or 0
    total_costs = total_maintenance + total_downtime
    
    return render_template('reports.html',
                         machine_costs=machine_costs,
                         total_maintenance=total_maintenance,
                         total_downtime=total_downtime,
                         total_costs=total_costs)

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default users if they don't exist
        if User.query.count() == 0:
            users = [
                User(username='admin', role='exco', email='admin@example.com'),
                User(username='manager', role='management', email='manager@example.com'),
                User(username='operator', role='operator', email='operator@example.com'),
                User(username='maintenance', role='maintenance', email='maintenance@example.com')
            ]
            
            for user in users:
                user.set_password('password123')  # Default password
                db.session.add(user)
            
            db.session.commit()
            print('Default users created. Username/Password:')
            print('admin/password123 (EXCO)')
            print('manager/password123 (Management)')
            print('operator/password123 (Operator)')
            print('maintenance/password123 (Maintenance)')

if __name__ == '__main__':
    init_db()
    # Debug mode should be disabled in production
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5001)
