"""
Amazon Bedrock Knowledge Base MCPサーバーのメインモジュール

FastMCPフレームワークを使用してMCPサーバーを構築し、
Bedrock Knowledge Baseの管理機能をMCPツールとして公開します。

このモジュールは以下の機能を提供します:
- Knowledge BaseのCRUD操作
- データソースの管理
- データ取り込みジョブの管理
- RAGクエリの実行
- S3ドキュメントの管理
"""

import logging
from typing import Dict, Any

from fastmcp import FastMCP

from bedrock_kb_mcp_server import __version__
from bedrock_kb_mcp_server.bedrock_client import BedrockKBClient
from bedrock_kb_mcp_server.models import (
    StorageType,
    SourceType,
    ParsingStrategy,
    ChunkingStrategy,
    CreateKnowledgeBaseRequest,
    CreateDataSourceRequest,
    ParsingConfiguration,
    ChunkingConfiguration,
    VectorIngestionConfiguration,
)
from bedrock_kb_mcp_server.types import (
    KnowledgeBaseResponseDict,
    KnowledgeBaseListResponseDict,
    KnowledgeBaseDetailDict,
    DataSourceResponseDict,
    DataSourceListResponseDict,
    IngestionJobResponseDict,
    RetrieveResponseDict,
    S3UploadResponseDict,
    S3DocumentListResponseDict,
    S3BucketCreateResponseDict,
    IAMRoleCreateResponseDict,
)
from bedrock_kb_mcp_server.utils import (
    validate_aws_credentials,
    setup_logging,
    handle_errors,
    validate_required_string,
)

# ============================================================================
# ロギング設定
# ============================================================================

# ロギングを設定（構造化ログは環境変数FASTMCP_STRUCTURED_LOGで制御）
# この時点でロギングが初期化され、以降のログ出力が可能になります
# 構造化ログ（JSON形式）を使用する場合は、環境変数FASTMCP_STRUCTURED_LOG=trueを設定
setup_logging()
# このモジュール専用のロガーを取得
# ログメッセージにはモジュール名（bedrock_kb_mcp_server.main）が含まれます
logger = logging.getLogger(__name__)

# ============================================================================
# AWS認証情報の検証
# ============================================================================

# AWS認証情報が設定されているか確認（警告のみ、エラーにはしない）
# boto3は自動的に認証情報を取得する場合もあるため（IAMロール、EC2インスタンスプロファイルなど）、
# 認証情報が明示的に設定されていなくてもエラーにはしません
# ただし、実際のAPI呼び出し時に認証情報がない場合はエラーが発生します
try:
    validate_aws_credentials()
except Exception as e:
    # 認証情報の検証でエラーが発生しても、サーバーの起動は続行します
    # 実際のAPI呼び出し時に認証エラーが発生する可能性があることを警告します
    logger.warning(f"AWS credentials validation: {e}")

# ============================================================================
# MCPサーバーの初期化
# ============================================================================

# FastMCPサーバーを初期化
# サーバー名とバージョンを指定してFastMCPインスタンスを作成
# サーバー名はMCPクライアントが識別するために使用されます
# バージョン情報はAPIレスポンスに含まれ、クライアントが機能の互換性を判断する際に使用されます
mcp = FastMCP("bedrock-kb-mcp-server", __version__)

# ============================================================================
# Bedrockクライアントの初期化
# ============================================================================

# Bedrock Knowledge Base APIクライアントを初期化
# このクライアントは、すべてのMCPツール関数から共有して使用されます
# AWS認証情報は環境変数またはAWS設定ファイルから自動的に取得されます
# リージョンは環境変数AWS_REGIONから取得されます（デフォルト: us-east-1）
bedrock_client = BedrockKBClient()


