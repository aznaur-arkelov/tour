from sys import argv
from app import app, db, User

if len(argv) != 3:
    print('usage:', argv[0], '<username> <password>')
    exit(1)

with app.app_context():
    admin = User(
        username = argv[1],
        password = argv[2],
        admin = True
    )
    db.session.add(admin)
    db.session.commit()
