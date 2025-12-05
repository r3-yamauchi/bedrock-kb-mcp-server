"""
Pydanticモデル定義モジュール

リクエスト/レスポンスのバリデーションと型安全性を提供するための
Pydanticモデルを定義します。

これらのモデルは以下の目的で使用されます:
- 入力値の検証（形式、必須チェックなど）
- 型安全性の向上
- APIドキュメントの自動生成
- IDEの自動補完サポート
"""

from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator


class StorageType(str, Enum):
    """
    Knowledge Baseのストレージタイプを定義する列挙型
    
    Attributes:
        S3: 標準的なS3ストレージを使用
        S3_VECTORS: S3 Vectorsを使用したベクトル検索対応ストレージ（埋め込みモデルが必要）
    """
    S3 = "S3"                    # 標準S3ストレージ
    S3_VECTORS = "S3_VECTORS"    # S3 Vectorsを使用したベクトル検索対応ストレージ


class SourceType(str, Enum):
    """
    データソースのタイプを定義する列挙型
    
    AWS Bedrock Knowledge Baseのデータソース設定で使用可能なタイプを定義します。
    ベクトル検索の機能は、Knowledge Baseのストレージ設定（storageConfiguration）で
    制御されます。
    
    Attributes:
        S3: 標準的なS3データソース
    """
    S3 = "S3"  # 標準S3データソース


class ParsingStrategy(str, Enum):
    """
    パーシング戦略を定義する列挙型
    
    AWS Bedrock Knowledge Baseでドキュメントをパースする際の戦略を定義します。
    
    Attributes:
        BEDROCK_FOUNDATION_MODEL: Foundation Modelを使用したパーシング
        BEDROCK_DATA_AUTOMATION: Bedrock Data Automationを使用したパーシング
    """
    BEDROCK_FOUNDATION_MODEL = "BEDROCK_FOUNDATION_MODEL"  # Foundation Modelパーシング
    BEDROCK_DATA_AUTOMATION = "BEDROCK_DATA_AUTOMATION"    # Bedrock Data Automationを使用したパーシング


class ChunkingStrategy(str, Enum):
    """
    チャンキング戦略を定義する列挙型
    
    AWS Bedrock Knowledge Baseでドキュメントをチャンクに分割する際の戦略を定義します。
    
    Attributes:
        FIXED_SIZE: 固定サイズのチャンクに分割
        HIERARCHICAL: 階層的なチャンクに分割（大きなチャンクと小さなチャンクの2層）
        SEMANTIC: セマンティックなチャンクに分割（NLPを使用）
        NONE: チャンクに分割しない（各ファイルが1つのチャンクとして扱われる）
    """
    FIXED_SIZE = "FIXED_SIZE"      # 固定サイズのチャンク
    HIERARCHICAL = "HIERARCHICAL"  # 階層的なチャンク
    SEMANTIC = "SEMANTIC"          # セマンティックなチャンク
    NONE = "NONE"                  # チャンクに分割しない


class KnowledgeBaseResponse(BaseModel):
    """
    Knowledge Base作成/更新のレスポンスモデル
    
    Knowledge Baseを作成または更新した際に返される情報を定義します。
    
    Attributes:
        knowledge_base_id: 作成または更新されたKnowledge BaseのID
        status: Knowledge Baseのステータス
            - "CREATING": 作成中
            - "ACTIVE": アクティブ（利用可能）
            - "UPDATING": 更新中
            - "FAILED": 失敗
        arn: Knowledge BaseのARN（オプション、作成時のみ含まれる場合がある）
    """
    knowledge_base_id: str  # Knowledge BaseのID
    status: str  # Knowledge Baseのステータス
    arn: Optional[str] = None  # Knowledge BaseのARN（オプション）


