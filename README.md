# AcxiomCRM - Enterprise Customer Relationship Management System

**AcxiomCRM** is a production-grade, role-based CRM application covering the complete customer-sales lifecycle from lead capture and qualification through follow-ups, opportunities, activity logs, reporting, append-only audit trail, and secured REST APIs.

---

## 🚀 Key Features & Modules

### 1. Authentication & Security Specification
- **Framework-Managed Password Hashing**: PBKDF2/SHA-256 password hashing. Passwords and hashes are never exposed in UI views, API responses, DTOs, or logs.
- **Password Complexity Policy**: Enforces $\ge 8$ characters, uppercase letter, lowercase letter, number, and special character.
- **Account Lockout Policy**: Automatically locks accounts for 15 minutes after 5 consecutive failed login attempts. Administrator can unlock accounts manually.
- **CSRF Protection**: All state-changing POST forms are protected via `ValidateAntiForgeryToken` / Flask-WTF CSRF tokens.
- **SQL Injection Defense**: Entity Framework / SQLAlchemy ORM parameterized queries.

### 2. Role-Based Authorization (RBAC)
- **Admin**: Complete system control, user and role administration, account unlock, audit trail inspection, all CRM records and analytics.
- **Manager**: Team-wide pipeline management, opportunity forecasting, team reports, and CRM oversight.
- **Sales Executive**: Scoped access strictly to assigned customers, leads, opportunities, follow-ups, and individual performance dashboards.

### 3. Executive Dashboard & Real-Time Analytics
- **Role-Scoped KPI Cards**: Total Customers, Total Leads, Open Leads, Active Pipeline Value (\$), Weighted Pipeline Value (\$ = $\text{Amount} \times \text{Probability} / 100$), Won Revenue (\$), and Overdue Follow-ups.
- **Chart.js Visualizations**:
  - Lead Status Breakdown (Doughnut Chart)
  - Opportunity Pipeline Stages Breakdown (Bar Chart)
  - Monthly Closed Sales vs Target Pipeline (Line Chart)
- **Date Range Filters**: All Time, Today, This Week, This Month, and Custom Date Range.

### 4. Core CRM Workflows
- **Customer Management**: Complete CRUD, unique code generation (`CUST-0001`), duplicate prevention by email/phone, relationship history.
- **Lead Management & Conversion**: Prospective lead capture, status progression (`New` $\rightarrow$ `Contacted` $\rightarrow$ `Qualified` $\rightarrow$ `Converted` / `Lost`), and automated 1-click **Lead-to-Customer & Opportunity Conversion Workflow**.
- **Opportunity Management**: Pipeline stages (`Qualification` $\rightarrow$ `Proposal` $\rightarrow$ `Negotiation` $\rightarrow$ `Won` / `Lost`), strict validations ($\text{Amount} > 0$, $0 \le \text{Probability} \le 100$, future close dates for active deals), Kanban pipeline board, and weighted value derivations.
- **Follow-Up Scheduling**: Scheduled calls, meetings, emails, tasks with due date validation ($\ge \text{Today}$ for new/planned items), upcoming/overdue tabs, reschedule and mark-complete actions.
- **Activity Logging**: Track touchpoints (Call, Meeting, Email, Task) associated with customer or lead records.
- **Append-Only Audit Trail**: Immutable tracking of Logins, Failed Logins, Logouts, Lockouts, Unlocks, CRUD operations, Role Changes, and Conversions.

### 5. Reporting & Exports
- **8 Comprehensive Reports**:
  1. Customer Master Report
  2. Lead Generation & Conversion Report
  3. Opportunity & Revenue Valuation Report
  4. Pipeline Stage & Owner Report
  5. Follow-Up Touchpoint Report
  6. Lead-to-Customer Conversion Analytics
  7. Sales Rep Activity & Performance Report
  8. Security & Business Audit Report
- **CSV Data Export** supported on all reporting and audit screens.

### 6. Secured REST API
| Method | Endpoint | Description | Access |
|---|---|---|---|
| `POST` | `/api/auth/login` | Authenticate user & issue JWT token | Public |
| `POST` | `/api/auth/logout` | Terminate session | Authenticated |
| `GET` | `/api/customers` | List/search scoped customers | Authorized |
| `GET` | `/api/customers/{id}` | Get customer by ID | Authorized |
| `POST` | `/api/customers` | Create customer (validates duplicate email/phone) | Authorized |
| `PUT` | `/api/customers/{id}` | Update customer | Authorized |
| `DELETE` | `/api/customers/{id}` | Delete customer | Authorized |
| `GET` | `/api/leads` | List/search scoped leads | Authorized |
| `POST` | `/api/leads` | Create prospective lead | Authorized |
| `GET` | `/api/opportunities` | List/search scoped opportunities | Authorized |
| `POST` | `/api/opportunities` | Create opportunity (validates Amount > 0, Prob 0-100) | Authorized |
| `GET` | `/api/followups` | List follow-up schedule | Authorized |
| `POST` | `/api/followups` | Schedule new follow-up (validates date $\ge$ today) | Authorized |
| `GET` | `/api/reports/pipeline` | Stage-wise and owner-wise pipeline metrics | Authorized |

---

## 🔑 Pre-Configured Test Credentials

| Role | Email | Password | Scope |
|---|---|---|---|
| **Admin** | `admin@acxiom.com` | `Admin@123` | Full Application & User Administration |
| **Manager** | `manager@acxiom.com` | `Manager@123` | Team Pipeline & Organization Reports |
| **Sales Executive** | `sales1@acxiom.com` | `Sales@123` | Assigned Portfolio (John Doe) |
| **Sales Executive** | `sales2@acxiom.com` | `Sales@123` | Assigned Portfolio (Jane Smith) |

---

## 🛠️ Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Seed Sample Data & Run Server**:
   ```bash
   python seed.py
   python run.py
   ```
   Open your browser and navigate to: `http://localhost:5000`

---

## 🧪 Automated Testing

Execute the comprehensive test suite verifying security, validation, RBAC, workflows, and REST APIs:
```bash
python -m unittest discover tests
```

