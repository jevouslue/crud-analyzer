# CRUD Analyzer
処理ごとにCRUDを把握するためのGUIツールです。  
処理単位でフォルダを作成し、その中にsqlファイルを配置することで解析結果をCSVファイルとして保存します。  
対象ダイアレクトはORACLE。  
[SQLGlot](https://sqlglot.com/sqlglot.html)を使用しているため柔軟に変更可能。

## 環境構築
1. 仮想環境構築
    ```bash
    uv venv
    ```
2. 依存関係解決
    ```bash
    uv sync
    ```

## パッケージ化
```bash
pyinstaller src/app.py --onefile --noconsole
```
実行後は[dist](dist)フォルダ内に環境にあったものが生成される  

## 使用例  
フォルダ構造
```text
sql
├── Job1
│   ├── Step1.sql
│   ├── Step2.sql
│   └── Step3.sql
└── Job2
    ├── Step1.sql
    └── Step2.sql
```

 CRUD.csv

| JOB_ID | C       | R             | U         | D |
|--------|---------|---------------|-----------|---|
| Job1   |         | DEPARTMENTS   |           |   | 
| Job1   |         | EMPLOYEES     | EMPLOYEES |   | 
| Job1   |         | HIST_SALARY   |           |   | 
| Job2   |         |               | EMPLOYEES |   | 
| Job2   |         | NEW_EMPLOYEES |           |   | 
| Job2   |         | STG_EMP       |           |   | 
| Job2   | SYN_EMP |               |           |   | 
