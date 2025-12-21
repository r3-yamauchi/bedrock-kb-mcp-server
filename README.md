# Amazon Bedrock Knowledge Base MCP Server (Unofficial)

Amazon Bedrock Knowledge Baseを管理するためのMCP（Model Context Protocol）サーバーです。

本プロジェクトでは FastMCPフレームワークを使用して Bedrock Knowledge Base に対する操作と
RAG（Retrieval-Augmented Generation）機能を提供しています。

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/r3-yamauchi/bedrock-kb-mcp-server)

## リポジトリ

https://github.com/r3-yamauchi/bedrock-kb-mcp-server

## 起動方法

```bash
uvx --from git+https://github.com/r3-yamauchi/bedrock-kb-mcp-server bedrock-kb-mcp-server
```

## 主な機能

- **Knowledge Base管理**: 作成、一覧取得、詳細取得、更新（敢えて削除機能は実装していません）
  - ストレージタイプは S3 のみをサポート
  - カスタムパーシング設定とチャンキング設定のサポート
- **データソース管理**: 作成、一覧取得（敢えて削除機能は実装していません）
  - カスタムパーシング設定とチャンキング設定のサポート
- **データ取り込みジョブ**: 開始、ステータス確認
- **RAGクエリ**: Knowledge Baseに対する検索クエリの実行
- **S3ドキュメント管理**: アップロード、一覧取得

## プロジェクト構造

```text
bedrock-kb-mcp-server/
├── pyproject.toml              # プロジェクト設定と依存関係
├── README.md                   # プロジェクトドキュメント
├── LICENSE                     # MITライセンス
├── .gitignore                  # Git除外設定
└── src/
    └── bedrock_kb_mcp_server/
        ├── __init__.py         # パッケージ初期化ファイル
        ├── main.py             # MCPサーバーのメインエントリーポイント
        ├── bedrock_client.py   # AWS Bedrock APIクライアントラッパー
        ├── models.py           # Pydanticモデル（バリデーションと型定義）
        ├── types.py            # TypedDict定義（型ヒントの改善）
        └── utils.py            # ユーティリティ関数（設定、エラーハンドリング、ログ、ARN正規化）
```

## 技術スタック

### コアライブラリ

- **FastMCP** (`>=0.1.0`): MCPサーバーを構築するためのフレームワーク
- **boto3** (`>=1.26.0`): AWS SDK for Python - AWSサービスとの通信に使用
- **pydantic** (`>=2.0.0`): データバリデーションと設定管理

### 開発ツール

- **pytest** (`>=7.0`): テストフレームワーク
- **pytest-asyncio** (`>=0.21.0`): 非同期テストサポート
- **black** (`>=23.0`): コードフォーマッター
- **ruff** (`>=0.1.0`): 高速なPythonリンター
- **mypy** (`>=1.0`): 静的型チェッカー

### Python要件

- **Python 3.12以上**が必要です

## クイックスタート

### 前提条件

- Python 3.12以上がインストールされていること
- `uv`がインストールされていること
- AWSアカウントと適切な認証情報が設定されていること

### 1. 依存関係のインストール

プロジェクトのルートディレクトリで以下のコマンドを実行します：

```bash
uv sync
```

開発環境の場合は：

```bash
uv sync --all-extras
```

### 2. AWS認証情報の設定

以下のいずれかの方法でAWS認証情報を設定します：

#### 方法1: AWSプロファイルを使用（推奨）

```bash
export AWS_PROFILE=your-profile-name
export AWS_REGION=us-east-1
```

#### 方法2: 環境変数で直接設定

```bash
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key
export AWS_REGION=us-east-1
```

#### 方法3: AWS CLIで設定済みの場合

AWS CLIで`aws configure`を実行して設定済みの場合は、追加の設定は不要です。

### 3. 環境変数の設定（オプション）

ログレベルや構造化ログの設定を行います：

```bash
# ログレベルを設定（DEBUG, INFO, WARNING, ERROR, CRITICAL）
export FASTMCP_LOG_LEVEL=INFO

# 構造化ログ（JSON形式）を使用する場合
export FASTMCP_STRUCTURED_LOG=false
```

### 4. サーバーの起動

以下のコマンドでサーバーを起動します：

```bash
uv run bedrock-kb-mcp-server
```

正常に起動すると、以下のようなログが表示されます：

```
2024-01-01 12:00:00,000 - bedrock_kb_mcp_server.main - INFO - Starting Amazon Bedrock Knowledge Base MCP Server
```

