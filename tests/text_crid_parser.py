import unittest

from src.CrudParser import CrudParser

class TestExtractTableOperate(unittest.TestCase):
    def setUp(self):
        self.parser = CrudParser(dialect="oracle")

    def _assert_crud(self, sql: str, expected: dict[str, set[str]]):
        """テスト検証用ヘルパー関数"""
        result = dict(self.parser.extract(sql))
        self.assertEqual(result, expected)

    # -----------------------------------------------------------------
    # 1. 関数のネスト (NVL, COALESCE 等) のテスト
    # -----------------------------------------------------------------
    def test_nvl_and_coalesce_in_select(self):
        sql = """
        SELECT 
            NVL(E.SALARY, 0) AS SAL,
            COALESCE(D.LOCATION_ID, NVL(E.MANAGER_ID, 9999)) AS LOC
        FROM EMPLOYEES E
        LEFT JOIN DEPARTMENTS D ON E.DEPARTMENT_ID = D.DEPARTMENT_ID
        WHERE NVL(E.STATUS, 'A') = 'A'
        """
        # NVLやCOALESCEを使っても影響を受けず、正しくRのみ抽出されるか
        self._assert_crud(sql, {"EMPLOYEES": {"R"}, "DEPARTMENTS": {"R"}})

    def test_nvl_in_update_set_clause(self):
        sql = """
        UPDATE EMPLOYEES
        SET SALARY = NVL((SELECT AVG(SALARY) FROM HIST_SALARY), 1000)
        WHERE DEPARTMENT_ID = COALESCE(:DEPT_ID, 10)
        """
        # EMPLOYEESはU、SET句/WHERE句内のサブクエリ・参照はR
        self._assert_crud(sql, {"EMPLOYEES": {"U"}, "HIST_SALARY": {"R"}})

    # -----------------------------------------------------------------
    # 2. DDL / 基本 DML
    # -----------------------------------------------------------------
    def test_truncate_table(self):
        sql = "TRUNCATE TABLE USER_LOGS;"
        self._assert_crud(sql, {"USER_LOGS": {"D"}})

    def test_insert_select(self):
        sql = """
        INSERT INTO ARCHIVE_LOGS (LOG_ID, LOG_DATE)
        SELECT LOG_ID, LOG_DATE FROM USER_LOGS WHERE LOG_DATE < SYSDATE - 30
        """
        self._assert_crud(sql, {"ARCHIVE_LOGS": {"C"}, "USER_LOGS": {"R"}})

    def test_update_with_subquery(self):
        sql = """
        UPDATE EMPLOYEES E
        SET E.SALARY = E.SALARY * 1.1
        WHERE E.DEPARTMENT_ID IN (SELECT D.DEPARTMENT_ID FROM DEPARTMENTS D WHERE D.LOCATION_ID = 1000)
        """
        self._assert_crud(sql, {"EMPLOYEES": {"U"}, "DEPARTMENTS": {"R"}})

    def test_delete_statement(self):
        sql = "DELETE FROM USER_LOGS WHERE LOG_DATE < SYSDATE - 365"
        self._assert_crud(sql, {"USER_LOGS": {"D"}})

    # -----------------------------------------------------------------
    # 3. MERGE INTO (UPSERT)
    # -----------------------------------------------------------------
    def test_merge_both_update_and_insert(self):
        sql = """
        MERGE INTO EMPLOYEES E
        USING NEW_EMPLOYEES N ON (E.EMPLOYEE_ID = N.EMPLOYEE_ID)
        WHEN MATCHED THEN
          UPDATE SET E.SALARY = NVL(N.SALARY, E.SALARY)
        WHEN NOT MATCHED THEN
          INSERT (EMPLOYEE_ID, SALARY) VALUES (N.EMPLOYEE_ID, N.SALARY)
        """
        self._assert_crud(sql, {"EMPLOYEES": {"U", "C"}, "NEW_EMPLOYEES": {"R"}})

    def test_merge_update_only(self):
        sql = """
        MERGE INTO EMPLOYEES E
        USING NEW_EMPLOYEES N
           ON (E.EMPLOYEE_ID = N.EMPLOYEE_ID)
        WHEN MATCHED THEN
          UPDATE SET E.SALARY = N.SALARY
        """
        self._assert_crud(sql, {"EMPLOYEES": {"U"}, "NEW_EMPLOYEES": {"R"}})

    # -----------------------------------------------------------------
    # 4. Oracle固有構文 (RETURNING句, 外部結合(+))
    # -----------------------------------------------------------------
    def test_returning_into_multiple_vars(self):
        sql = """
        UPDATE EMPLOYEES
        SET SALARY = SALARY * 1.1
        WHERE DEPARTMENT_ID = 10
        RETURNING SALARY, EMPLOYEE_ID INTO :NEW_SAL, :EMP_ID
        """
        # RETURNING句の代入先変数群が参照(R)として誤検知されないか
        self._assert_crud(sql, {"EMPLOYEES": {"U"}})

    def test_oracle_outer_join_plus_operator(self):
        sql = """
        SELECT E.EMP_NAME, D.DEPT_NAME
        FROM EMPLOYEES E, DEPARTMENTS D
        WHERE E.DEPT_ID = D.DEPT_ID(+)
        """
        self._assert_crud(sql, {"EMPLOYEES": {"R"}, "DEPARTMENTS": {"R"}})


    # -----------------------------------------------------------------
    # 5. WITH句 (CTE) の除外テスト
    # -----------------------------------------------------------------
    def test_cte_with_clause_exclusion(self):
        sql = """
        WITH TEMP_DEPT AS (
            SELECT DEPARTMENT_ID FROM DEPARTMENTS WHERE LOCATION_ID = 100
        )
        SELECT E.EMPLOYEE_NAME
        FROM EMPLOYEES E
        JOIN TEMP_DEPT T ON E.DEPARTMENT_ID = T.DEPARTMENT_ID
        """
        # TEMP_DEPT は仮想テーブルのため出力から除外され、DEPARTMENTS と EMPLOYEES のみ残るか
        self._assert_crud(sql, {"EMPLOYEES": {"R"}, "DEPARTMENTS": {"R"}})

    # -----------------------------------------------------------------
    # 6. シノニム
    # -----------------------------------------------------------------
    def test_synonym(self):
        sql = """
        INSERT INTO SYN_EMP (EMP_ID, EMP_NAME)
        SELECT ID, NAME FROM STG_EMP
        """
        self._assert_crud(sql, {"SYN_EMP": {"C"}, "STG_EMP": {"R"}})

if __name__ == "__main__":
    unittest.main()