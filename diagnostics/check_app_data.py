"""Check what data was inserted for a specific app."""
import pyodbc
import sys

def check_app_data(app_id: int):
    conn = pyodbc.connect(
        'Driver={ODBC Driver 17 for SQL Server};'
        'Server=localhost\\SQLEXPRESS;'
        'Database=XmlConversionDB;'
        'Trusted_Connection=yes;'
    )
    cursor = conn.cursor()
    
    # Get contacts
    cursor.execute('SELECT con_id, ac_role FROM migration.app_contact_base WHERE app_id = ?', app_id)
    contacts = cursor.fetchall()
    print(f'Contacts for app {app_id}: {len(contacts)} rows')
    for row in contacts:
        print(f'  con_id={row[0]}, ac_role={row[1]}')
    
    if not contacts:
        print('No contacts found - checking source XML...')
        cursor.execute('SELECT app_id FROM dbo.app_xml WHERE app_id = ?', app_id)
        if cursor.fetchone():
            print(f'  XML exists for app {app_id}')
        else:
            print(f'  No XML found for app {app_id}')
        conn.close()
        return
    
    con_ids = [r[0] for r in contacts]
    
    # Get addresses
    cursor.execute(f'SELECT con_id, address_type_enum, address1, city, state_code FROM migration.app_contact_address WHERE con_id IN ({",".join("?" * len(con_ids))})', con_ids)
    addresses = cursor.fetchall()
    print(f'\nAddresses: {len(addresses)} rows')
    for row in addresses[:10]:
        print(f'  con_id={row[0]}, type={row[1]}, addr1={row[2]}, city={row[3]}, state={row[4]}')
    if len(addresses) > 10:
        print(f'  ... and {len(addresses) - 10} more')
    
    # Get employments
    cursor.execute(f'SELECT con_id, employment_type_enum, employer_name, position FROM migration.app_contact_employment WHERE con_id IN ({",".join("?" * len(con_ids))})', con_ids)
    employments = cursor.fetchall()
    print(f'\nEmployments: {len(employments)} rows')
    for row in employments[:10]:
        print(f'  con_id={row[0]}, type={row[1]}, employer={row[2]}, position={row[3]}')
    if len(employments) > 10:
        print(f'  ... and {len(employments) - 10} more')
    
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python check_app_data.py <app_id>')
        sys.exit(1)
    
    check_app_data(int(sys.argv[1]))
