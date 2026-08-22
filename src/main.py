from crud_parser import CrudParser


def main():
    sql = """SELECT E.EMPLOYEE_NAME, D.DEPARTMENT_NAME
        FROM EMPLOYEES E, DEPARTMENTS D
        WHERE E.DEPARTMENT_ID = D.DEPARTMENT_ID(+)"""
    parser = CrudParser()
    crud_map = parser.extract(sql)
    print(crud_map)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