# ============================================================================
# Knowledge Base Management Tools
# ============================================================================


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def create_knowledge_base(
    name: str,
    description: str,
    role_arn: str,
    storage_type: str = "S3",
    bucket_arn: str = "",
    embedding_model_arn: str = "",
    region: str = "us-east-1",
    # パーシング設定（オプション）
    parsing_strategy: str = "",
    parsing_model_arn: str = "",
    parsing_modality: str = "",
    parsing_prompt_text: str = "",
    # チャンキング設定（オプション）
    chunking_strategy: str = "",
    chunking_max_tokens: int = 0,
    chunking_overlap_percentage: int = 0,
    chunking_overlap_tokens: int = 0,
    chunking_buffer_size: int = 0,
    chunking_breakpoint_threshold: int = 0,
    # マルチモーダルストレージ設定（オプション）
    multimodal_storage_s3_uri: str = "",
) -> KnowledgeBaseResponseDict:
    """
    新しいAmazon Bedrock Knowledge Baseを作成します。
    
    Args:
        name: Knowledge Baseの名前（1-100文字）
        description: Knowledge Baseの説明（1文字以上）
        role_arn: Knowledge Baseが使用するIAMロールのARN
            - 完全な形式: "arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME"
            - アカウントIDなし: "arn:aws:iam::role/ROLE_NAME" または "role/ROLE_NAME"（自動補完）
        storage_type: ストレージタイプ
            - 'S3': 標準的なS3ストレージ（デフォルト）
            - 'S3_VECTORS': S3 Vectorsを使用したベクトル検索対応ストレージ
        bucket_arn: ドキュメントを保存するS3バケットのARNまたはS3 URI
            - ARN形式: "arn:aws:s3:::BUCKET_NAME"
            - URI形式: "s3://BUCKET_NAME" または "s3://BUCKET_NAME/path"
            S3_VECTORSの場合はベクトルバケットARNまたはURIを指定
        region: Knowledge Baseを作成する先のリージョン（デフォルト: "us-east-1"）
            例: "us-east-1", "ap-northeast-1"
            注意: Knowledge Baseのリージョンは作成時に決定され、後から変更できません
        embedding_model_arn: 埋め込みモデルのARN（S3_VECTORSタイプの場合必須）
            形式: "arn:aws:bedrock:REGION::foundation-model/MODEL_ID"
            
            サポートされている埋め込みモデル:
            - Amazon Titan Embeddings G1 - Text:
              "arn:aws:bedrock:REGION::foundation-model/amazon.titan-embed-text-v1"
              （ベクトル次元数: 1536、タイプ: Floating-point）
            
            - Amazon Titan Text Embeddings V2:
              "arn:aws:bedrock:REGION::foundation-model/amazon.titan-embed-text-v2:0"
              （ベクトル次元数: 256, 512, 1024、タイプ: Floating-point, binary）
            
            - Cohere Embed Multilingual:
              "arn:aws:bedrock:REGION::foundation-model/cohere.embed-multilingual-v3"
              （ベクトル次元数: 1024、タイプ: Floating-point, binary）
            
            - Amazon Nova Multimodal Embeddings v1:
              "arn:aws:bedrock:REGION::foundation-model/amazon.nova-2-multimodal-embeddings-v1:0"
              （ベクトル次元数: 1024、タイプ: Floating-point）
              （マルチモーダル対応: テキスト、画像、動画、音声を処理可能）
              注意: マルチモーダルコンテンツを処理する場合は、supplementalDataStorageConfiguration
              でマルチモーダルストレージ先を指定する必要があります
            
            例: "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
            注意: リージョンは実際に使用するリージョンに置き換えてください
        
        パーシング設定（オプション）:
        parsing_strategy: パーシング戦略
            - 'BEDROCK_FOUNDATION_MODEL': Foundation Modelを使用したパーシング
              （マルチモーダルデータ（画像、表、グラフなど）を処理可能、プロンプトカスタマイズ可能）
            - 'BEDROCK_DATA_AUTOMATION': Bedrock Data Automationを使用したパーシング
              （マルチモーダルデータを処理可能、完全マネージド、追加プロンプト不要）
            注意: 指定しない場合はデフォルトパーサーが使用されます（テキストのみ、無料）
        parsing_model_arn: Foundation ModelのARN（parsing_strategy='BEDROCK_FOUNDATION_MODEL'の場合必須）
            例: "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            サポートされているモデル: Claude 3 Sonnet, Claude 3 Opus, Claude 3 Haikuなど
        parsing_modality: マルチモーダル設定
            - 'MULTIMODAL': テキストと画像の両方を処理（オプション）
        parsing_prompt_text: パーシングプロンプトのテキスト（オプション）
            Foundation Modelにドキュメントの解釈方法を指示するテキスト
            例: "Extract all text, tables, and figures from this document."
        
        チャンキング設定（オプション）:
        chunking_strategy: チャンキング戦略
            - 'FIXED_SIZE': 固定サイズのチャンクに分割（推奨: max_tokens=1000, overlap_percentage=20）
            - 'HIERARCHICAL': 階層的なチャンクに分割（大きなチャンクと小さなチャンクの2層）
            - 'SEMANTIC': セマンティックなチャンクに分割（NLPを使用して類似コンテンツでグループ化）
            - 'NONE': チャンクに分割しない（各ファイルが1つのチャンクとして扱われる）
            注意: 指定しない場合はデフォルトのチャンキングが使用されます
        chunking_max_tokens: 最大トークン数（chunking_strategy='FIXED_SIZE'または'SEMANTIC'の場合に使用）
            - FIXED_SIZE: 1以上（推奨: 500-2000）
            - SEMANTIC: 1以上（推奨: 1000-3000）
        chunking_overlap_percentage: オーバーラップ率（chunking_strategy='FIXED_SIZE'の場合に使用）
            範囲: 1-99（推奨: 10-30）
            隣接するチャンク間で重複するトークンの割合
        chunking_overlap_tokens: オーバーラップトークン数（chunking_strategy='HIERARCHICAL'の場合に使用）
            階層チャンキングで使用する重複トークン数
        chunking_buffer_size: バッファサイズ（chunking_strategy='SEMANTIC'の場合に使用）
            範囲: 0-1（推奨: 1）
            文を比較する際の移動コンテキストウィンドウのサイズ
        chunking_breakpoint_threshold: ブレークポイントのパーセンタイル閾値（chunking_strategy='SEMANTIC'の場合に使用）
            範囲: 50-99（推奨: 80-95）
            チャンクを分割するための類似度閾値（低いほど多くのチャンクが作成される）

    Returns:
        KnowledgeBaseResponseDict: Knowledge Baseの作成結果
            - knowledge_base_id: 作成されたKnowledge BaseのID
            - status: Knowledge Baseのステータス（'CREATING', 'ACTIVE', 'FAILED'など）
            - arn: Knowledge BaseのARN（オプション）
    
    Raises:
        ValueError: 入力値が無効な場合（バリデーションエラー）
            - storage_typeが無効な値の場合
            - S3_VECTORSタイプでembedding_model_arnが指定されていない場合
            - parsing_strategy='BEDROCK_FOUNDATION_MODEL'でparsing_model_arnが指定されていない場合
            - ARN形式が無効な場合
    
    Examples:
        # 基本的なKnowledge Baseの作成（デフォルト設定）
        create_knowledge_base(
            name="My Knowledge Base",
            description="Example KB",
            role_arn="arn:aws:iam::123456789012:role/BedrockKBRole",
            storage_type="S3",
            bucket_arn="s3://my-bucket"  # S3 URI形式も使用可能
        )
        
        # S3 Vectorsを使用したKnowledge Baseの作成
        create_knowledge_base(
            name="Vector KB",
            description="Vector search enabled KB",
            role_arn="role/BedrockKBRole",  # アカウントIDなし形式も使用可能（自動補完）
            storage_type="S3_VECTORS",
            bucket_arn="s3://vector-bucket",  # S3 URI形式も使用可能
            embedding_model_arn="arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        )
        
        # カスタムパーシングとチャンキング設定を使用
        create_knowledge_base(
            name="Custom KB",
            description="KB with custom parsing and chunking",
            role_arn="arn:aws:iam::123456789012:role/BedrockKBRole",
            storage_type="S3",
            bucket_arn="arn:aws:s3:::my-bucket",
            parsing_strategy="BEDROCK_FOUNDATION_MODEL",
            parsing_model_arn="arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
            parsing_modality="MULTIMODAL",
            chunking_strategy="FIXED_SIZE",
            chunking_max_tokens=1000,
            chunking_overlap_percentage=20
        )
        
        # Amazon Nova Multimodal Embeddings v1を使用したマルチモーダルKnowledge Base
        create_knowledge_base(
            name="Multimodal KB",
            description="KB with Nova Multimodal Embeddings",
            role_arn="arn:aws:iam::123456789012:role/BedrockKBRole",
            storage_type="S3_VECTORS",
            bucket_arn="arn:aws:s3:::vector-bucket",
            embedding_model_arn="arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-2-multimodal-embeddings-v1:0",
            multimodal_storage_s3_uri="s3://multimodal-storage-bucket/"
        )
    """
    # ストレージタイプのバリデーション
    # 入力された文字列をStorageType列挙型に変換して検証します
    # 無効な値の場合はValueErrorが発生し、エラーハンドリングデコレータがキャッチします
    try:
        storage_type_enum = StorageType(storage_type)
    except ValueError:
        raise ValueError(f"Invalid storage_type: {storage_type}. Must be 'S3' or 'S3_VECTORS'")
    
    # ベクトル取り込み設定を構築（オプション）
    vector_ingestion_config = None
    if parsing_strategy or chunking_strategy:
        # パーシング設定を構築
        parsing_config = None
        if parsing_strategy:
            parsing_config = ParsingConfiguration(
                parsing_strategy=ParsingStrategy(parsing_strategy),
                parsing_model_arn=parsing_model_arn if parsing_model_arn else None,
                parsing_modality=parsing_modality if parsing_modality else None,
                parsing_prompt_text=parsing_prompt_text if parsing_prompt_text else None,
            )
        
        # チャンキング設定を構築
        chunking_config = None
        if chunking_strategy:
            chunking_config = ChunkingConfiguration(
                chunking_strategy=ChunkingStrategy(chunking_strategy),
                max_tokens=chunking_max_tokens if chunking_max_tokens > 0 else None,
                overlap_percentage=chunking_overlap_percentage if chunking_overlap_percentage > 0 else None,
                overlap_tokens=chunking_overlap_tokens if chunking_overlap_tokens > 0 else None,
                buffer_size=chunking_buffer_size if chunking_buffer_size > 0 else None,
                breakpoint_percentile_threshold=chunking_breakpoint_threshold if chunking_breakpoint_threshold > 0 else None,
            )
        
        if parsing_config or chunking_config:
            vector_ingestion_config = VectorIngestionConfiguration(
                parsing_configuration=parsing_config,
                chunking_configuration=chunking_config,
            )
    
    # Pydanticモデルを使用してリクエストパラメータをバリデーション
    # この段階で、ARN形式、文字列長、必須フィールドなどの検証が行われます
    # S3_VECTORSタイプの場合、embedding_model_arnが必須であることも検証されます
    request = CreateKnowledgeBaseRequest(
        name=name,
        description=description,
        role_arn=role_arn,
        storage_type=storage_type_enum,
        bucket_arn=bucket_arn,
        embedding_model_arn=embedding_model_arn if embedding_model_arn else None,
        vector_ingestion_configuration=vector_ingestion_config,
    )
    
    # AWS API用のストレージ設定を構築
    # ストレージタイプに応じて、異なる設定構造を作成します
    if request.storage_type == StorageType.S3_VECTORS:
        # S3_VECTORSタイプの場合
        # 埋め込みモデルARNが必須であることを再確認（Pydanticでも検証済みですが、念のため）
        if not request.embedding_model_arn:
            raise ValueError("embedding_model_arn is required for S3_VECTORS storage type")
        
        # S3 Vectors用のストレージ設定を構築
        # AWS APIの仕様に従って、s3VectorsConfigurationオブジェクトを作成します
        # vectorBucketArnは、ベクトル埋め込みを保存するS3バケットのARNです
        # 注意: indexNameやindexArnは現在サポートしていません（既存インデックスを使用する場合に必要）
        storage_configuration = {
            "type": "S3_VECTORS",  # AWS APIでは"S3_VECTORS"（複数形）を使用
            "s3VectorsConfiguration": {
                "vectorBucketArn": request.bucket_arn,  # ベクトルバケットのARN
                # オプション: "indexName": "my-index",  # 既存のインデックス名（将来の拡張）
                # オプション: "indexArn": "arn:aws:bedrock:...",  # 既存のインデックスARN（将来の拡張）
            },
        }
        
        # Knowledge Base設定（埋め込みモデルを含む）
        # S3_VECTORSを使用する場合、knowledgeBaseConfigurationが必須です
        # type: "VECTOR"を指定し、埋め込みモデルのARNを設定します
        vector_kb_config: Dict[str, Any] = {
            "embeddingModelArn": request.embedding_model_arn,  # 埋め込みモデルのARN
        }
        
        # マルチモーダルストレージ設定が指定されている場合は追加
        # supplementalDataStorageConfigurationは、マルチモーダルコンテンツ（画像、動画、音声）を
        # 保存するS3バケットの場所を指定します
        # Amazon Nova Multimodal Embeddings v1を使用する場合に特に重要です
        if multimodal_storage_s3_uri:
            # S3 URI形式を検証（s3://bucket-name/path/形式であることを確認）
            multimodal_uri = multimodal_storage_s3_uri.strip()
            if not multimodal_uri.startswith("s3://"):
                raise ValueError("multimodal_storage_s3_uri must start with 's3://'")
            if len(multimodal_uri) < 7:  # "s3://" + 最低1文字
                raise ValueError("multimodal_storage_s3_uri must be a valid S3 URI")
            
            # supplementalDataStorageConfigurationを構築
            # storageLocationsは固定で1要素の配列です
            vector_kb_config["supplementalDataStorageConfiguration"] = {
                "storageLocations": [
                    {
                        "type": "S3",  # 現在はS3のみサポート
                        "s3Location": {
                            "uri": multimodal_uri  # S3 URI（例: "s3://bucket-name/path/"）
                        }
                    }
                ]
            }
        
        knowledge_base_configuration = {
            "type": "VECTOR",  # ベクトル検索を使用することを指定
            "vectorKnowledgeBaseConfiguration": vector_kb_config,
        }
    else:
        # S3タイプの場合（従来の設定）
        # 標準的なS3ストレージを使用する場合の設定
        # knowledgeBaseConfigurationは不要です（デフォルト設定が使用されます）
        storage_configuration = {
            "type": "S3",  # 標準S3ストレージ
            "s3Configuration": {"bucketArn": request.bucket_arn},  # ドキュメント保存用バケットARN
        }
        knowledge_base_configuration = None  # S3タイプでは不要

    # ベクトル取り込み設定をAWS API形式に変換
    vector_ingestion_config_dict = None
    if request.vector_ingestion_configuration:
        vector_ingestion_config_dict = request.vector_ingestion_configuration.to_api_dict()
    
    # リージョンを正規化（前後の空白を削除、空文字列の場合はus-east-1を使用）
    region_cleaned = region.strip() if region else "us-east-1"
    
    # 指定されたリージョンで一時的にクライアントを作成
    kb_client = BedrockKBClient(region=region_cleaned)
    
    # Bedrockクライアントを使用してKnowledge Baseを作成
    result = kb_client.create_knowledge_base(
        name=request.name,
        description=request.description,
        role_arn=request.role_arn,
        storage_configuration=storage_configuration,
        knowledge_base_configuration=knowledge_base_configuration,
        vector_ingestion_configuration=vector_ingestion_config_dict,
    )
    return result


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def list_knowledge_bases() -> KnowledgeBaseListResponseDict:
    """
    すべてのAmazon Bedrock Knowledge Baseの一覧を取得します。
    
    Returns:
        KnowledgeBaseListResponseDict: Knowledge Base一覧
            - count: Knowledge Baseの数
            - knowledge_bases: Knowledge Baseの詳細情報のリスト
    """
    # BedrockクライアントからすべてのKnowledge Baseを取得
    # ページネーションが自動的に処理され、すべてのKnowledge Baseが取得されます
    knowledge_bases = bedrock_client.list_knowledge_bases()
    
    # レスポンスを整形して返す
    # count: Knowledge Baseの総数
    # knowledge_bases: Knowledge Baseの詳細情報のリスト
    return {
        "count": len(knowledge_bases),
        "knowledge_bases": knowledge_bases,
    }


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def get_knowledge_base(knowledge_base_id: str) -> KnowledgeBaseDetailDict:
    """
    特定のAmazon Bedrock Knowledge Baseの詳細情報を取得します。
    
    Args:
        knowledge_base_id: Knowledge BaseのID

    Returns:
        KnowledgeBaseDetailDict: Knowledge Baseの詳細情報
            - id: Knowledge BaseのID
            - name: Knowledge Baseの名前
            - status: Knowledge Baseのステータス
            - description: Knowledge Baseの説明（オプション）
            - arn: Knowledge BaseのARN（オプション）
            - その他の設定情報
    
    Raises:
        ValueError: knowledge_base_idが空の場合
    """
    # 入力値のバリデーション（共通関数を使用）
    knowledge_base_id = validate_required_string(knowledge_base_id, "knowledge_base_id")
    
    # BedrockクライアントからKnowledge Baseの詳細を取得
    kb = bedrock_client.get_knowledge_base(knowledge_base_id)
    return kb


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def update_knowledge_base(
    knowledge_base_id: str,
    name: str = "",
    description: str = "",
    role_arn: str = "",
) -> KnowledgeBaseResponseDict:
    """
    Amazon Bedrock Knowledge Baseを更新します。
    
    Knowledge Baseの名前、説明、IAMロールを更新できます。
    空文字列のパラメータは更新されません（既存の値が保持されます）。

    Args:
        knowledge_base_id: 更新対象のKnowledge BaseのID
        name: 新しい名前（オプション、空文字列の場合は更新されない）
        description: 新しい説明（オプション、空文字列の場合は更新されない）
        role_arn: 新しいIAMロールARN（オプション、空文字列の場合は更新されない）

    Returns:
        KnowledgeBaseResponseDict: 更新されたKnowledge Baseのステータス
            - knowledge_base_id: Knowledge BaseのID
            - status: Knowledge Baseのステータス
            - arn: Knowledge BaseのARN（オプション）
    
    Raises:
        ValueError: knowledge_base_idが空の場合
    """
    # 入力値のバリデーション（共通関数を使用）
    knowledge_base_id = validate_required_string(knowledge_base_id, "knowledge_base_id")
    
    # Bedrockクライアントを使用してKnowledge Baseを更新
    # 空文字列の場合はNoneに変換して、既存の値を保持する
    result = bedrock_client.update_knowledge_base(
        knowledge_base_id=knowledge_base_id,
        name=name.strip() if name else None,
        description=description.strip() if description else None,
        role_arn=role_arn.strip() if role_arn else None,
    )
    return result


