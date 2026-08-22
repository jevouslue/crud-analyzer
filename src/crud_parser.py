import re
from collections import defaultdict
import sqlglot
from sqlglot import exp


class CrudParser:
    CRUD_CREATE = "C"
    CRUD_READ = "R"
    CRUD_UPDATE = "U"
    CRUD_DELETE = "D"

    def __init__(self, dialect="oracle"):
        self._crud_map: dict[str, set[str]] = defaultdict(set)
        self._cte_names: set[str] = set()
        self.dialect = dialect

    def extract(self, query: str) -> dict[str, set[str]]:
        self._reset_props()
        
        # --- 前処理: INTO 以降の変数を単一のダミー変数 (DUMMY_VAR) に置換 ---
        # 例: RETURNING SALARY, EMPLOYEE_ID INTO :NEW_SAL, :EMP_ID;
        #  -> RETURNING SALARY, EMPLOYEE_ID INTO DUMMY_VAR;
        cleaned_query = re.sub(
            r"(RETURNING\s+[\s\S]+?\s+INTO)\s+[\s\S]+?(;|$)",
            r"\1 DUMMY_VAR\2",
            query,
            flags=re.IGNORECASE,
        )

        # Oracle方言でパース
        ast = sqlglot.parse_one(cleaned_query, read=self.dialect)

        if ast is None:
            return self._crud_map

        # CTE（WITH句の仮想テーブル名）を収集
        self._cte_names = {
            cte_expr.alias_or_name.upper()
            for cte_expr in ast.find_all(exp.CTE)
            if cte_expr.alias_or_name
        }

        # ASTのステートメント型に応じて分岐
        if isinstance(ast, exp.Insert):
            self._handle_insert(ast)
        elif isinstance(ast, exp.Update):
            self._handle_update(ast)
        elif isinstance(ast, (exp.Delete, exp.TruncateTable)):
            self._handle_delete(ast)
        elif isinstance(ast, exp.Select):
            self._handle_select(ast)
        elif isinstance(ast, exp.Merge):
            self._handle_merge(ast)

        return self._crud_map

    def _reset_props(self):
        self._crud_map = defaultdict(set)
        self._cte_names = set()

    def _normalize_name(self, name: str) -> str:
        """テーブル名を大文字に統一して正規化 """
        if not name:
            return ""
        return name.strip('"').strip("'").strip("`").upper()

    def _mark_read_tables(
        self,
        expr: exp.Expression,
        exclude_tables: set[str] | None = None,
    ):
        """指定された式から参照(R)しているテーブルを抽出する。
        exclude_tables や CTE に含まれるテーブル名は R の対象外とする。
        """
        if exclude_tables is None:
            exclude_tables = set()

        # テーブル一覧を取得
        tables = [
            t
            for t in expr.find_all(exp.Table)
            if (
                t.name
                and self._normalize_name(t.name) not in self._cte_names
                and self._normalize_name(t.name) not in exclude_tables
            )
        ]

        # エイリアスの置き換えマップ作成
        alias_table_map = {
            self._normalize_name(t.alias): self._normalize_name(t.name)
            for t in tables
            if t.alias
        }

        for t in tables:
            norm_name = self._normalize_name(t.name)
            actual_name = alias_table_map.get(norm_name, norm_name)

            # 操作対象テーブルやCTEでなければ R を追加
            if actual_name not in exclude_tables and actual_name not in self._cte_names:
                self._crud_map[actual_name].add(self.CRUD_READ)

    def _handle_select(self, stmt: exp.Select | exp.Subquery):
        self._mark_read_tables(stmt)

    def _handle_insert(self, stmt: exp.Insert):
        target = stmt.this
        target_name = None

        if isinstance(target, exp.Schema):
            target = target.this

        if isinstance(target, exp.Table):
            target_name = self._normalize_name(target.name)
            if target_name and target_name not in self._cte_names:
                self._crud_map[target_name].add(self.CRUD_CREATE)

        exclude = {target_name} if target_name else set()

        # INSERT INTO ... SELECT の SELECT 側の参照テーブルを抽出
        if stmt.expression is not None:
            self._mark_read_tables(stmt.expression, exclude_tables=exclude)

        # WITH句（CTE）内の参照テーブルを抽出
        for with_expr in stmt.find_all(exp.With):
            for cte in with_expr.expressions:
                self._mark_read_tables(cte, exclude_tables=exclude)

    def _handle_update(self, stmt: exp.Update):
        target = stmt.this
        target_name = None

        if isinstance(target, exp.Table):
            target_name = self._normalize_name(target.name)
            if target_name and target_name not in self._cte_names:
                self._crud_map[target_name].add(self.CRUD_UPDATE)

        exclude = {target_name} if target_name else set()

        # RETURNING 句を除外して R 抽出を行う（RETURNING 句内のカラム参照による誤判定を抑止）
        stmt_without_returning = stmt.copy()
        if hasattr(stmt_without_returning, "args") and "returning" in stmt_without_returning.args:
            stmt_without_returning.args.pop("returning", None)

        self._mark_read_tables(stmt_without_returning, exclude_tables=exclude)

    def _handle_delete(self, stmt: exp.Delete | exp.TruncateTable):
        target = stmt.this
        target_name = None

        if isinstance(target, exp.Table):
            target_name = self._normalize_name(target.name)
        elif isinstance(target, exp.Schema):
            target_name = self._normalize_name(target.this.name)
        else:
            tables = list(stmt.find_all(exp.Table))
            if tables:
                target_name = self._normalize_name(tables[0].name)

        if target_name and target_name not in self._cte_names:
            self._crud_map[target_name].add(self.CRUD_DELETE)

        exclude = {target_name} if target_name else set()

        stmt_without_returning = stmt.copy()
        if hasattr(stmt_without_returning, "args") and "returning" in stmt_without_returning.args:
            stmt_without_returning.args.pop("returning", None)

        self._mark_read_tables(stmt_without_returning, exclude_tables=exclude)

    def _handle_merge(self, stmt: exp.Merge):
        """Oracleの MERGE INTO 構文を正しく処理する"""
        target = stmt.this
        target_name = None

        if isinstance(target, exp.Table):
            target_name = self._normalize_name(target.name)
        elif isinstance(target, exp.Schema):
            target_name = self._normalize_name(target.this.name)

        # WHEN句 (exp.When) を探して、その後の処理 (then) が Update か Insert かを判定
        has_update = False
        has_insert = False

        for when in stmt.find_all(exp.When):
            then_expr = when.args.get("then")
            if isinstance(then_expr, exp.Update):
                has_update = True
            elif isinstance(then_expr, exp.Insert):
                has_insert = True

        if target_name and target_name not in self._cte_names:
            if has_update:
                self._crud_map[target_name].add(self.CRUD_UPDATE)
            if has_insert:
                self._crud_map[target_name].add(self.CRUD_CREATE)

            # 万が一 When 句が見つからなかった場合の安全対策（UとCの両方を付与）
            if not has_update and not has_insert:
                self._crud_map[target_name].add(self.CRUD_UPDATE)
                self._crud_map[target_name].add(self.CRUD_CREATE)

        exclude = {target_name} if target_name else set()

        # USING 句および ON 句からの参照 (R) を抽出
        if stmt.args.get("using"):
            self._mark_read_tables(stmt.args["using"], exclude_tables=exclude)
        if stmt.args.get("on"):
            self._mark_read_tables(stmt.args["on"], exclude_tables=exclude)