class KnowledgeBaseDetail(BaseModel):
    """
    Knowledge Baseの詳細情報モデル
    
    Knowledge Baseの詳細情報を定義します。
    
    Attributes:
        id: Knowledge BaseのID
        name: Knowledge Baseの名前
        status: Knowledge Baseのステータス
        description: Knowledge Baseの説明（オプション）
        arn: Knowledge BaseのARN（オプション）
    """
    id: str  # Knowledge BaseのID
    name: str  # Knowledge Baseの名前
    status: str  # Knowledge Baseのステータス
    description: Optional[str] = None  # Knowledge Baseの説明（オプション）
    arn: Optional[str] = None  # Knowledge BaseのARN（オプション）


class DataSourceResponse(BaseModel):
    """
    データソース作成のレスポンスモデル
    
    データソースを作成した際に返される情報を定義します。
    
    Attributes:
        data_source_id: 作成されたデータソースのID
        status: データソースのステータス
            - "CREATING": 作成中
            - "ACTIVE": アクティブ（利用可能）
            - "FAILED": 失敗
    """
    data_source_id: str  # データソースのID
    status: str  # データソースのステータス


class IngestionJobResponse(BaseModel):
    """
    取り込みジョブのレスポンスモデル
    
    取り込みジョブの情報を定義します。
    
    Attributes:
        ingestion_job_id: 取り込みジョブのID
        status: ジョブのステータス
            - "STARTING": ジョブが開始中
            - "IN_PROGRESS": ジョブが実行中
            - "COMPLETE": ジョブが完了
            - "FAILED": ジョブが失敗
        statistics: 統計情報（オプション、ジョブが進行中または完了している場合）
            - numberOfDocumentsScanned: スキャンされたドキュメント数
            - numberOfDocumentsModified: 変更されたドキュメント数
            - numberOfDocumentsDeleted: 削除されたドキュメント数
            - numberOfDocumentsFailed: 失敗したドキュメント数
    """
    ingestion_job_id: str  # 取り込みジョブのID
    status: str  # ジョブのステータス
    statistics: Optional[Dict[str, Any]] = None  # 統計情報（オプション）


class S3UploadResponse(BaseModel):
    """
    S3アップロードのレスポンスモデル
    
    S3へのファイルアップロード結果を定義します。
    
    Attributes:
        s3_uri: アップロードされたファイルのS3 URI（s3://bucket/key形式）
        status: アップロードステータス（通常は "uploaded"）
    """
    s3_uri: str  # S3 URI（s3://bucket/key形式）
    status: str  # アップロードステータス


class RetrieveResponse(BaseModel):
    """
    RAGクエリのレスポンスモデル
    
    Knowledge Baseに対するRAGクエリの結果を定義します。
    
    Attributes:
        results: 検索結果のリスト
            各結果には以下の情報が含まれます:
            - content: ドキュメントの内容（テキスト）
            - location: ドキュメントの場所（S3 URIなど）
            - score: 関連度スコア（0.0-1.0の範囲、高いほど関連性が高い）
            - metadata: メタデータ（ドキュメントの種類、作成日時など）
        query: 実行したクエリテキスト
    """
    results: List[Dict[str, Any]]  # 検索結果のリスト
    query: str  # 実行したクエリテキスト


class ListResponse(BaseModel):
    """
    一覧取得のレスポンスモデル
    
    一覧取得操作の結果を定義します。
    
    Attributes:
        count: 取得されたアイテムの数
        items: アイテムの詳細情報のリスト
    """
    count: int  # アイテムの数
    items: List[Dict[str, Any]]  # アイテムの詳細情報のリスト