# ============================================================================
# Data Source Management Tools
# ============================================================================


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def create_data_source(
    knowledge_base_id: str,
    name: str,
    source_type: str = "S3",
    bucket_arn: str = "",
    inclusion_prefixes: str = "",
    # パーシング設定（オプション）
    parsing_strategy: str = "",
    parsing_model_arn: str = "",
    parsing_modality: str = "",
    parsing_prompt_text: str = "",
    # チャンキング設定（オプション）
    chunking_strategy: str = "",
    chunking_max_tokens: int = 0,
    chunking_overlap_percentage: int = 0,
    chunking_overlap_tokens: int = 0,
    chunking_buffer_size: int = 0,
    chunking_breakpoint_threshold: int = 0,
) -> DataSourceResponseDict:
    """
    Knowledge Baseにデータソースを作成します。
    
    データソースは、Knowledge Baseがデータを取得する場所を定義します。
    S3バケットを指定し、必要に応じて特定のプレフィックス（フォルダ）のみを
    含めることができます。パーシング設定とチャンキング設定を指定することで、
    データソースごとに異なる処理方法を適用できます。
    
    注意: Knowledge Baseの`storage_type`が`S3_VECTORS`でも、データソースの`type`は
    常に`S3`になります。これらは異なる概念です：
    - `storage_type`: Knowledge Baseのストレージ設定（S3またはS3_VECTORS）
    - `dataSourceConfiguration.type`: データソースのタイプ（S3, WEB, CONFLUENCEなど）

    Args:
        knowledge_base_id: データソースを追加するKnowledge BaseのID
        name: データソースの名前（1-100文字）
        source_type: データソースタイプ（現在は'S3'のみサポート、デフォルト: 'S3'）
        bucket_arn: データソースとして使用するS3バケットのARN（arn:aws:s3:::BUCKET_NAME形式）
        inclusion_prefixes: 含めるS3プレフィックスのカンマ区切り文字列（オプション）
            例: "documents/,images/" のように複数のプレフィックスを指定可能
            空文字列の場合はバケット内のすべてのオブジェクトが対象
        
        パーシング設定（オプション）:
        parsing_strategy: パーシング戦略
            - 'BEDROCK_FOUNDATION_MODEL': Foundation Modelを使用したパーシング
              （マルチモーダルデータ（画像、表、グラフなど）を処理可能、プロンプトカスタマイズ可能）
            - 'BEDROCK_DATA_AUTOMATION': Bedrock Data Automationを使用したパーシング
              （マルチモーダルデータを処理可能、完全マネージド、追加プロンプト不要）
            注意: 指定しない場合はKnowledge Baseのデフォルト設定が使用されます
        parsing_model_arn: Foundation ModelのARN（parsing_strategy='BEDROCK_FOUNDATION_MODEL'の場合必須）
            例: "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            サポートされているモデル: Claude 3 Sonnet, Claude 3 Opus, Claude 3 Haikuなど
        parsing_modality: マルチモーダル設定
            - 'MULTIMODAL': テキストと画像の両方を処理（オプション）
        parsing_prompt_text: パーシングプロンプトのテキスト（オプション）
            Foundation Modelにドキュメントの解釈方法を指示するテキスト
            例: "Extract all text, tables, and figures from this document."
        
        チャンキング設定（オプション）:
        chunking_strategy: チャンキング戦略
            - 'FIXED_SIZE': 固定サイズのチャンクに分割（推奨: max_tokens=1000, overlap_percentage=20）
            - 'HIERARCHICAL': 階層的なチャンクに分割（大きなチャンクと小さなチャンクの2層）
            - 'SEMANTIC': セマンティックなチャンクに分割（NLPを使用して類似コンテンツでグループ化）
            - 'NONE': チャンクに分割しない（各ファイルが1つのチャンクとして扱われる）
            注意: 指定しない場合はKnowledge Baseのデフォルト設定が使用されます
        chunking_max_tokens: 最大トークン数（chunking_strategy='FIXED_SIZE'または'SEMANTIC'の場合に使用）
            - FIXED_SIZE: 1以上（推奨: 500-2000）
            - SEMANTIC: 1以上（推奨: 1000-3000）
        chunking_overlap_percentage: オーバーラップ率（chunking_strategy='FIXED_SIZE'の場合に使用）
            範囲: 1-99（推奨: 10-30）
            隣接するチャンク間で重複するトークンの割合
        chunking_overlap_tokens: オーバーラップトークン数（chunking_strategy='HIERARCHICAL'の場合に使用）
            階層チャンキングで使用する重複トークン数
        chunking_buffer_size: バッファサイズ（chunking_strategy='SEMANTIC'の場合に使用）
            範囲: 0-1（推奨: 1）
            文を比較する際の移動コンテキストウィンドウのサイズ
        chunking_breakpoint_threshold: ブレークポイントのパーセンタイル閾値（chunking_strategy='SEMANTIC'の場合に使用）
            範囲: 50-99（推奨: 80-95）
            チャンクを分割するための類似度閾値（低いほど多くのチャンクが作成される）

    Returns:
        DataSourceResponseDict: データソースの作成結果
            - data_source_id: 作成されたデータソースのID
            - status: データソースのステータス（'CREATING', 'ACTIVE', 'FAILED'など）
    
    Raises:
        ValueError: 入力値が無効な場合（source_typeが無効、バリデーションエラーなど）
            - source_typeが'S3'以外の場合
            - parsing_strategy='BEDROCK_FOUNDATION_MODEL'でparsing_model_arnが指定されていない場合
            - ARN形式が無効な場合
    
    Examples:
        # 基本的なデータソースの作成（デフォルト設定）
        create_data_source(
            knowledge_base_id="KB123",
            name="My Data Source",
            source_type="S3",
            bucket_arn="arn:aws:s3:::my-bucket"
        )
        
        # 特定のプレフィックスのみを含めるデータソース
        create_data_source(
            knowledge_base_id="KB123",
            name="Documents Only",
            source_type="S3",
            bucket_arn="arn:aws:s3:::my-bucket",
            inclusion_prefixes="documents/,pdfs/"
        )
        
        # カスタムパーシングとチャンキング設定を使用
        create_data_source(
            knowledge_base_id="KB123",
            name="Custom Data Source",
            source_type="S3",
            bucket_arn="arn:aws:s3:::my-bucket",
            parsing_strategy="BEDROCK_FOUNDATION_MODEL",
            parsing_model_arn="arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
            parsing_modality="MULTIMODAL",
            chunking_strategy="FIXED_SIZE",
            chunking_max_tokens=1000,
            chunking_overlap_percentage=20
        )
    """
    # データソースタイプのバリデーション
    try:
        source_type_enum = SourceType(source_type)
    except ValueError:
        raise ValueError(f"Invalid source_type: {source_type}. Must be 'S3'")
    
    # ベクトル取り込み設定を構築（オプション）
    vector_ingestion_config = None
    if parsing_strategy or chunking_strategy:
        # パーシング設定を構築
        parsing_config = None
        if parsing_strategy:
            parsing_config = ParsingConfiguration(
                parsing_strategy=ParsingStrategy(parsing_strategy),
                parsing_model_arn=parsing_model_arn if parsing_model_arn else None,
                parsing_modality=parsing_modality if parsing_modality else None,
                parsing_prompt_text=parsing_prompt_text if parsing_prompt_text else None,
            )
        
        # チャンキング設定を構築
        chunking_config = None
        if chunking_strategy:
            chunking_config = ChunkingConfiguration(
                chunking_strategy=ChunkingStrategy(chunking_strategy),
                max_tokens=chunking_max_tokens if chunking_max_tokens > 0 else None,
                overlap_percentage=chunking_overlap_percentage if chunking_overlap_percentage > 0 else None,
                overlap_tokens=chunking_overlap_tokens if chunking_overlap_tokens > 0 else None,
                buffer_size=chunking_buffer_size if chunking_buffer_size > 0 else None,
                breakpoint_percentile_threshold=chunking_breakpoint_threshold if chunking_breakpoint_threshold > 0 else None,
            )
        
        if parsing_config or chunking_config:
            vector_ingestion_config = VectorIngestionConfiguration(
                parsing_configuration=parsing_config,
                chunking_configuration=chunking_config,
            )
    
    # Pydanticモデルを使用してリクエストパラメータをバリデーション
    request = CreateDataSourceRequest(
        knowledge_base_id=knowledge_base_id,
        name=name,
        source_type=source_type_enum,
        bucket_arn=bucket_arn,
        inclusion_prefixes=inclusion_prefixes,
        vector_ingestion_configuration=vector_ingestion_config,
    )
    
    # インクルージョンプレフィックスをカンマ区切りからリストに変換
    # ユーザーが"documents/,images/"のようにカンマ区切りで指定した場合、
    # ["documents/", "images/"]のようなリストに変換します
    # 空文字列や空白のみの要素は除外し、各要素の前後の空白を削除します
    prefixes = [
        p.strip() for p in request.inclusion_prefixes.split(",") if p.strip()
    ] if request.inclusion_prefixes else []

    # AWS API用のデータソース設定を構築
    # dataSourceConfigurationは、データソースの種類と設定を定義します
    # 現在はS3タイプのみをサポートしています
    data_source_configuration = {
        "type": request.source_type.value,  # "S3"を設定
        "s3Configuration": {
            "bucketArn": request.bucket_arn,  # データソースとして使用するS3バケットのARN
            # inclusionPrefixesは、プレフィックスが指定されている場合のみ追加されます
        },
    }

    # プレフィックスが指定されている場合は設定に追加
    # inclusionPrefixesを指定すると、指定されたプレフィックスに一致するオブジェクトのみが
    # データソースとして使用されます（例: "documents/"フォルダ内のファイルのみ）
    if prefixes:
        data_source_configuration["s3Configuration"]["inclusionPrefixes"] = prefixes

    # ベクトル取り込み設定をAWS API形式に変換
    vector_ingestion_config_dict = None
    if request.vector_ingestion_configuration:
        vector_ingestion_config_dict = request.vector_ingestion_configuration.to_api_dict()

    # Bedrockクライアントを使用してデータソースを作成
    result = bedrock_client.create_data_source(
        knowledge_base_id=request.knowledge_base_id,
        name=request.name,
        data_source_configuration=data_source_configuration,
        vector_ingestion_configuration=vector_ingestion_config_dict,
    )
    return result


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def list_data_sources(knowledge_base_id: str) -> DataSourceListResponseDict:
    """
    指定されたKnowledge Baseのデータソース一覧を取得します。
    
    Knowledge Baseに紐づけられているすべてのデータソースを取得します。

    Args:
        knowledge_base_id: Knowledge BaseのID

    Returns:
        DataSourceListResponseDict: データソース一覧
            - count: データソースの数
            - data_sources: データソースの詳細情報のリスト
                各要素には以下の情報が含まれます:
                - id: データソースのID
                - name: データソースの名前
                - status: データソースのステータス
                - dataSourceConfiguration: データソースの設定情報
    
    Raises:
        ValueError: knowledge_base_idが空の場合
    """
    # 入力値のバリデーション（共通関数を使用）
    knowledge_base_id = validate_required_string(knowledge_base_id, "knowledge_base_id")
    
    # Bedrockクライアントからデータソース一覧を取得
    data_sources = bedrock_client.list_data_sources(knowledge_base_id)
    return {
        "count": len(data_sources),
        "data_sources": data_sources,
    }


