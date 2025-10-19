# PROJECT CONTEXT
- Use this folder and contents to derive specifications, data model, technology selection, and fullfill project goals.
- We can tune specifications and tasks from here - they aren't perfect. Ask questions.


## OUTLINE OF CONTENTS
- `create_destination_tables.sql` will be used to create the destination SQL tables. It is a REQUIREMENT to translate the XML file contents into these tables. This can be considered as a CONTRACT.
- `new_datamodel_queries.sql` contains examples on how to retrieve data.
- *.xml are examples of actual files that will be extracted. To simulate the production environment, these files will be loaded into a text column in a table ("app_xml"), stored with their "app_id" (/Provenir/Request/@ID) in another column.
- `xml-source-to-database-map.csv` is a spreadsheet that specifies
    - XML source element and attribute
    - Destination table and column
    - Reference to type of mapping which can be derived from logic `migrate_table_logic.sql`, which illustrates enum mapping.
- `migrate_table_logic.sql` is SQL that is used to convert data from an old database to the new data model. The structure very closely aligns with the XML.


---

## Source XML Structure, Extraction & Mapping Summary

- What is required is that for each of the destination tables, there will be a single insert statement for each unique FK on each application. This means that all the `app_*` tables will have one insert and all the `contact_*` tables may have two inserts (if contained in the xml). The source attributes in the xml file are spread around in various xml elements. Each insert will gather the attributes in various elements and group them together to align with the destination table and columns.
- Each table has a PK and/or FK. The PK/FK `app_id` and the PK/FK `con_id's` should be extracted once from the xml and used in a transaction that combines all of the inserts for a single xml together. 
- Insert `_base` tables first, because they have a PK (IDENTITY INSERT ON required) and the other tables have an FK to that. Propagate all related PK/FK's from here in the xml:
    - `app_id`: `Provenir/Request/@ID`
    - `con_id` 1 (for primary): `Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']/@con_id`
    - `con_id` 2 (for authorized user -- if present): `Provenir/Request/CustData/application/contact[@ac_role_tp_c='AUTH']/@con_id`
- The mapping spreadsheet is the authoritative "contract" for extraction and transformation. Each row is a mapping "rule". 
- Each rule may have a different type of mapping listed, including type conversions, defaults, bit conversions, and enum mappings (see `data-enum-map.md` and `migrate_table_logic.sql`). 
- Only XML elements and attributes listed in `xml-source-to-database-map.csv` are extracted and mapped to destination tables/columns. All other XML content is ignored.
- Do not add columns to SQL INSERT statements that are not mapped and/or do not have a value.
- XML has mixed casing. Convert source and destination lower-case when comparing.
- The `/source-xml-samples/` folder contains actual XML files representing production data.
- Each XML file has a root `<Provenir>` element, with a child `<Request>` element. The `ID` attribute of `<Request>` is used as `app_id` in the database.
- Nested elements include `<CustData>`, `<application>`, `<app_product>`, `<contact>`, `<comments>`, and others. Attributes are found at multiple levels.
- Ignore irrelevant data. To clarify from samples and derived from the contract, the full xml path for each source element are here:
    - `Provenir/Request/`
    - `Provenir/Request/CustData/application/`
    - `Provenir/Request/CustData/application/app_product/`
    - `Provenir/Request/CustData/application/rmts_info/`
    - `Provenir/Request/CustData/application/contact/`  * may have multiple nodes
    - `Provenir/Request/CustData/application/contact/contact_address/`  * may have multiple nodes
    - `Provenir/Request/CustData/application/contact/contact_employment/`  * may have multiple nodes
    - `Provenir/Request/CustData/application/contact/app_prod_bcard/`
- Before attempting to process each XML, a pre-flight check should be made to ensure that an `app_id` and `con_id` can be extracted and that at least these two node paths are available:
    - `Provenir/Request/CustData/application/`
    - `Provenir/Request/CustData/application/contact/`
- To simulate production, each XML file is loaded into a text column in the `app_xml` table, with its `app_id` stored in a separate column.
- Extraction logic must:
  - Navigate the XML hierarchy efficiently
  - Handle edge cases (missing, malformed, or extra data)
- Example XML files are used for validation and edge case testing.

---