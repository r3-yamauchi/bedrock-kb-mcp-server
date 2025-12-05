"""
Amazon Bedrock Knowledge Base MCP Server パッケージ

このパッケージは、Amazon Bedrock Knowledge Baseを管理するための
MCP (Model Context Protocol) サーバーを提供します。

MCPは、AIアシスタントやLLMアプリケーションが外部リソースやツールに
アクセスするための標準化されたプロトコルです。

主な機能:
- Knowledge BaseのCRUD操作
- データソースの管理
- データ取り込みジョブの管理
- RAGクエリの実行
- S3ドキュメントの管理
"""

# パッケージのバージョン情報
# セマンティックバージョニングに従って管理されます
# メジャー.マイナー.パッチの形式（例: 0.1.0）
__version__ = "0.1.0"

# パッケージの作成者情報
__author__ = "r3-yamauchi"