# ============================================================================
# Data Ingestion Tools
# ============================================================================


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def start_ingestion_job(
    knowledge_base_id: str, data_source_id: str
) -> IngestionJobResponseDict:
    """
    データソースからKnowledge Baseへのデータ取り込みジョブを開始します。
    
    このジョブは非同期で実行され、データソース内のドキュメントを
    Knowledge Baseに取り込みます。ジョブの進捗は`get_ingestion_job`で確認できます。

    Args:
        knowledge_base_id: Knowledge BaseのID
        data_source_id: データソースのID

    Returns:
        IngestionJobResponseDict: 取り込みジョブの開始結果
            - ingestion_job_id: 開始された取り込みジョブのID
            - status: ジョブのステータス（通常は "STARTING" または "IN_PROGRESS"）
            - statistics: 統計情報（オプション、ジョブ開始時は通常None）
    
    Raises:
        ValueError: knowledge_base_idまたはdata_source_idが空の場合
    
    Note:
        取り込みジョブは非同期で実行されるため、この関数は即座に返ります。
        ジョブの完了を待つには、`get_ingestion_job`を定期的に呼び出して
        ステータスを確認してください。
    """
    # 入力値のバリデーション（共通関数を使用）
    knowledge_base_id = validate_required_string(knowledge_base_id, "knowledge_base_id")
    data_source_id = validate_required_string(data_source_id, "data_source_id")
    
    # Bedrockクライアントを使用して取り込みジョブを開始
    result = bedrock_client.start_ingestion_job(
        knowledge_base_id, data_source_id
    )
    return result


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def get_ingestion_job(
    knowledge_base_id: str, data_source_id: str, ingestion_job_id: str
) -> IngestionJobResponseDict:
    """
    取り込みジョブのステータスと詳細情報を取得します。
    
    取り込みジョブの進捗状況、統計情報、エラー情報などを取得できます。

    Args:
        knowledge_base_id: Knowledge BaseのID
        data_source_id: データソースのID
        ingestion_job_id: 取り込みジョブのID（`start_ingestion_job`で取得）

    Returns:
        IngestionJobResponseDict: 取り込みジョブの詳細情報
            - ingestion_job_id: 取り込みジョブのID
            - status: ジョブのステータス
                - "STARTING": ジョブが開始中
                - "IN_PROGRESS": ジョブが実行中
                - "COMPLETE": ジョブが完了
                - "FAILED": ジョブが失敗
            - statistics: 統計情報（オプション、ジョブが進行中または完了している場合）
                - numberOfDocumentsScanned: スキャンされたドキュメント数
                - numberOfDocumentsModified: 変更されたドキュメント数
                - numberOfDocumentsDeleted: 削除されたドキュメント数
                - numberOfDocumentsFailed: 失敗したドキュメント数
    
    Raises:
        ValueError: いずれかのIDが空の場合
    """
    # 入力値のバリデーション（共通関数を使用）
    knowledge_base_id = validate_required_string(knowledge_base_id, "knowledge_base_id")
    data_source_id = validate_required_string(data_source_id, "data_source_id")
    ingestion_job_id = validate_required_string(ingestion_job_id, "ingestion_job_id")
    
    # Bedrockクライアントから取り込みジョブの詳細を取得
    result = bedrock_client.get_ingestion_job(
        knowledge_base_id, data_source_id, ingestion_job_id
    )
    return result