### 5. 動作確認

MCP Serverは標準入力（stdin）からJSON-RPC形式のリクエストを受け取り、標準出力（stdout）にJSON-RPC形式のレスポンスを返します。

#### 動作確認方法1: サーバーが起動していることを確認

サーバーを起動すると、以下のようなログが表示されます。このログが表示されれば、サーバーは正常に起動しています。

#### 動作確認方法2: MCPクライアントを使用（推奨）

MCP対応のクライアント（例: Claude Desktop、Cursor IDEなど）を使用して接続します。

**Claude Desktopの場合**:
1. `~/Library/Application Support/Claude/claude_desktop_config.json`を編集
2. MCP Serverを追加：

```json
{
  "mcpServers": {
    "bedrock-kb-mcp-server": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/bedrock-kb-mcp-server", "bedrock-kb-mcp-server"],
      "env": {
        "AWS_PROFILE": "your-profile-name",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

**Cursor IDEの場合**:
1. 設定からMCP Serverを追加
2. コマンドパスと環境変数を設定

#### 動作確認方法3: テストスクリプトを使用

プロジェクトに含まれている`test_mcp_server.py`を使用：

```bash
python3 test_mcp_server.py
```

注意: このスクリプトはサーバーが起動してリクエストに応答することを確認しますが、実際のAWS API呼び出しは行いません。

## インストール

```bash
uv sync
```

開発環境の場合は：

```bash
uv sync --all-extras
```

## 使用方法

### 環境変数の設定

以下の環境変数を設定する必要があります：

- `AWS_PROFILE`: AWSプロファイル名（認証情報の管理に使用）
- `AWS_REGION`: AWSリージョン（例: `us-east-1`、デフォルト: `us-east-1`）
- `FASTMCP_LOG_LEVEL`: ログレベル（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`、デフォルト: `INFO`）
- `FASTMCP_STRUCTURED_LOG`: 構造化ログ（JSON形式）を使用するか（`true`/`false`、デフォルト: `false`）

### サーバーの起動

```bash
uv run bedrock-kb-mcp-server
```

## 主要コンポーネント

### 1. `bedrock_client.py` - AWS Bedrock APIクライアント

AWS Bedrock Knowledge Base APIとの低レベルな通信を担当するラッパークラスです。

#### `BedrockKBClient` クラス

環境変数`AWS_REGION`からリージョンを取得し、以下の3つのAWSクライアントを初期化します：
- `bedrock-agent`: Knowledge Baseとデータソースの管理用
- `bedrock-agent-runtime`: RAGクエリ実行用
- `s3`: S3ドキュメント管理用

すべてのクライアントには以下の設定が適用されます：
- リトライ設定（最大3回、adaptiveモード）
- 接続タイムアウト（10秒）
- 読み取りタイムアウト（30秒）

#### 主要メソッド

##### Knowledge Base管理
- `create_knowledge_base()`: 新しいKnowledge Baseを作成
- `list_knowledge_bases()`: すべてのKnowledge Baseを一覧取得（ページネーション対応）
- `get_knowledge_base()`: 特定のKnowledge Baseの詳細情報を取得
- `update_knowledge_base()`: Knowledge Baseの名前、説明、IAMロールを更新

**データソース管理**
- `create_data_source()`: Knowledge Baseにデータソースを追加
- `list_data_sources()`: 指定されたKnowledge Baseのデータソース一覧を取得

##### データ取り込みジョブ管理
- `start_ingestion_job()`: データソースからKnowledge Baseへのデータ取り込みジョブを開始
- `get_ingestion_job()`: 取り込みジョブのステータスと統計情報を取得

**RAGクエリ**
- `retrieve()`: Knowledge Baseに対してRAGクエリを実行（結果数1-100を指定可能）

**S3ドキュメント管理**
- `upload_document_to_s3()`: ローカルファイルをS3バケットにアップロード
- `list_s3_documents()`: S3バケット内のドキュメント一覧を取得（プレフィックスでフィルタリング可能）

### 2. `main.py` - MCPサーバーメイン

FastMCPフレームワークを使用してMCPサーバーを構築し、`BedrockKBClient`の機能をMCPツールとして公開します。

#### MCPツール

