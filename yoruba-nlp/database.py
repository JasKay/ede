from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text
from sqlalchemy.orm import declarative_base, Session
import json

# Create SQLite database
engine = create_engine("sqlite:///ede.db", echo=False)
Base = declarative_base()

# Define the Ede table
class EdeEntry(Base):
    __tablename__ = "entries"

    id = Column(String, primary_key=True)
    source_language = Column(String)
    source_text = Column(Text)
    target_language = Column(String)
    target_text = Column(Text)
    language_family = Column(String)
    dialect = Column(String)
    data_type = Column(String)
    domain = Column(String)
    sources = Column(String)  # stored as JSON string
    verified_by = Column(Integer, default=0)
    verification_score = Column(Float, default=0.0)
    quality_checked = Column(Boolean, default=False)
    quality_notes = Column(Text)
    license = Column(String)
    last_updated = Column(String)

# Create the table
Base.metadata.create_all(engine)

# Load master JSON into database
print("Loading ede_master.json into database...")

with open("ede_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with Session(engine) as session:
    for entry in data:
        row = EdeEntry(
            id=entry["id"],
            source_language=entry["source_language"],
            source_text=entry["source_text"],
            target_language=entry["target_language"],
            target_text=entry["target_text"],
            language_family=entry["language_family"],
            dialect=entry["dialect"],
            data_type=entry["data_type"],
            domain=entry.get("domain", "unknown"),
            sources=json.dumps(entry["sources"]),
            verified_by=entry["verified_by"],
            verification_score=entry["verification_score"],
            quality_checked=entry["quality_checked"],
            quality_notes=entry.get("quality_notes", ""),
            license=entry["license"],
            last_updated=entry["last_updated"]
        )
        session.merge(row)
    session.commit()

print(f"Done. {len(data)} entries loaded into ede.db")