# ============================================================================
# Query Tools
# ============================================================================


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def retrieve(
    knowledge_base_id: str, query: str, number_of_results: int = 5
) -> RetrieveResponseDict:
    """
    Knowledge Baseに対してRAG（Retrieval-Augmented Generation）クエリを実行します。
    
    ベクトル検索を使用して、クエリに関連するドキュメントを取得します。
    
    Args:
        knowledge_base_id: クエリ対象のKnowledge BaseのID
        query: 検索クエリのテキスト
        number_of_results: 返す結果の数（デフォルト: 5、範囲: 1-100）

    Returns:
        RetrieveResponseDict: クエリ結果
            - results: 検索結果のリスト（各結果にはcontent、location、score、metadataが含まれる）
            - query: 実行したクエリテキスト
    
    Raises:
        ValueError: 入力値が無効な場合（knowledge_base_idやqueryが空、number_of_resultsが範囲外など）
    """
    # 入力値のバリデーション（共通関数を使用）
    # knowledge_base_idとqueryは必須パラメータです
    knowledge_base_id = validate_required_string(knowledge_base_id, "knowledge_base_id")
    query = validate_required_string(query, "query")
    
    # number_of_resultsは1から100の範囲で指定する必要があります
    # AWS APIの制限に従います
    if number_of_results < 1 or number_of_results > 100:
        raise ValueError("number_of_results must be between 1 and 100")

    # Bedrockクライアントを使用してRAGクエリを実行
    # ベクトル検索を使用して、クエリに関連するドキュメントを取得します
    # 結果は関連度スコアでソートされ、指定された数の結果が返されます
    result = bedrock_client.retrieve(
        knowledge_base_id,  # 前後の空白は既に削除済み
        query,  # 前後の空白は既に削除済み
        number_of_results  # 返す結果の数
    )
    return result


