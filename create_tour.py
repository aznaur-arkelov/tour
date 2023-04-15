from sys import argv
from app import app, db, Tour

if len(argv) != 6:
    print('usage:', argv[0], '<name> <description> <location> <duration> <price>')
    exit(1)

with app.app_context():
    tour = Tour(
        name = argv[1],
        description = argv[2],
        location = argv[3],
        duration = argv[4],
        price = argv[5],
    )
    db.session.add(tour)
    db.session.commit()
