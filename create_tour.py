from sys import argv
from app import app, db, Tour

if len(argv) != 4:
    print('usage:', argv[0], '<name> <description> <price>')
    exit(1)

with app.app_context():
    tour = Tour(
        name = argv[1],
        description = argv[2],
        price = argv[3],
    )
    db.session.add(tour)
    db.session.commit()