# ============================================================================
# S3 Document Management Tools
# ============================================================================


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def upload_document_to_s3(
    local_file_path: str, bucket_name: str, s3_key: str
) -> S3UploadResponseDict:
    """
    ローカルファイルをS3バケットにアップロードします。
    
    アップロードされたファイルは、Knowledge Baseのデータソースとして
    使用できます。

    Args:
        local_file_path: アップロードするローカルファイルのパス
        bucket_name: アップロード先のS3バケット名
        s3_key: S3オブジェクトキー（バケット内のパス）
                例: "documents/myfile.pdf" のようにパスを指定可能

    Returns:
        S3UploadResponseDict: アップロード結果
            - s3_uri: アップロードされたファイルのS3 URI（s3://bucket/key形式）
            - status: アップロードステータス（"uploaded"）
    
    Raises:
        ValueError: パラメータが空の場合、またはファイルが存在しない場合
    
    Example:
        upload_document_to_s3(
            "/path/to/document.pdf",
            "my-bucket",
            "documents/document.pdf"
        )
        # 戻り値: {"s3_uri": "s3://my-bucket/documents/document.pdf", "status": "uploaded"}
    """
    import os
    
    # 入力値のバリデーション（共通関数を使用）
    # すべてのパラメータは必須です
    local_file_path = validate_required_string(local_file_path, "local_file_path")
    bucket_name = validate_required_string(bucket_name, "bucket_name")
    s3_key = validate_required_string(s3_key, "s3_key")
    
    # ファイルの存在確認
    # ローカルファイルシステム上にファイルが存在することを確認します
    # ファイルが存在しない場合、S3へのアップロードは失敗するため、事前にチェックします
    if not os.path.exists(local_file_path):
        raise ValueError(f"File not found: {local_file_path}")
    
    # 注意: ファイルサイズのチェックは行っていません
    # 非常に大きなファイルの場合、アップロードに時間がかかる可能性があります

    # Bedrockクライアントを使用してS3にアップロード
    result = bedrock_client.upload_document_to_s3(
        local_file_path,  # 前後の空白は既に削除済み
        bucket_name,  # 前後の空白は既に削除済み
        s3_key  # 前後の空白は既に削除済み
    )
    return result


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def list_s3_documents(bucket_name: str, prefix: str = "") -> S3DocumentListResponseDict:
    """
    S3バケット内のドキュメント一覧を取得します。
    
    指定されたプレフィックス（フォルダ）に一致するドキュメントのみを
    取得することもできます。

    Args:
        bucket_name: S3バケット名
        prefix: フィルタリングするS3プレフィックス（オプション）
                例: "documents/" を指定すると、documents/フォルダ内の
                    ファイルのみが返されます

    Returns:
        S3DocumentListResponseDict: ドキュメント一覧
            - count: ドキュメントの数
            - bucket: バケット名
            - prefix: 使用されたプレフィックス（指定した場合）
            - documents: ドキュメントの詳細情報のリスト
                各要素には以下の情報が含まれます:
                - key: S3オブジェクトキー（ファイルパス）
                - size: ファイルサイズ（バイト）
                - last_modified: 最終更新日時（ISO形式）
    
    Raises:
        ValueError: bucket_nameが空の場合
    
    Example:
        # すべてのドキュメントを取得
        list_s3_documents("my-bucket")
        
        # 特定のプレフィックスのドキュメントのみを取得
        list_s3_documents("my-bucket", "documents/")
    """
    # 入力値のバリデーション（共通関数を使用）
    bucket_name = validate_required_string(bucket_name, "bucket_name")
    
    # プレフィックスはオプションなので、指定されている場合のみstripを適用
    prefix_cleaned = prefix.strip() if prefix else ""
    
    # BedrockクライアントからS3ドキュメント一覧を取得
    documents = bedrock_client.list_s3_documents(
        bucket_name,  # 前後の空白は既に削除済み
        prefix_cleaned
    )
    return {
        "count": len(documents),
        "bucket": bucket_name,  # 前後の空白は既に削除済み
        "prefix": prefix_cleaned,
        "documents": documents,
    }


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def create_s3_bucket(
    bucket_name: str,
    region: str = "us-east-1",
) -> S3BucketCreateResponseDict:
    """
    S3バケットを新規作成します。
    
    バケット名は以下のルールに従う必要があります:
    - 3文字以上63文字以下
    - 小文字、数字、ハイフン（-）、ピリオド（.）のみ使用可能
    - 先頭と末尾は小文字または数字である必要がある
    - 連続するハイフンやピリオドは使用不可
    - IPアドレス形式（例: 192.168.1.1）は使用不可
    - バケット名はグローバルに一意である必要があります
    
    注意: セキュリティ上の理由から、パブリックアクセスブロックは常に有効化されます。

    Args:
        bucket_name: 作成するS3バケット名（必須）
            例: "my-documents-bucket"
        region: バケットを作成するリージョン（デフォルト: "us-east-1"）
            例: "us-east-1", "ap-northeast-1"
            注意: us-east-1リージョンの場合、LocationConstraintは指定しません

    Returns:
        S3BucketCreateResponseDict: バケット作成結果
            - bucket_name: 作成されたバケット名
            - region: バケットが作成されたリージョン
            - arn: バケットのARN（arn:aws:s3:::bucket-name形式）
            - status: 作成ステータス（"created"）
    
    Raises:
        ValueError: bucket_nameが空の場合、またはバケット名が無効な形式の場合
        ClientError: AWS API呼び出しが失敗した場合
            例: バケット名が既に使用されている、権限がないなど
    
    Example:
        # 基本的なバケット作成（デフォルトリージョン、パブリックアクセスブロック有効）
        create_s3_bucket("my-documents-bucket")
        
        # 特定のリージョンにバケットを作成
        create_s3_bucket("my-documents-bucket", region="ap-northeast-1")
    
    Note:
        - バケットの作成には数秒かかる場合があります
        - バケット名が既に使用されている場合、BucketAlreadyOwnedByYouまたはBucketAlreadyExistsエラーが発生します
        - パブリックアクセスブロック設定は、バケット作成後に自動的に適用されます
    """
    # 入力値のバリデーション（共通関数を使用）
    bucket_name = validate_required_string(bucket_name, "bucket_name")
    
    # バケット名の基本的なバリデーション
    # AWS S3のバケット名ルールに従う必要があります
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        raise ValueError("bucket_name must be between 3 and 63 characters")
    
    # バケット名は小文字、数字、ハイフン、ピリオドのみ使用可能
    # ただし、IPアドレス形式は使用不可
    import re
    if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', bucket_name):
        raise ValueError(
            "bucket_name must start and end with a lowercase letter or number, "
            "and contain only lowercase letters, numbers, hyphens, and periods"
        )
    
    # 連続するハイフンやピリオドは使用不可
    if '..' in bucket_name or '--' in bucket_name:
        raise ValueError("bucket_name cannot contain consecutive periods or hyphens")
    
    # IPアドレス形式のチェック（簡易版）
    # より厳密なチェックが必要な場合は、ipaddressモジュールを使用できます
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, bucket_name):
        raise ValueError("bucket_name cannot be in IP address format")
    
    # リージョンを正規化（前後の空白を削除、空文字列の場合はus-east-1を使用）
    region_cleaned = region.strip() if region else "us-east-1"
    
    # BedrockクライアントからS3バケットを作成
    result = bedrock_client.create_s3_bucket(
        bucket_name=bucket_name,  # 前後の空白は既に削除済み
        region=region_cleaned,  # 既定値はus-east-1
    )
    return result


