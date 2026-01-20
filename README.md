# Machine Management System

A comprehensive web-based application for managing machines, tracking costs, downtime, maintenance, and breakdowns with role-based access control.

## Features

### Core Functionality
- **Machine Management**: Track all machines with details (model, serial number, location, status)
- **Breakdown Logging**: Log and prioritize machine breakdowns (Critical, High, Medium, Low)
- **Maintenance Tracking**: Request and track preventive, corrective, and emergency maintenance
- **Cost Tracking**: Monitor maintenance costs and downtime costs automatically
- **Quote Management**: Upload, review, and approve maintenance quotes
- **Role-Based Access**: Different permissions for operators, maintenance team, management, and executives

### Dashboard
- Unified view of all critical information
- Real-time machine status
- Prioritized breakdown list
- Pending maintenance requests
- Quote approval queue
- Cost statistics

### User Roles

1. **Operator**: 
   - Log breakdowns
   - Request maintenance
   - View machines and their status

2. **Maintenance**:
   - All operator permissions
   - Update breakdown status
   - Upload quotes
   - Complete maintenance tasks

3. **Management**:
   - All maintenance permissions
   - Approve/reject maintenance requests
   - Approve/reject quotes
   - Add new machines
   - View cost reports

4. **EXCO (Executive)**:
   - All management permissions
   - Full access to analytics and reports

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/lionelpretor/machine-management.git
cd machine-management
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Access the application:
Open your web browser and navigate to: `http://localhost:5000`

## Default Users

The system comes with pre-configured users for testing:

| Username | Password | Role |
|----------|----------|------|
| admin | password123 | EXCO |
| manager | password123 | Management |
| operator | password123 | Operator |
| maintenance | password123 | Maintenance |

**Important**: Change these passwords in production!

## Usage Guide

### Logging a Breakdown
1. Login with any user account
2. Click "Log Breakdown" in the navigation
3. Select the machine
4. Enter issue details and set priority
5. Submit

### Requesting Maintenance
1. Click "Request Maintenance"
2. Select machine and maintenance type
3. Provide description and estimated cost
4. Set scheduled date
5. Submit request

### Uploading Quotes (Maintenance Team)
1. View pending maintenance requests on dashboard
2. Click "Upload Quote"
3. Enter vendor details and amount
4. Attach quote document
5. Submit for approval

### Approving Quotes (Management/EXCO)
1. View pending quotes on dashboard
2. Review quote details
3. Click "View" to see the uploaded document
4. Click "Approve" or "Reject"

### Viewing Reports (Management/EXCO)
1. Click "Reports" in navigation
2. View cost breakdown by machine
3. Analyze maintenance vs downtime costs
4. Export data as needed

## Database

The system uses SQLite for data storage. The database file (`machine_management.db`) is created automatically on first run.

### Database Schema

- **Users**: User accounts with role-based access
- **Machines**: Machine inventory and details
- **Breakdowns**: Breakdown incidents with priority tracking
- **MaintenanceRequests**: Maintenance scheduling and tracking
- **Quotes**: Vendor quotes for maintenance approval
- **CostEntries**: Comprehensive cost tracking

## API Endpoints

The application provides the following routes:

- `GET /` - Home page (redirects to dashboard or login)
- `GET/POST /login` - User authentication
- `GET /logout` - User logout
- `GET /dashboard` - Main dashboard with all information
- `GET /machines` - List all machines
- `GET/POST /machine/add` - Add new machine (Management/EXCO only)
- `GET /machine/<id>` - View machine details
- `GET/POST /breakdown/log` - Log new breakdown
- `POST /breakdown/<id>/update` - Update breakdown status
- `GET/POST /maintenance/request` - Request maintenance
- `POST /maintenance/<id>/update` - Update maintenance request
- `GET/POST /quote/upload/<id>` - Upload quote for maintenance
- `POST /quote/<id>/approve` - Approve or reject quote
- `GET /reports` - View cost reports and analytics

## Security Features

- Password hashing using Werkzeug security
- Session-based authentication with Flask-Login
- Role-based access control
- File upload validation and sanitization
- SQL injection protection via SQLAlchemy ORM

## Cost Calculation

### Downtime Costs
Automatically calculated when a breakdown is resolved:
- Duration = Downtime End - Downtime Start
- Cost = Duration (hours) × $100/hour

### Maintenance Costs
Recorded when maintenance is completed with actual cost entered

## File Uploads

Quotes can be uploaded in the following formats:
- PDF documents
- Word documents (.doc, .docx)
- Images (.jpg, .jpeg, .png)
- Maximum file size: 16MB

Files are stored in the `uploads/` directory with timestamped filenames.

## Production Deployment

### Security Recommendations

1. **Change Secret Key**:
   Set environment variable:
   ```bash
   export SECRET_KEY='your-secure-random-secret-key'
   ```

2. **Change Default Passwords**:
   Login with each default user and update passwords

3. **Use Production Database**:
   Consider PostgreSQL or MySQL for production:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/dbname'
   ```

4. **Enable HTTPS**:
   Use a reverse proxy (nginx, Apache) with SSL certificates

5. **Set Debug to False**:
   Remove or set `debug=False` in `app.run()`

### Deployment Options

- **Docker**: Create a Dockerfile for containerized deployment
- **Cloud Platforms**: Deploy to Heroku, AWS, Azure, or Google Cloud
- **Traditional Server**: Use Gunicorn/uWSGI with nginx

## Troubleshooting

### Issue: Database not created
- Ensure write permissions in the application directory
- Check that SQLite is properly installed

### Issue: File upload fails
- Verify `uploads/` directory exists and is writable
- Check file size is under 16MB
- Ensure valid file format

### Issue: Login fails
- Verify database was initialized (default users created)
- Check console output for any errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create an issue on GitHub
- Contact: admin@example.com 