##### Knowledge Base管理ツール
- `create_knowledge_base`: Knowledge Baseを作成
  - ストレージタイプ: S3、S3_VECTORS
  - 埋め込みモデル: Amazon Titan、Cohere、Amazon Nova Multimodal Embeddings v1
  - パーシング設定: BEDROCK_FOUNDATION_MODEL、BEDROCK_DATA_AUTOMATION
  - チャンキング設定: FIXED_SIZE、HIERARCHICAL、SEMANTIC、NONE
  - マルチモーダルストレージ設定（supplementalDataStorageConfiguration）
  - S3 ARN形式とS3 URI形式の両方をサポート
  - IAMロールARNのアカウントID自動補完
- `list_knowledge_bases`: すべてのKnowledge Baseを一覧取得
- `get_knowledge_base`: 特定のKnowledge Baseの詳細を取得
- `update_knowledge_base`: Knowledge Baseを更新

##### データソース管理ツール
- `create_data_source`: データソースを作成
  - パーシング設定とチャンキング設定のサポート
  - S3 ARN形式とS3 URI形式の両方をサポート
- `list_data_sources`: データソース一覧を取得

##### データ取り込みツール
- `start_ingestion_job`: 取り込みジョブを開始
- `get_ingestion_job`: 取り込みジョブのステータスを取得

##### RAGクエリツール
- `retrieve`: Knowledge Baseに対してRAGクエリを実行

##### S3ドキュメント管理ツール
- `upload_document_to_s3`: S3にドキュメントをアップロード
- `list_s3_documents`: S3バケット内のドキュメント一覧を取得

### 3. `models.py` - Pydanticモデル

リクエスト/レスポンスのバリデーションと型安全性を提供するPydanticモデルを定義します。

- `StorageType`: ストレージタイプの列挙型（S3, S3_VECTORS）
- `SourceType`: データソースタイプの列挙型（S3）
- `ParsingStrategy`: パーシング戦略の列挙型（BEDROCK_FOUNDATION_MODEL, BEDROCK_DATA_AUTOMATION）
- `ChunkingStrategy`: チャンキング戦略の列挙型（FIXED_SIZE, HIERARCHICAL, SEMANTIC, NONE）
- `ParsingConfiguration`: パーシング設定モデル
- `ChunkingConfiguration`: チャンキング設定モデル
- `VectorIngestionConfiguration`: ベクトル取り込み設定モデル
- `CreateKnowledgeBaseRequest`: Knowledge Base作成リクエストのバリデーション
  - S3 URI形式のサポート（自動的にARN形式に変換）
  - IAMロールARNのアカウントID自動補完
- `CreateDataSourceRequest`: データソース作成リクエストのバリデーション
  - S3 URI形式のサポート（自動的にARN形式に変換）
- 各種レスポンスモデル

### 4. `types.py` - TypedDict定義

APIレスポンスの型安全性を向上させるためのTypedDict定義を提供します。

- `KnowledgeBaseResponseDict`: Knowledge Base作成/更新レスポンス
- `DataSourceResponseDict`: データソース作成レスポンス
- `IngestionJobResponseDict`: 取り込みジョブレスポンス
- その他のレスポンス型定義

### 5. `utils.py` - ユーティリティ関数

設定管理、エラーハンドリング、ログ出力、ARN正規化などの共通機能を提供します。

- `validate_aws_credentials()`: AWS認証情報の検証
- `get_log_level()`: ログレベルの安全な取得
- `handle_errors()`: エラーハンドリングデコレータ（AWS APIエラーの適切な処理）
  - 10種類以上のAWSエラーコードに対応
  - AWSリクエストIDを含む詳細なエラー情報
- `get_aws_account_id()`: STSを使用してAWSアカウントIDを取得
- `normalize_s3_arn_or_uri()`: S3 URI形式をARN形式に変換
- `normalize_iam_role_arn()`: IAMロールARNのアカウントIDを自動補完
- `validate_required_string()`: 必須文字列パラメータのバリデーション共通化
- `StructuredFormatter`: 構造化ログフォーマッター（JSON形式）
- `sanitize_log_data()`: 機密情報のマスキング
- `setup_logging()`: ロギング設定の一元管理

## ワークフロー例

### 1. Knowledge Baseの作成と設定

1. S3バケットにドキュメントをアップロード

   ```python
   upload_document_to_s3(local_file_path, bucket_name, s3_key)
   ```