class ParsingConfiguration(BaseModel):
    """
    パーシング設定モデル
    
    ドキュメントをパースする際の設定を定義します。
    
    Attributes:
        parsing_strategy: パーシング戦略（BEDROCK_FOUNDATION_MODEL または BEDROCK_DATA_AUTOMATION）
        parsing_model_arn: Foundation ModelのARN（BEDROCK_FOUNDATION_MODELの場合必須）
        parsing_modality: マルチモーダルデータのパーシングを有効にするか（MULTIMODAL）
        parsing_prompt_text: パーシングプロンプトのテキスト（オプション）
    """
    parsing_strategy: ParsingStrategy = Field(..., description="パーシング戦略")
    parsing_model_arn: Optional[str] = Field(default=None, description="Foundation ModelのARN")
    parsing_modality: Optional[str] = Field(default=None, description="マルチモーダル設定（MULTIMODAL）")
    parsing_prompt_text: Optional[str] = Field(default=None, description="パーシングプロンプトのテキスト")
    
    @model_validator(mode='after')
    def validate_parsing_model(self):
        """
        パーシングモデルのバリデーション
        
        BEDROCK_FOUNDATION_MODEL戦略の場合、parsing_model_arnが必須です。
        """
        if self.parsing_strategy == ParsingStrategy.BEDROCK_FOUNDATION_MODEL and not self.parsing_model_arn:
            raise ValueError('parsing_model_arn is required for BEDROCK_FOUNDATION_MODEL parsing strategy')
        return self


class ChunkingConfiguration(BaseModel):
    """
    チャンキング設定モデル
    
    ドキュメントをチャンクに分割する際の設定を定義します。
    
    Attributes:
        chunking_strategy: チャンキング戦略（FIXED_SIZE, HIERARCHICAL, SEMANTIC, NONE）
        max_tokens: 最大トークン数（FIXED_SIZE, SEMANTICの場合）
        overlap_percentage: オーバーラップ率（FIXED_SIZEの場合、0-100）
        overlap_tokens: オーバーラップトークン数（HIERARCHICALの場合）
        level_configurations: 階層チャンキングのレベル設定（HIERARCHICALの場合）
        buffer_size: バッファサイズ（SEMANTICの場合）
        breakpoint_percentile_threshold: ブレークポイントのパーセンタイル閾値（SEMANTICの場合）
    """
    chunking_strategy: ChunkingStrategy = Field(..., description="チャンキング戦略")
    max_tokens: Optional[int] = Field(default=None, description="最大トークン数")
    overlap_percentage: Optional[int] = Field(default=None, ge=0, le=100, description="オーバーラップ率（0-100）")
    overlap_tokens: Optional[int] = Field(default=None, description="オーバーラップトークン数（階層チャンキング用）")
    level_configurations: Optional[List[Dict[str, Any]]] = Field(default=None, description="階層チャンキングのレベル設定")
    buffer_size: Optional[int] = Field(default=None, description="バッファサイズ（セマンティックチャンキング用）")
    breakpoint_percentile_threshold: Optional[int] = Field(default=None, description="ブレークポイントのパーセンタイル閾値（セマンティックチャンキング用）")


