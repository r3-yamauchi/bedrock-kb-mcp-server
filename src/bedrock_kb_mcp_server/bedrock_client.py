"""
AWS Bedrock Knowledge Base APIクライアントラッパー

AWS Bedrock Knowledge Base APIとの低レベルな通信を担当するクラスです。
boto3を使用してAWS APIを呼び出し、エラーハンドリングとロギングを行います。
"""

import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from bedrock_kb_mcp_server.types import (
    KnowledgeBaseResponseDict,
    DataSourceResponseDict,
    IngestionJobResponseDict,
    RetrieveResponseDict,
    S3UploadResponseDict,
)

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)


class BedrockKBClient:
    """
    AWS Bedrock Knowledge Base操作のラッパークラス
    
    Knowledge Base、データソース、取り込みジョブ、RAGクエリなどの
    AWS Bedrock API操作を提供します。
    """

    def __init__(self):
        """
        Bedrockクライアントを初期化します。
        
        環境変数からAWSリージョンを取得し、以下の3つのAWSクライアントを初期化します:
        - bedrock-agent: Knowledge Baseとデータソースの管理用
        - bedrock-agent-runtime: RAGクエリ実行用
        - s3: S3ドキュメント管理用
        
        Environment Variables:
            AWS_REGION: AWSリージョン（デフォルト: us-east-1）
        """
        # 環境変数からリージョンを取得（デフォルト: us-east-1）
        # AWS_REGION環境変数が設定されていない場合は、us-east-1が使用されます
        # 注意: リージョンはKnowledge Baseの作成時に決定され、後から変更できません
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # AWSクライアント設定（リトライとタイムアウト設定）
        # adaptiveモードは、エラーの種類に応じて自動的にリトライ間隔を調整します
        # 一時的なエラー（ThrottlingExceptionなど）に対して自動的にリトライを行います
        config = Config(
            retries={
                'max_attempts': 3,      # 最大3回までリトライ（初回を含む）
                'mode': 'adaptive'      # 適応的リトライモード（エラーの種類に応じて間隔を調整）
            },
            connect_timeout=10,         # 接続タイムアウト: 10秒（サーバーへの接続確立までの最大時間）
            read_timeout=30             # 読み取りタイムアウト: 30秒（レスポンス受信までの最大時間）
        )
        
        # Bedrock Agent APIクライアント（Knowledge Base管理用）
        # このクライアントは、Knowledge Base、データソース、取り込みジョブの
        # CRUD操作に使用されます
        self.bedrock_agent = boto3.client(
            "bedrock-agent",  # AWS Bedrock Agentサービス
            region_name=self.region,  # 指定されたリージョン
            config=config,  # リトライとタイムアウト設定を適用
        )
        
        # Bedrock Agent Runtime APIクライアント（RAGクエリ実行用）
        # このクライアントは、Knowledge Baseに対するRAGクエリ（retrieve）の
        # 実行に使用されます
        self.bedrock_agent_runtime = boto3.client(
            "bedrock-agent-runtime",  # AWS Bedrock Agent Runtimeサービス
            region_name=self.region,  # 指定されたリージョン
            config=config,  # リトライとタイムアウト設定を適用
        )
        
        # S3クライアント（ドキュメント管理用）
        # このクライアントは、S3バケットへのドキュメントアップロードや
        # ドキュメント一覧の取得に使用されます
        self.s3_client = boto3.client(
            "s3",  # Amazon S3サービス
            region_name=self.region,  # 指定されたリージョン
            config=config,  # リトライとタイムアウト設定を適用
        )
        
        # リージョン情報をログに記録（機密情報はマスクされる）
        logger.info(f"Initialized Bedrock client for region: {self.region}")

    def create_knowledge_base(
        self,
        name: str,
        description: str,
        role_arn: str,
        storage_configuration: Dict[str, Any],
        knowledge_base_configuration: Optional[Dict[str, Any]] = None,
        vector_ingestion_configuration: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeBaseResponseDict:
        """
        新しいKnowledge Baseを作成します。
        
        Args:
            name: Knowledge Baseの名前
            description: Knowledge Baseの説明
            role_arn: Knowledge Baseが使用するIAMロールのARN
            storage_configuration: ストレージ設定の辞書
                - type: ストレージタイプ（"S3" または "S3_VECTORS"）
                - s3Configuration (S3の場合): S3設定
                    - bucketArn: S3バケットARN
                - s3VectorsConfiguration (S3_VECTORSの場合): S3 Vectors設定
                    - vectorBucketArn: ベクトルを保存するS3バケットのARN
                    - indexName (オプション): ベクトルインデックスの名前
                    - indexArn (オプション): ベクトルインデックスのARN
            knowledge_base_configuration: Knowledge Base設定の辞書（S3_VECTORSの場合必須）
                - type: "VECTOR"を指定
                - vectorKnowledgeBaseConfiguration: ベクトル設定
                    - embeddingModelArn: 埋め込みモデルのARN
            vector_ingestion_configuration: ベクトル取り込み設定の辞書（オプション）
                - parsingConfiguration: パーシング設定（オプション）
                - chunkingConfiguration: チャンキング設定（オプション）
        
        Returns:
            KnowledgeBaseResponseDict: Knowledge Baseの作成結果
                - knowledge_base_id: 作成されたKnowledge BaseのID
                - status: Knowledge Baseのステータス
                - arn: Knowledge BaseのARN（オプション）
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        """
        try:
            # API呼び出しパラメータを構築
            # boto3のcreate_knowledge_baseメソッドに渡すパラメータを辞書形式で構築します
            api_params = {
                "name": name,  # Knowledge Baseの名前
                "description": description,  # Knowledge Baseの説明
                "roleArn": role_arn,  # IAMロールのARN（Knowledge BaseがAWSサービスにアクセスするために使用）
                "storageConfiguration": storage_configuration,  # ストレージ設定（S3またはS3_VECTORS）
            }
            
            # Knowledge Base設定が指定されている場合は追加
            # S3_VECTORSタイプの場合、knowledgeBaseConfigurationが必須です
            # この設定には、埋め込みモデルのARNが含まれます
            if knowledge_base_configuration:
                api_params["knowledgeBaseConfiguration"] = knowledge_base_configuration
            
            # ベクトル取り込み設定が指定されている場合は追加
            # パーシング設定やチャンキング設定を含むことができます
            if vector_ingestion_configuration:
                api_params["vectorIngestionConfiguration"] = vector_ingestion_configuration
            
            # AWS Bedrock APIを呼び出してKnowledge Baseを作成
            # このAPI呼び出しは非同期で実行され、Knowledge Baseの作成が開始されます
            # 作成が完了するまでには時間がかかる場合があります（ステータスで確認可能）
            response = self.bedrock_agent.create_knowledge_base(**api_params)
            
            # 作成成功をログに記録
            # Knowledge BaseのIDをログに記録します（機密情報は自動的にマスクされます）
            logger.info(f"Created knowledge base: {response['knowledgeBaseId']}")
            
            # レスポンスを整形して返す
            # AWS APIのレスポンスから必要な情報を抽出し、統一された形式で返します
            # knowledgeBaseArnはオプションのため、存在しない場合は空文字列を返します
            return {
                "knowledge_base_id": response["knowledgeBaseId"],  # 作成されたKnowledge BaseのID
                "status": response["knowledgeBaseStatus"],  # Knowledge Baseのステータス（通常は"CREATING"）
                "arn": response.get("knowledgeBaseArn", ""),  # Knowledge BaseのARN（オプション）
            }
        except ClientError as e:
            # エラーをログに記録して再発生
            # AWS API呼び出しでエラーが発生した場合、エラー情報をログに記録し、
            # エラーハンドリングデコレータ（handle_errors）が適切に処理できるように再発生させます
            logger.error(f"Error creating knowledge base: {e}")
            raise

    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        すべてのKnowledge Baseの一覧を取得します。
        
        ページネーションを使用して、すべてのKnowledge Baseを取得します。
        
        Returns:
            List[Dict[str, Any]]: Knowledge Baseの詳細情報のリスト
                各要素には以下の情報が含まれます:
                - knowledgeBaseId: Knowledge BaseのID
                - name: Knowledge Baseの名前
                - status: Knowledge Baseのステータス
                - description: Knowledge Baseの説明（オプション）
                - updatedAt: 最終更新日時
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        """
        try:
            knowledge_bases = []
            
            # ページネーターを取得（複数ページの結果を自動的に処理）
            # AWS APIはページネーションを使用して結果を返すため、
            # paginatorを使用することで、すべてのページを自動的に処理できます
            paginator = self.bedrock_agent.get_paginator("list_knowledge_bases")
            
            # すべてのページをループして結果を収集
            # paginate()メソッドは、すべてのページを順番に返すイテレータを返します
            # 各ページには、knowledgeBaseSummariesというキーにKnowledge Baseのサマリー情報が含まれます
            for page in paginator.paginate():
                # 各ページからKnowledge Baseサマリーを取得してリストに追加
                # ページにknowledgeBaseSummariesキーがない場合（空のページなど）は空リストを返します
                knowledge_bases.extend(page.get("knowledgeBaseSummaries", []))
            
            # 取得したKnowledge Baseの数をログに記録
            logger.info(f"Retrieved {len(knowledge_bases)} knowledge bases")
            return knowledge_bases
            
        except ClientError as e:
            logger.error(f"Error listing knowledge bases: {e}")
            raise

    def get_knowledge_base(self, knowledge_base_id: str) -> Dict[str, Any]:
        """
        特定のKnowledge Baseの詳細情報を取得します。
        
        Knowledge Baseの設定、ステータス、ストレージ設定などの
        詳細な情報を取得します。

        Args:
            knowledge_base_id: Knowledge BaseのID

        Returns:
            Dict[str, Any]: Knowledge Baseの詳細情報
                - id: Knowledge BaseのID
                - name: Knowledge Baseの名前
                - status: Knowledge Baseのステータス
                - description: Knowledge Baseの説明
                - roleArn: 使用されているIAMロールのARN
                - storageConfiguration: ストレージ設定
                - knowledgeBaseArn: Knowledge BaseのARN
                - createdAt: 作成日時
                - updatedAt: 最終更新日時
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        """
        try:
            # AWS Bedrock APIを呼び出してKnowledge Baseの詳細を取得
            response = self.bedrock_agent.get_knowledge_base(
                knowledgeBaseId=knowledge_base_id
            )
            
            # 取得成功をログに記録
            logger.info(f"Retrieved knowledge base: {knowledge_base_id}")
            
            # Knowledge Baseの詳細情報を返す
            return response["knowledgeBase"]
        except ClientError as e:
            logger.error(f"Error getting knowledge base {knowledge_base_id}: {e}")
            raise

    def update_knowledge_base(
        self,
        knowledge_base_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        role_arn: Optional[str] = None,
    ) -> KnowledgeBaseResponseDict:
        """
        Knowledge Baseの情報を更新します。
        
        Knowledge Baseの名前、説明、IAMロールを更新できます。
        Noneが指定されたパラメータは更新されません（既存の値が保持されます）。

        Args:
            knowledge_base_id: 更新対象のKnowledge BaseのID
            name: 新しい名前（オプション、Noneの場合は更新されない）
            description: 新しい説明（オプション、Noneの場合は更新されない）
            role_arn: 新しいIAMロールARN（オプション、Noneの場合は更新されない）

        Returns:
            KnowledgeBaseResponseDict: 更新されたKnowledge Baseのステータス
                - knowledge_base_id: Knowledge BaseのID
                - status: Knowledge Baseのステータス
                - arn: Knowledge BaseのARN（オプション、更新時は含まれない場合がある）
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        
        Note:
            少なくとも1つのパラメータ（name、description、role_arn）を
            指定する必要があります。
        """
        try:
            # 更新パラメータを構築（指定されたパラメータのみを含める）
            update_params = {"knowledgeBaseId": knowledge_base_id}
            
            # 指定されたパラメータを追加
            if name:
                update_params["name"] = name
            if description:
                update_params["description"] = description
            if role_arn:
                update_params["roleArn"] = role_arn

            # AWS Bedrock APIを呼び出してKnowledge Baseを更新
            response = self.bedrock_agent.update_knowledge_base(**update_params)
            
            # 更新成功をログに記録
            logger.info(f"Updated knowledge base: {knowledge_base_id}")
            
            # 更新結果を整形して返す
            # 更新APIのレスポンスにはarnが含まれない場合があるため、Optionalとして扱います
            return {
                "knowledge_base_id": response["knowledgeBase"]["id"],
                "status": response["knowledgeBase"]["status"],
                "arn": response["knowledgeBase"].get("knowledgeBaseArn"),  # オプション
            }
        except ClientError as e:
            logger.error(f"Error updating knowledge base {knowledge_base_id}: {e}")
            raise

    def delete_knowledge_base(self, knowledge_base_id: str) -> Dict[str, Any]:
        """
        Knowledge Baseを削除します。
        
        注意: この操作は取り消せません。Knowledge Baseとその関連リソースが
        完全に削除されます。

        Args:
            knowledge_base_id: 削除対象のKnowledge BaseのID

        Returns:
            Dict[str, Any]: 削除ステータス
                - status: 削除ステータス（"deleted"）
                - knowledge_base_id: 削除されたKnowledge BaseのID
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        
        Warning:
            この操作は永続的です。削除されたKnowledge Baseは復元できません。
            関連するデータソースや取り込みジョブの履歴も削除される場合があります。
        """
        try:
            # AWS Bedrock APIを呼び出してKnowledge Baseを削除
            self.bedrock_agent.delete_knowledge_base(knowledgeBaseId=knowledge_base_id)
            
            # 削除成功をログに記録
            logger.info(f"Deleted knowledge base: {knowledge_base_id}")
            
            # 削除結果を返す
            return {"status": "deleted", "knowledge_base_id": knowledge_base_id}
        except ClientError as e:
            logger.error(f"Error deleting knowledge base {knowledge_base_id}: {e}")
            raise

    def create_data_source(
        self,
        knowledge_base_id: str,
        name: str,
        data_source_configuration: Dict[str, Any],
        vector_ingestion_configuration: Optional[Dict[str, Any]] = None,
    ) -> DataSourceResponseDict:
        """
        Knowledge Baseにデータソースを作成します。
        
        データソースは、Knowledge Baseがデータを取得する場所を定義します。
        通常はS3バケットを指定します。

        Args:
            knowledge_base_id: データソースを追加するKnowledge BaseのID
            name: データソースの名前
            data_source_configuration: データソース設定の辞書
                - type: データソースタイプ（現在は"S3"のみサポート）
                - s3Configuration: S3設定
                    - bucketArn: S3バケットARN
                    - inclusionPrefixes (オプション): 含めるS3プレフィックスのリスト
            vector_ingestion_configuration: ベクトル取り込み設定の辞書（オプション）
                - parsingConfiguration: パーシング設定（オプション）
                - chunkingConfiguration: チャンキング設定（オプション）
        
        Returns:
            DataSourceResponseDict: データソースの作成結果
                - data_source_id: 作成されたデータソースのID
                - status: データソースのステータス
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        """
        try:
            # API呼び出しパラメータを構築
            api_params = {
                "knowledgeBaseId": knowledge_base_id,
                "name": name,
                "dataSourceConfiguration": data_source_configuration,
            }
            
            # ベクトル取り込み設定が指定されている場合は追加
            # パーシング設定やチャンキング設定を含むことができます
            if vector_ingestion_configuration:
                api_params["vectorIngestionConfiguration"] = vector_ingestion_configuration
            
            # AWS Bedrock APIを呼び出してデータソースを作成
            response = self.bedrock_agent.create_data_source(**api_params)
            
            # 作成成功をログに記録
            logger.info(
                f"Created data source {response['dataSource']['id']} for KB {knowledge_base_id}"
            )
            
            # レスポンスを整形して返す
            return {
                "data_source_id": response["dataSource"]["id"],
                "status": response["dataSource"]["status"],
            }
        except ClientError as e:
            logger.error(f"Error creating data source: {e}")
            raise

    def list_data_sources(self, knowledge_base_id: str) -> List[Dict[str, Any]]:
        """
        指定されたKnowledge Baseのデータソース一覧を取得します。
        
        ページネーションを使用して、すべてのデータソースを取得します。

        Args:
            knowledge_base_id: Knowledge BaseのID

        Returns:
            List[Dict[str, Any]]: データソースの詳細情報のリスト
                各要素には以下の情報が含まれます:
                - id: データソースのID
                - name: データソースの名前
                - status: データソースのステータス
                - description: データソースの説明（オプション）
                - updatedAt: 最終更新日時
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        """
        try:
            data_sources = []
            
            # ページネーターを取得（複数ページの結果を自動的に処理）
            paginator = self.bedrock_agent.get_paginator("list_data_sources")
            
            # すべてのページをループして結果を収集
            for page in paginator.paginate(knowledgeBaseId=knowledge_base_id):
                # 各ページからデータソースサマリーを取得してリストに追加
                data_sources.extend(page.get("dataSourceSummaries", []))
            
            # 取得したデータソースの数をログに記録
            logger.info(f"Retrieved {len(data_sources)} data sources for KB {knowledge_base_id}")
            return data_sources
        except ClientError as e:
            logger.error(f"Error listing data sources for KB {knowledge_base_id}: {e}")
            raise

    def delete_data_source(
        self, knowledge_base_id: str, data_source_id: str
    ) -> Dict[str, Any]:
        """
        データソースを削除します。
        
        注意: この操作は取り消せません。データソースが削除されると、
        そのデータソースからのデータ取り込みは行われなくなります。

        Args:
            knowledge_base_id: Knowledge BaseのID
            data_source_id: 削除対象のデータソースのID

        Returns:
            Dict[str, Any]: 削除ステータス
                - status: 削除ステータス（"deleted"）
                - data_source_id: 削除されたデータソースのID
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        
        Warning:
            この操作は永続的です。削除されたデータソースは復元できません。
        """
        try:
            # AWS Bedrock APIを呼び出してデータソースを削除
            self.bedrock_agent.delete_data_source(
                knowledgeBaseId=knowledge_base_id, dataSourceId=data_source_id
            )
            
            # 削除成功をログに記録
            logger.info(f"Deleted data source {data_source_id} from KB {knowledge_base_id}")
            
            # 削除結果を返す
            return {"status": "deleted", "data_source_id": data_source_id}
        except ClientError as e:
            logger.error(f"Error deleting data source {data_source_id}: {e}")
            raise

    def start_ingestion_job(
        self, knowledge_base_id: str, data_source_id: str
    ) -> IngestionJobResponseDict:
        """
        データソースからKnowledge Baseへのデータ取り込みジョブを開始します。
        
        このジョブは非同期で実行され、データソース内のドキュメントを
        Knowledge Baseに取り込みます。取り込みには時間がかかる場合があります。

        Args:
            knowledge_base_id: Knowledge BaseのID
            data_source_id: データソースのID

        Returns:
            IngestionJobResponseDict: 取り込みジョブの開始結果
                - ingestion_job_id: 開始された取り込みジョブのID
                - status: ジョブのステータス（通常は "STARTING" または "IN_PROGRESS"）
                - statistics: 統計情報（オプション、ジョブ開始時は通常None）
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        
        Note:
            取り込みジョブは非同期で実行されるため、この関数は即座に返ります。
            ジョブの進捗を確認するには、`get_ingestion_job`を使用してください。
        """
        try:
            # AWS Bedrock APIを呼び出して取り込みジョブを開始
            response = self.bedrock_agent.start_ingestion_job(
                knowledgeBaseId=knowledge_base_id, dataSourceId=data_source_id
            )
            
            # ジョブ開始成功をログに記録
            logger.info(
                f"Started ingestion job {response['ingestionJob']['ingestionJobId']} "
                f"for data source {data_source_id}"
            )
            
            # レスポンスを整形して返す
            return {
                "ingestion_job_id": response["ingestionJob"]["ingestionJobId"],
                "status": response["ingestionJob"]["status"],
            }
        except ClientError as e:
            logger.error(f"Error starting ingestion job: {e}")
            raise

    def get_ingestion_job(
        self, knowledge_base_id: str, data_source_id: str, ingestion_job_id: str
    ) -> IngestionJobResponseDict:
        """
        取り込みジョブのステータスと詳細情報を取得します。
        
        取り込みジョブの進捗状況、統計情報、エラー情報などを取得できます。
        ジョブの完了を待つために、この関数を定期的に呼び出すことができます。

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
            ClientError: AWS API呼び出しが失敗した場合
        """
        try:
            # AWS Bedrock APIを呼び出して取り込みジョブの詳細を取得
            response = self.bedrock_agent.get_ingestion_job(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id,
            )
            
            # 取得成功をログに記録
            logger.info(f"Retrieved ingestion job {ingestion_job_id}")
            
            # ジョブ情報を抽出
            job = response["ingestionJob"]
            
            # レスポンスを整形して返す
            return {
                "ingestion_job_id": job["ingestionJobId"],
                "status": job["status"],
                "statistics": job.get("statistics", {}),  # 統計情報はオプション
            }
        except ClientError as e:
            logger.error(f"Error getting ingestion job {ingestion_job_id}: {e}")
            raise

    def retrieve(
        self,
        knowledge_base_id: str,
        query: str,
        number_of_results: int = 5,
    ) -> RetrieveResponseDict:
        """
        Knowledge Baseに対してRAG（Retrieval-Augmented Generation）クエリを実行します。
        
        ベクトル検索を使用して、クエリに関連するドキュメントを取得します。
        
        Args:
            knowledge_base_id: クエリ対象のKnowledge BaseのID
            query: 検索クエリのテキスト
            number_of_results: 返す結果の数（デフォルト: 5、最大: 100）
        
        Returns:
            RetrieveResponseDict: クエリ結果
                - results: 検索結果のリスト
                    各結果には以下の情報が含まれます:
                    - content: ドキュメントの内容
                    - location: ドキュメントの場所（S3 URIなど）
                    - score: 関連度スコア
                    - metadata: メタデータ
                - query: 実行したクエリテキスト
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
        """
        try:
            # Bedrock Agent Runtime APIを使用してRAGクエリを実行
            # retrieve APIは、Knowledge Baseに対してベクトル検索を実行し、
            # クエリに関連するドキュメントチャンクを返します
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=knowledge_base_id,  # クエリ対象のKnowledge BaseのID
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": number_of_results,  # 返す結果の数（1-100の範囲）
                        # オプション: "overrideSearchType": "HYBRID"  # ハイブリッド検索（将来の拡張）
                        # オプション: "filter": {...}  # メタデータフィルター（将来の拡張）
                    }
                },
                retrievalQuery={"text": query},  # 検索クエリのテキスト
                # オプション: nextToken: ページネーション用のトークン（大量の結果がある場合）
            )
            
            # 取得した結果の数をログに記録
            # 検索結果の数をログに記録します（デバッグや監視に有用）
            retrieval_results = response.get("retrievalResults", [])
            logger.info(f"Retrieved {len(retrieval_results)} results")
            
            # レスポンスを整形して返す
            # AWS APIのレスポンスから検索結果を抽出し、クエリテキストと一緒に返します
            # 各結果には、content（テキスト内容）、location（S3 URIなど）、score（関連度）、metadataが含まれます
            return {
                "results": retrieval_results,  # 検索結果のリスト（関連度順にソート済み）
                "query": query,  # 実行したクエリテキスト（確認用）
            }
        except ClientError as e:
            logger.error(f"Error retrieving from knowledge base: {e}")
            raise

    def upload_document_to_s3(
        self, local_file_path: str, bucket_name: str, s3_key: str
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
            ClientError: AWS API呼び出しが失敗した場合
                例: バケットが存在しない、権限がない、ファイルが大きすぎるなど
        """
        try:
            # S3クライアントを使用してファイルをアップロード
            self.s3_client.upload_file(local_file_path, bucket_name, s3_key)
            
            # S3 URIを構築
            s3_uri = f"s3://{bucket_name}/{s3_key}"
            
            # アップロード成功をログに記録
            logger.info(f"Uploaded document to {s3_uri}")
            
            # アップロード結果を返す
            return {"s3_uri": s3_uri, "status": "uploaded"}
        except ClientError as e:
            logger.error(f"Error uploading document to S3: {e}")
            raise

    def list_s3_documents(
        self, bucket_name: str, prefix: str = ""
    ) -> List[Dict[str, Any]]:
        """
        S3バケット内のドキュメント一覧を取得します。
        
        ページネーションを使用して、すべてのドキュメントを取得します。
        指定されたプレフィックス（フォルダ）に一致するドキュメントのみを
        取得することもできます。

        Args:
            bucket_name: S3バケット名
            prefix: フィルタリングするS3プレフィックス（オプション）
                    例: "documents/" を指定すると、documents/フォルダ内の
                        ファイルのみが返されます

        Returns:
            List[Dict[str, Any]]: ドキュメントの詳細情報のリスト
                各要素には以下の情報が含まれます:
                - key: S3オブジェクトキー（ファイルパス）
                - size: ファイルサイズ（バイト）
                - last_modified: 最終更新日時（ISO形式）
        
        Raises:
            ClientError: AWS API呼び出しが失敗した場合
                例: バケットが存在しない、権限がないなど
        
        Note:
            大量のドキュメントがある場合、この関数の実行に時間がかかる場合があります。
        """
        try:
            documents = []
            
            # ページネーターを取得（複数ページの結果を自動的に処理）
            paginator = self.s3_client.get_paginator("list_objects_v2")
            
            # すべてのページをループして結果を収集
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                # 各ページからオブジェクト情報を取得
                for obj in page.get("Contents", []):
                    # ドキュメント情報を整形してリストに追加
                    documents.append(
                        {
                            "key": obj["Key"],  # S3オブジェクトキー
                            "size": obj["Size"],  # ファイルサイズ（バイト）
                            "last_modified": obj["LastModified"].isoformat(),  # ISO形式の日時
                        }
                    )
            
            # 取得したドキュメントの数をログに記録
            logger.info(f"Retrieved {len(documents)} documents from S3")
            return documents
        except ClientError as e:
            logger.error(f"Error listing S3 documents: {e}")
            raise