2. Knowledge Baseを作成（S3 URI形式とIAMロールARNの短縮形式を使用可能）

   ```python
   # 基本的なKnowledge Base
   create_knowledge_base(
       name="My Knowledge Base",
       description="Example KB",
       role_arn="role/BedrockKBRole",  # アカウントIDなし形式（自動補完）
       storage_type="S3",
       bucket_arn="s3://my-bucket"  # S3 URI形式
   )
   
   # S3 Vectorsを使用したKnowledge Base
   create_knowledge_base(
       name="Vector KB",
       description="Vector search enabled KB",
       role_arn="arn:aws:iam::123456789012:role/BedrockKBRole",
       storage_type="S3_VECTORS",
       bucket_arn="s3://vector-bucket",
       embedding_model_arn="arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
   )
   
   # マルチモーダルKnowledge Base（Amazon Nova Multimodal Embeddings v1）
   create_knowledge_base(
       name="Multimodal KB",
       description="KB with Nova Multimodal Embeddings",
       role_arn="role/BedrockKBRole",
       storage_type="S3_VECTORS",
       bucket_arn="s3://vector-bucket",
       embedding_model_arn="arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-2-multimodal-embeddings-v1:0",
       multimodal_storage_s3_uri="s3://multimodal-storage-bucket/"
   )
   
   # カスタムパーシングとチャンキング設定を使用
   create_knowledge_base(
       name="Custom KB",
       description="KB with custom parsing and chunking",
       role_arn="role/BedrockKBRole",
       storage_type="S3",
       bucket_arn="s3://my-bucket",
       parsing_strategy="BEDROCK_FOUNDATION_MODEL",
       parsing_model_arn="arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
       parsing_modality="MULTIMODAL",
       chunking_strategy="FIXED_SIZE",
       chunking_max_tokens=1000,
       chunking_overlap_percentage=20
   )
   ```

3. データソースを作成（S3 URI形式とカスタム設定を使用可能）

   ```python
   # 基本的なデータソース
   create_data_source(
       knowledge_base_id="KB123",
       name="My Data Source",
       source_type="S3",
       bucket_arn="s3://my-bucket"  # S3 URI形式
   )
   
   # カスタムパーシングとチャンキング設定を使用
   create_data_source(
       knowledge_base_id="KB123",
       name="Custom Data Source",
       source_type="S3",
       bucket_arn="s3://my-bucket",
       parsing_strategy="BEDROCK_FOUNDATION_MODEL",
       parsing_model_arn="arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
       chunking_strategy="FIXED_SIZE",
       chunking_max_tokens=1000,
       chunking_overlap_percentage=20
   )
   ```

4. データ取り込みジョブを開始

   ```python
   start_ingestion_job(knowledge_base_id, data_source_id)
   ```

5. ジョブのステータスを確認

   ```python
   get_ingestion_job(knowledge_base_id, data_source_id, ingestion_job_id)
   ```

### 2. RAGクエリの実行

1. Knowledge Baseに対してクエリを実行

   ```python
   retrieve(knowledge_base_id, query, number_of_results)
   ```

2. 結果には関連ドキュメントと引用情報が含まれます

## アーキテクチャの特徴

### 1. レイヤードアーキテクチャ

- **プレゼンテーション層**: `main.py` - MCPツールの定義と公開
- **ビジネスロジック層**: `bedrock_client.py` - AWS APIとの通信
- **データ層**: `models.py` - データバリデーションと型定義

### 2. エラーハンドリング

- すべてのAWS API呼び出しは`ClientError`を適切に処理
- 10種類以上のAWSエラーコードに対応（InternalServerException、InvalidParameterException、ResourceNotFoundExceptionなど）
- AWSリクエストIDを含む詳細なエラー情報
- エラーコードに応じた日本語メッセージを提供
- エラー情報はログに記録され、ユーザーには分かりやすいメッセージが返却される

### 3. ロギング

- **標準ログ**: 人間が読みやすい形式（デフォルト）
- **構造化ログ**: JSON形式で出力可能（`FASTMCP_STRUCTURED_LOG=true`で有効化）
- **機密情報の自動マスキング**: ARN、認証情報などが自動的にマスクされる
- 環境変数でログレベルを制御可能

### 4. 型安全性

- Pydanticを使用したデータバリデーション
- TypedDictを使用したAPIレスポンスの型定義
- すべてのMCPツール関数とBedrockKBClientメソッドの戻り値型を具体的に定義
- 型ヒントの活用
- mypyによる静的型チェック対応
- IDEの補完機能と型安全性が向上

### 5. 入力バリデーションと正規化