class VectorIngestionConfiguration(BaseModel):
    """
    ベクトル取り込み設定モデル
    
    データソースからベクトルストアへの取り込み設定を定義します。
    
    Attributes:
        parsing_configuration: パーシング設定（オプション）
        chunking_configuration: チャンキング設定（オプション）
    """
    parsing_configuration: Optional[ParsingConfiguration] = Field(default=None, description="パーシング設定")
    chunking_configuration: Optional[ChunkingConfiguration] = Field(default=None, description="チャンキング設定")
    
    def to_api_dict(self) -> Dict[str, Any]:
        """
        AWS API形式の辞書に変換
        
        Returns:
            Dict[str, Any]: AWS API形式のvectorIngestionConfiguration辞書
        """
        result: Dict[str, Any] = {}
        
        # パーシング設定を追加
        if self.parsing_configuration:
            parsing_config = {
                "parsingStrategy": self.parsing_configuration.parsing_strategy.value
            }
            
            if self.parsing_configuration.parsing_strategy == ParsingStrategy.BEDROCK_FOUNDATION_MODEL:
                foundation_config: Dict[str, Any] = {
                    "modelArn": self.parsing_configuration.parsing_model_arn
                }
                if self.parsing_configuration.parsing_modality:
                    foundation_config["parsingModality"] = self.parsing_configuration.parsing_modality
                if self.parsing_configuration.parsing_prompt_text:
                    foundation_config["parsingPrompt"] = {
                        "parsingPromptText": self.parsing_configuration.parsing_prompt_text
                    }
                parsing_config["bedrockFoundationModelConfiguration"] = foundation_config
            elif self.parsing_configuration.parsing_strategy == ParsingStrategy.BEDROCK_DATA_AUTOMATION:
                automation_config: Dict[str, Any] = {}
                if self.parsing_configuration.parsing_modality:
                    automation_config["parsingModality"] = self.parsing_configuration.parsing_modality
                parsing_config["bedrockDataAutomationConfiguration"] = automation_config
            
            result["parsingConfiguration"] = parsing_config
        
        # チャンキング設定を追加
        if self.chunking_configuration:
            chunking_config = {
                "chunkingStrategy": self.chunking_configuration.chunking_strategy.value
            }
            
            if self.chunking_configuration.chunking_strategy == ChunkingStrategy.FIXED_SIZE:
                if self.chunking_configuration.max_tokens is not None:
                    chunking_config["fixedSizeChunkingConfiguration"] = {
                        "maxTokens": self.chunking_configuration.max_tokens,
                        "overlapPercentage": self.chunking_configuration.overlap_percentage or 0
                    }
            elif self.chunking_configuration.chunking_strategy == ChunkingStrategy.HIERARCHICAL:
                hierarchical_config: Dict[str, Any] = {}
                if self.chunking_configuration.level_configurations:
                    hierarchical_config["levelConfigurations"] = self.chunking_configuration.level_configurations
                if self.chunking_configuration.overlap_tokens is not None:
                    hierarchical_config["overlapTokens"] = self.chunking_configuration.overlap_tokens
                chunking_config["hierarchicalChunkingConfiguration"] = hierarchical_config
            elif self.chunking_configuration.chunking_strategy == ChunkingStrategy.SEMANTIC:
                semantic_config: Dict[str, Any] = {}
                if self.chunking_configuration.max_tokens is not None:
                    semantic_config["maxTokens"] = self.chunking_configuration.max_tokens
                if self.chunking_configuration.buffer_size is not None:
                    semantic_config["bufferSize"] = self.chunking_configuration.buffer_size
                if self.chunking_configuration.breakpoint_percentile_threshold is not None:
                    semantic_config["breakpointPercentileThreshold"] = self.chunking_configuration.breakpoint_percentile_threshold
                chunking_config["semanticChunkingConfiguration"] = semantic_config
            
            result["chunkingConfiguration"] = chunking_config
        
        return result


