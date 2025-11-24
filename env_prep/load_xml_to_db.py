import os
import pyodbc
import logging
import xml.etree.ElementTree as ET

from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


SAMPLES_DIR = str(Path(__file__).parent.parent / "config" / "samples" / "xml_files")
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=XmlConversionDB;Trusted_Connection=yes;"
    "UID=vscode;"
    "PWD=express"
)


def get_xml_files(directory):
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]


def load_files_to_db():
    try:
        conn = pyodbc.connect(CONN_STR)
        logging.info("Database connection established.")
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return

    xml_files = get_xml_files(SAMPLES_DIR)
    logging.info(f"Found {len(xml_files)} XML files to load.")
    loaded = 0
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET IDENTITY_INSERT app_xml ON;")
            for file_path in xml_files:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    xml_content = f.read()
                # Parse XML to extract app_id
                try:
                    root = ET.fromstring(xml_content)
                    request = root.find("Request")
                    app_id = request.get("ID") if request is not None else None
                except ET.ParseError as e:
                    logging.warning(f"Failed to parse XML in {file_path}: {e}")
                    app_id = None
                # If app_id is missing, derive a new one based on MAX(app_id)+1 to ensure uniqueness
                if app_id is None:
                    try:
                        cursor.execute("SELECT MAX(app_id) FROM app_xml")
                        max_row = cursor.fetchone()
                        max_id = max_row[0] if max_row and max_row[0] is not None else 0
                        app_id = int(max_id) + 1
                        logging.info(f"Derived app_id {app_id} for file {file_path} (no ID in XML)")
                    except Exception as e:
                        logging.warning(f"Failed to derive app_id for {file_path}: {e}")
                        logging.warning(f"Skipping {file_path}: No app_id found and could not derive one.")
                        continue

                # Insert using the contract column name `app_XML` (preserve case as used in DB)
                cursor.execute(
                    "INSERT INTO app_xml (app_id, app_XML) VALUES (?, ?)", app_id, xml_content
                )
                loaded += 1
            cursor.execute("SET IDENTITY_INSERT app_xml OFF;")
            conn.commit()
        logging.info(f"Loaded {loaded} XML files into app_xml table.")
    except Exception as e:
        logging.error(f"Failed to load XML files: {e}")
    finally:
        conn.close()
        logging.info("Database connection closed.")


if __name__ == "__main__":
    load_files_to_db()
