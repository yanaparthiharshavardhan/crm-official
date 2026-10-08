import os
from app import create_app
from app.models import db, User
from seed import seed_database

app = create_app()

with app.app_context():
    db.create_all()
    # Check if we should seed default data
    if not User.query.first():
        seed_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