- ARN形式とURI形式の両方をサポート
  - S3 ARN形式: `arn:aws:s3:::bucket-name`
  - S3 URI形式: `s3://bucket-name` または `s3://bucket-name/path`（自動的にARN形式に変換）
  - IAMロールARN: 完全な形式または短縮形式（アカウントIDを自動補完）
- 必須フィールドのチェック
- ストレージタイプ、パーシング戦略、チャンキング戦略の列挙型による型安全性の向上
- Pydanticモデルによる包括的なバリデーション

### 6. リトライロジック

- AWS API呼び出しにリトライメカニズムを実装
- 適応的リトライモード（adaptive）を使用
- 一時的なネットワークエラーやレート制限エラーに対する自動リトライ

## セキュリティ考慮事項

1. **AWS認証情報**: 環境変数`AWS_PROFILE`を使用して認証情報を管理
2. **IAMロール**: Knowledge Baseには適切なIAMロールが必要
3. **S3アクセス**: S3バケットへのアクセス権限が必要
4. **リージョン設定**: 適切なAWSリージョンを指定
5. **機密情報のマスキング**: ログ出力時にARN、認証情報などが自動的にマスクされる

## トラブルシューティング

### よくある問題

1. **AWS認証エラー**
   - `AWS_PROFILE`が正しく設定されているか確認
   - AWS認証情報が有効か確認
   - boto3が自動的に認証情報を取得する場合もあるため（IAMロール、EC2インスタンスプロファイル）、明示的な設定がなくても動作する場合があります

2. **リージョンエラー**
   - `AWS_REGION`が正しく設定されているか確認
   - Bedrockがそのリージョンで利用可能か確認

3. **権限エラー**
   - IAMロールに必要な権限があるか確認
   - S3バケットへのアクセス権限があるか確認

4. **取り込みジョブの失敗**
   - データソースの設定を確認
   - S3バケット内のドキュメント形式を確認

5. **バリデーションエラー**
   - ARN形式が正しい場合、エラーメッセージを確認
   - 必須フィールドがすべて指定されているか確認

### エラー: AWS認証情報が見つからない

```
WARNING - AWS認証情報が明示的に設定されていません。
```

**解決方法**: AWS認証情報を設定してください（クイックスタートの手順2を参照）

### エラー: モジュールが見つからない

```
ModuleNotFoundError: No module named 'fastmcp'
```

**解決方法**: 依存関係をインストールしてください

```bash
uv sync
```

### エラー: Pythonバージョンが古い

```
ERROR: This package requires Python >=3.12
```

**解決方法**: Python 3.12以上をインストールしてください

### サーバーが起動しない

- ログレベルを`DEBUG`に設定して詳細なログを確認：

```bash
export FASTMCP_LOG_LEVEL=DEBUG
uv run bedrock-kb-mcp-server
```

- 構造化ログを有効にしてJSON形式で確認：

```bash
export FASTMCP_STRUCTURED_LOG=true
uv run bedrock-kb-mcp-server
```

## 実際の使用例

### Knowledge Baseの一覧を取得

MCPクライアントから`list_knowledge_bases`ツールを呼び出すと、AWSアカウント内のすべてのKnowledge Baseが返されます。

### Knowledge Baseを作成

```json
{
  "name": "my-knowledge-base",
  "description": "テスト用のKnowledge Base",
  "role_arn": "role/BedrockKnowledgeBaseRole",
  "storage_type": "S3",
  "bucket_arn": "s3://my-documents-bucket"
}
```

**注意**: 
- `role_arn`は短縮形式（`role/ROLE_NAME`）も使用可能で、アカウントIDが自動補完されます
- `bucket_arn`はS3 URI形式（`s3://bucket-name`）も使用可能で、自動的にARN形式に変換されます

### RAGクエリを実行

```json
{
  "knowledge_base_id": "YOUR_KB_ID",
  "query": "ドキュメントの内容について教えてください",
  "number_of_results": 5
}
```

## 注意事項

- 実際のAWS APIを呼び出すため、適切なAWS認証情報とIAM権限が必要です
- Knowledge Baseの作成には、適切なIAMロールが必要です
- S3バケットへのアクセス権限が必要です
- リージョンによってはBedrockが利用できない場合があります

## 開発

### コードフォーマット

```bash
black src/
ruff check src/
mypy src/
```

### テスト（今後実装予定）

```bash
pytest
```

## ライセンス

MIT License - see [LICENSE](LICENSE) file for details.
