from app import create_app, db
from app.models import User, Item, Warehouse, ProjectSite, Movement, Stock, Category

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Item': Item, 'Warehouse': Warehouse, 
            'ProjectSite': ProjectSite, 'Movement': Movement, 'Stock': Stock, 'Category': Category}

if __name__ == '__main__':
    app.run(debug=True)
