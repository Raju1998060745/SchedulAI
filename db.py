from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

engine = create_engine('sqlite:///database.db')  # or use PostgreSQL/MySQL
Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine)
