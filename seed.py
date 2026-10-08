from datetime import datetime, date, timedelta
from app import create_app
from app.models import (
    db, User, Role, Customer, Lead, LeadStatus, LeadPriority, LeadSource,
    Opportunity, OpportunityStage, OpportunityStatus, FollowUp, FollowUpStatus,
    FollowUpType, Activity, ActivityType, ActivityStatus, AuditLog, AuditAction
)

def seed_database():
    app = create_app()
    with app.app_context():
        # Drop and create all tables for a clean seed
        db.create_all()

        # Check if already seeded
        if User.query.first():
            print("Database already contains records. Skipping seed.")
            return

        print("Seeding AcxiomCRM database...")

        # 1. Users
        admin = User(name="System Administrator", email="admin@acxiom.com", role=Role.ADMIN, is_active=True)
        admin.set_password("Admin@123")

        manager = User(name="Sarah Jenkins", email="manager@acxiom.com", role=Role.MANAGER, is_active=True)
        manager.set_password("Manager@123")

        sales1 = User(name="John Doe", email="sales1@acxiom.com", role=Role.SALES_EXECUTIVE, is_active=True)
        sales1.set_password("Sales@123")

        sales2 = User(name="Jane Smith", email="sales2@acxiom.com", role=Role.SALES_EXECUTIVE, is_active=True)
        sales2.set_password("Sales@123")

        db.session.add_all([admin, manager, sales1, sales2])
        db.session.commit()

        # 2. Customers
        c1 = Customer(
            customer_code="CUST-0001",
            customer_name="TechCorp Solutions Ltd",
            email="contact@techcorp.com",
            phone="9876543210",
            company_name="TechCorp Solutions",
            address="100 Innovation Way, Silicon Park",
            city="Bengaluru",
            state="Karnataka",
            status="Active",
            notes="Enterprise cloud infrastructure client.",
            owner_id=sales1.id,
            created_by_id=admin.id,
            created_date=datetime.utcnow() - timedelta(days=60)
        )

        c2 = Customer(
            customer_code="CUST-0002",
            customer_name="Global Logistics Inc",
            email="support@globallogistics.com",
            phone="9876543211",
            company_name="Global Logistics",
            address="45 Harbor Blvd, Port Zone",
            city="Mumbai",
            state="Maharashtra",
            status="Active",
            notes="Fleet tracking and warehouse management systems.",
            owner_id=sales1.id,
            created_by_id=manager.id,
            created_date=datetime.utcnow() - timedelta(days=45)
        )

        c3 = Customer(
            customer_code="CUST-0003",
            customer_name="Apex Health Systems",
            email="admin@apexhealth.org",
            phone="9876543212",
            company_name="Apex Health",
            address="78 Care Ave, Medical District",
            city="Hyderabad",
            state="Telangana",
            status="Active",
            notes="Hospital management software suite.",
            owner_id=sales2.id,
            created_by_id=sales2.id,
            created_date=datetime.utcnow() - timedelta(days=30)
        )

        c4 = Customer(
            customer_code="CUST-0004",
            customer_name="Pinnacle Retail Group",
            email="info@pinnacleretail.com",
            phone="9876543213",
            company_name="Pinnacle Retail",
            address="12 Commercial Square",
            city="Delhi",
            state="Delhi",
            status="Active",
            notes="Omnichannel eCommerce & Point of Sale network.",
            owner_id=sales2.id,
            created_by_id=manager.id,
            created_date=datetime.utcnow() - timedelta(days=15)
        )

        db.session.add_all([c1, c2, c3, c4])
        db.session.commit()

        # 3. Leads
        l1 = Lead(
            lead_code="LEAD-0001",
            lead_name="David Miller",
            email="david.m@cyberdefense.io",
            phone="9876543220",
            company_name="CyberDefense Systems",
            source=LeadSource.WEBSITE,
            status=LeadStatus.QUALIFIED,
            priority=LeadPriority.HIGH,
            expected_value=65000.0,
            notes="Looking for zero-trust security audit & software rollout.",
            assigned_to_id=sales1.id,
            created_date=datetime.utcnow() - timedelta(days=20)
        )

        l2 = Lead(
            lead_code="LEAD-0002",
            lead_name="Elena Rostova",
            email="elena@quantumai.dev",
            phone="9876543221",
            company_name="Quantum AI Labs",
            source=LeadSource.REFERRAL,
            status=LeadStatus.CONTACTED,
            priority=LeadPriority.HIGH,
            expected_value=120000.0,
            notes="Interested in AI infrastructure acceleration tier.",
            assigned_to_id=sales1.id,
            created_date=datetime.utcnow() - timedelta(days=10)
        )

        l3 = Lead(
            lead_code="LEAD-0003",
            lead_name="Robert Chang",
            email="robert@horizonfintech.com",
            phone="9876543222",
            company_name="Horizon Financial",
            source=LeadSource.CAMPAIGN,
            status=LeadStatus.NEW,
            priority=LeadPriority.MEDIUM,
            expected_value=45000.0,
            notes="Lead from Q3 banking conference webinar.",
            assigned_to_id=sales2.id,
            created_date=datetime.utcnow() - timedelta(days=5)
        )

        db.session.add_all([l1, l2, l3])
        db.session.commit()

        # 4. Opportunities
        today = date.today()
        o1 = Opportunity(
            opportunity_code="OPP-0001",
            opportunity_name="TechCorp Cloud Hybrid Expansion",
            customer_id=c1.id,
            amount=85000.0,
            stage=OpportunityStage.NEGOTIATION,
            probability=80,
            expected_close_date=today + timedelta(days=14),
            status=OpportunityStatus.OPEN,
            source="Account Expansion",
            notes="Finalizing SLA agreements with procurement team.",
            assigned_to_id=sales1.id,
            created_date=datetime.utcnow() - timedelta(days=25)
        )

        o2 = Opportunity(
            opportunity_code="OPP-0002",
            opportunity_name="Global Logistics Fleet IoT Rollout",
            customer_id=c2.id,
            amount=140000.0,
            stage=OpportunityStage.PROPOSAL,
            probability=50,
            expected_close_date=today + timedelta(days=30),
            status=OpportunityStatus.OPEN,
            source="Referral",
            notes="RFP submitted; technical demo completed successfully.",
            assigned_to_id=sales1.id,
            created_date=datetime.utcnow() - timedelta(days=15)
        )

        o3 = Opportunity(
            opportunity_code="OPP-0003",
            opportunity_name="Apex Health Diagnostic Analytics",
            customer_id=c3.id,
            amount=95000.0,
            stage=OpportunityStage.WON,
            probability=100,
            expected_close_date=today - timedelta(days=5),
            status=OpportunityStatus.WON,
            source="Direct Inbound",
            notes="Contract signed and payment escrow initialized.",
            assigned_to_id=sales2.id,
            created_date=datetime.utcnow() - timedelta(days=40)
        )

        o4 = Opportunity(
            opportunity_code="OPP-0004",
            opportunity_name="Pinnacle POS Modernization",
            customer_id=c4.id,
            amount=50000.0,
            stage=OpportunityStage.QUALIFICATION,
            probability=20,
            expected_close_date=today + timedelta(days=45),
            status=OpportunityStatus.OPEN,
            source="Website",
            notes="Initial requirements discovery phase in progress.",
            assigned_to_id=sales2.id,
            created_date=datetime.utcnow() - timedelta(days=5)
        )

        db.session.add_all([o1, o2, o3, o4])
        db.session.commit()

        # 5. Follow-Ups
        fu1 = FollowUp(
            subject="Negotiation contract review with TechCorp legal",
            followup_type=FollowUpType.MEETING,
            followup_date=today + timedelta(days=2),
            status=FollowUpStatus.PLANNED,
            remarks="Review clause 4.2 data redundancy and payment terms.",
            customer_id=c1.id,
            opportunity_id=o1.id,
            assigned_to_id=sales1.id
        )

        fu2 = FollowUp(
            subject="Demo follow-up call with CyberDefense Miller",
            followup_type=FollowUpType.CALL,
            followup_date=today + timedelta(days=3),
            status=FollowUpStatus.PLANNED,
            remarks="Check if security team had questions on API tokens.",
            lead_id=l1.id,
            assigned_to_id=sales1.id
        )

        fu3 = FollowUp(
            subject="Overdue quarterly check-in with Global Logistics",
            followup_type=FollowUpType.CALL,
            followup_date=today - timedelta(days=2),
            status=FollowUpStatus.PLANNED, # Overdue planned
            remarks="Need to confirm warehouse hardware delivery timeline.",
            customer_id=c2.id,
            assigned_to_id=sales1.id
        )

        fu4 = FollowUp(
            subject="Apex Health Kickoff Session",
            followup_type=FollowUpType.MEETING,
            followup_date=today - timedelta(days=4),
            status=FollowUpStatus.COMPLETED,
            remarks="[Completed on " + str(today - timedelta(days=4)) + "]: Great session with CIO. Implementation team onboarded.",
            customer_id=c3.id,
            opportunity_id=o3.id,
            assigned_to_id=sales2.id
        )

        db.session.add_all([fu1, fu2, fu3, fu4])
        db.session.commit()

        # 6. Activities
        a1 = Activity(
            activity_type=ActivityType.CALL,
            subject="Introductory discovery call",
            description="Discussed high level goals and current software stack.",
            activity_date=today - timedelta(days=10),
            status=ActivityStatus.COMPLETED,
            customer_id=c1.id,
            assigned_to_id=sales1.id
        )

        a2 = Activity(
            activity_type=ActivityType.MEETING,
            subject="Solution Architecture Presentation",
            description="Presented multi-cloud failover architecture diagram to engineering VP.",
            activity_date=today - timedelta(days=6),
            status=ActivityStatus.COMPLETED,
            customer_id=c1.id,
            assigned_to_id=sales1.id
        )

        a3 = Activity(
            activity_type=ActivityType.EMAIL,
            subject="Sent formal commercial proposal",
            description="Emailed pricing proposal and standard MSA terms.",
            activity_date=today - timedelta(days=3),
            status=ActivityStatus.COMPLETED,
            lead_id=l1.id,
            assigned_to_id=sales1.id
        )

        db.session.add_all([a1, a2, a3])
        db.session.commit()

        # 7. Audit Logs
        log1 = AuditLog(
            user_id=admin.id,
            action=AuditAction.LOGIN,
            entity_name='Auth',
            details="Admin logged in from local workstation.",
            result="Success",
            ip_address="127.0.0.1",
            created_date=datetime.utcnow() - timedelta(days=1)
        )

        log2 = AuditLog(
            user_id=sales1.id,
            action=AuditAction.CREATE,
            entity_name='Customer',
            record_id=str(c1.id),
            new_value=str(c1.to_dict()),
            details=f"Created customer {c1.customer_code} ({c1.customer_name})",
            result="Success",
            ip_address="127.0.0.1",
            created_date=datetime.utcnow() - timedelta(days=60)
        )

        log3 = AuditLog(
            user_id=sales1.id,
            action=AuditAction.CREATE,
            entity_name='Opportunity',
            record_id=str(o1.id),
            new_value=str(o1.to_dict()),
            details=f"Created opportunity {o1.opportunity_code} for ${o1.amount:,.2f}",
            result="Success",
            ip_address="127.0.0.1",
            created_date=datetime.utcnow() - timedelta(days=25)
        )

        db.session.add_all([log1, log2, log3])
        db.session.commit()

        print("Database seeded successfully with Users, Customers, Leads, Opportunities, Follow-Ups, Activities, and Audit Logs!")

if __name__ == '__main__':
    seed_database()

