import os
from collections.abc import Generator
from sqlmodel import Session, SQLModel, create_engine, text  # Added text import

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True)


def init_db() -> None:
    # We open a direct connection to register the vector extension first
    with engine.connect() as connection:
        # This registers the pgvector type in your PostgreSQL database instance
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()
    
    # Now SQLModel can create the tables safely without crashing
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