@mcp.tool()  # MCPツールとして公開
@handle_errors  # エラーハンドリングデコレータを適用
def create_bedrock_kb_role(
    role_name: str,
    region: str = "us-east-1",
    description: str = "Bedrock Knowledge Base access",
    max_session_duration: int = 3600,
) -> IAMRoleCreateResponseDict:
    """
    Amazon Bedrock Knowledge Base用のサービスロールを作成します。
    
    このツールは、Bedrock Knowledge Baseが使用するIAMロールを作成します。
    ロールには以下の信頼ポリシーが設定されます:
    - Service: bedrock.amazonaws.com
    - Condition: aws:SourceAccountとaws:SourceArnによる制限
      - aws:SourceAccount: 現在のAWSアカウントID
      - aws:SourceArn: arn:aws:bedrock:[REGION]:[ACCOUNT_ID]:knowledge-base/*

    Args:
        role_name: 作成するIAMロールの名前（必須）
            例: "BedrockKnowledgeBaseRole"
            注意: ロール名はAWSアカウント内で一意である必要があります
        region: Knowledge Baseを作成する先のリージョン（デフォルト: "us-east-1"）
            例: "us-east-1", "ap-northeast-1"
            注意: 信頼ポリシーのaws:SourceArnにこのリージョンが使用されます
            このリージョンは、Knowledge Baseを作成する際に指定するリージョンと一致させる必要があります
        description: ロールの説明（デフォルト: "Bedrock Knowledge Base access"）
        max_session_duration: 最大セッション時間（秒）（デフォルト: 3600秒 = 1時間）
            範囲: 3600秒（1時間）から43200秒（12時間）まで

    Returns:
        IAMRoleCreateResponseDict: ロール作成結果
            - role_name: 作成されたロール名
            - role_arn: ロールのARN（arn:aws:iam::ACCOUNT_ID:role/service-role/ROLE_NAME形式）
            - path: ロールのパス（/service-role/）
            - status: 作成ステータス（"created"）
    
    Raises:
        ValueError: role_nameが空の場合、またはmax_session_durationが無効な範囲の場合
        ClientError: AWS API呼び出しが失敗した場合
            例: ロール名が既に使用されている、権限がないなど
    
    Example:
        # 基本的なロール作成（デフォルトリージョン）
        create_bedrock_kb_role("BedrockKnowledgeBaseRole")
        
        # 特定のリージョン用のロール作成
        create_bedrock_kb_role("BedrockKnowledgeBaseRole", region="ap-northeast-1")
        
        # カスタム説明とセッション時間を指定
        create_bedrock_kb_role(
            "MyBedrockRole",
            description="Custom Bedrock KB role",
            max_session_duration=7200
        )
    
    Note:
        - ロールは /service-role/ パスに作成されます
        - 信頼ポリシーには、現在のAWSアカウントIDとリージョンが自動的に設定されます
        - ロール作成後、適切な権限ポリシーをアタッチする必要があります
        - ロール名が既に使用されている場合、EntityAlreadyExistsエラーが発生します
    """
    # 入力値のバリデーション（共通関数を使用）
    role_name = validate_required_string(role_name, "role_name")
    
    # ロール名の基本的なバリデーション
    # IAMロール名のルールに従う必要があります
    if len(role_name) < 1 or len(role_name) > 64:
        raise ValueError("role_name must be between 1 and 64 characters")
    
    # ロール名は英数字、ハイフン、アンダースコア、ピリオドのみ使用可能
    import re
    if not re.match(r'^[\w+=,.@-]+$', role_name):
        raise ValueError(
            "role_name must contain only alphanumeric characters, hyphens, "
            "underscores, periods, plus signs, equals signs, commas, and @ symbols"
        )
    
    # max_session_durationのバリデーション
    # IAMの制限: 3600秒（1時間）から43200秒（12時間）まで
    if max_session_duration < 3600 or max_session_duration > 43200:
        raise ValueError("max_session_duration must be between 3600 and 43200 seconds")
    
    # リージョンを正規化（前後の空白を削除、空文字列の場合はus-east-1を使用）
    region_cleaned = region.strip() if region else "us-east-1"
    
    # BedrockクライアントからIAMロールを作成
    result = bedrock_client.create_bedrock_kb_role(
        role_name=role_name,  # 前後の空白は既に削除済み
        region=region_cleaned,  # 既定値はus-east-1
        description=description,
        max_session_duration=max_session_duration,
    )
    return result