class CreateKnowledgeBaseRequest(BaseModel):
    """
    Knowledge Base作成リクエストのバリデーションモデル
    
    Knowledge Baseを作成する際に必要なパラメータを定義し、
    入力値の検証を行います。
    
    Attributes:
        name: Knowledge Baseの名前（1-100文字）
        description: Knowledge Baseの説明（1文字以上）
        role_arn: Knowledge Baseが使用するIAMロールのARN
        storage_type: ストレージタイプ（デフォルト: S3）
        bucket_arn: ドキュメントを保存するS3バケットのARN（S3_VECTORSの場合はベクトルバケットARN）
        embedding_model_arn: 埋め込みモデルのARN（S3_VECTORSタイプの場合必須）
        vector_ingestion_configuration: ベクトル取り込み設定（オプション）
    """
    # Knowledge Base名: 必須、1-100文字
    name: str = Field(..., min_length=1, max_length=100, description="Knowledge Base名")
    
    # 説明: 必須、1文字以上
    description: str = Field(..., min_length=1, description="説明")
    
    # IAMロールARN: 必須、ARN形式で検証
    role_arn: str = Field(..., description="IAMロールARN")
    
    # ストレージタイプ: デフォルトはS3
    storage_type: StorageType = Field(default=StorageType.S3, description="ストレージタイプ")
    
    # S3バケットARN: 必須、ARN形式で検証
    bucket_arn: str = Field(..., description="S3バケットARN")
    
    # 埋め込みモデルARN: オプション（S3_VECTORSタイプの場合は必須）
    embedding_model_arn: Optional[str] = Field(default=None, description="埋め込みモデルARN")
    
    # ベクトル取り込み設定: オプション
    vector_ingestion_configuration: Optional[VectorIngestionConfiguration] = Field(
        default=None, description="ベクトル取り込み設定（パーシング、チャンキング設定を含む）"
    )
    
    @model_validator(mode='after')
    def validate_embedding_model(self):
        """
        モデル全体のバリデーション
        
        S3_VECTORSタイプを選択した場合、embedding_model_arnが必須であることを確認します。
        
        Returns:
            self: バリデーション成功時は自身を返す
        
        Raises:
            ValueError: S3_VECTORSタイプでembedding_model_arnが指定されていない場合
        """
        if self.storage_type == StorageType.S3_VECTORS and not self.embedding_model_arn:
            raise ValueError('embedding_model_arn is required for S3_VECTORS storage type')
        return self
    
    @field_validator('role_arn')
    @classmethod
    def validate_role_arn(cls, v: str) -> str:
        """
        IAMロールARNの形式を検証し、必要に応じてアカウントIDを補完
        
        Args:
            v: 検証するARN文字列
        
        Returns:
            str: 正規化されたIAMロールARN文字列
        
        Raises:
            ValueError: ARN形式が無効な場合
        """
        from bedrock_kb_mcp_server.utils import normalize_iam_role_arn
        return normalize_iam_role_arn(v)
    
    @field_validator('bucket_arn')
    @classmethod
    def validate_bucket_arn(cls, v: str) -> str:
        """
        S3バケットARNの形式を検証
        
        Args:
            v: 検証するARN文字列
        
        Returns:
            str: 検証済みのARN文字列
        
        Raises:
            ValueError: ARN形式が無効な場合
        """
        if not v.startswith('arn:aws:s3:::'):
            raise ValueError('Invalid S3 bucket ARN format')
        return v


class CreateDataSourceRequest(BaseModel):
    """
    データソース作成リクエストのバリデーションモデル
    
    データソースを作成する際に必要なパラメータを定義し、
    入力値の検証を行います。
    
    Attributes:
        knowledge_base_id: データソースを追加するKnowledge BaseのID
        name: データソースの名前（1-100文字）
        source_type: データソースタイプ（現在はS3のみサポート、デフォルト: S3）
        bucket_arn: データソースとして使用するS3バケットのARNまたはS3 URI
        inclusion_prefixes: 含めるS3プレフィックスのカンマ区切り文字列（オプション）
        vector_ingestion_configuration: ベクトル取り込み設定（オプション）
    """
    # Knowledge Base ID: 必須
    knowledge_base_id: str = Field(..., description="Knowledge Base ID")
    
    # データソース名: 必須、1-100文字
    name: str = Field(..., min_length=1, max_length=100, description="データソース名")
    
    # データソースタイプ: デフォルトはS3
    source_type: SourceType = Field(default=SourceType.S3, description="データソースタイプ")
    
    # S3バケットARNまたはS3 URI: 必須、ARN形式またはURI形式で検証
    bucket_arn: str = Field(..., description="S3バケットARNまたはS3 URI")
    
    # インクルージョンプレフィックス: オプション、カンマ区切り
    inclusion_prefixes: Optional[str] = Field(default="", description="カンマ区切りのS3プレフィックス")
    
    # ベクトル取り込み設定: オプション
    vector_ingestion_configuration: Optional[VectorIngestionConfiguration] = Field(
        default=None, description="ベクトル取り込み設定（パーシング、チャンキング設定を含む）"
    )
    
    @field_validator('bucket_arn')
    @classmethod
    def validate_bucket_arn(cls, v: str) -> str:
        """
        S3バケットARNまたはS3 URIの形式を検証し、ARN形式に正規化
        
        Args:
            v: 検証するARN文字列またはS3 URI
        
        Returns:
            str: 正規化されたS3 ARN文字列
        
        Raises:
            ValueError: ARN形式またはURI形式が無効な場合
        """
        from bedrock_kb_mcp_server.utils import normalize_s3_arn_or_uri
        return normalize_s3_arn_or_uri(v)