def main():
    """
    MCPサーバーを起動します。
    
    この関数は、FastMCPサーバーを起動して、クライアントからの
    リクエストを待機します。
    
    MCPサーバーは標準入力（stdin）からJSON-RPC形式のリクエストを受け取り、
    標準出力（stdout）にJSON-RPC形式のレスポンスを返します。
    
    Note:
        この関数はブロッキングです。サーバーを停止するには、SIGTERMまたはSIGINTを送信します。
    """
    # サーバー起動をログに記録
    # このログは、サーバーが正常に起動したことを示します
    logger.info("Starting Amazon Bedrock Knowledge Base MCP Server")
    
    # FastMCPサーバーを起動（ブロッキング）
    # mcp.run()は、標準入力からリクエストを読み取り、処理して、標準出力にレスポンスを書き込みます
    # この呼び出しは、サーバーが停止するまでブロックされます
    mcp.run()


# スクリプトとして直接実行された場合にmain()を呼び出す
# このモジュールがPythonスクリプトとして直接実行された場合（例: python -m bedrock_kb_mcp_server.main）
# またはエントリーポイントから実行された場合（例: bedrock-kb-mcp-serverコマンド）に、
# main()関数を呼び出してMCPサーバーを起動します
if __name__ == "__main__":
    main()

