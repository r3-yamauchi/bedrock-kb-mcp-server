"""
型定義モジュール

TypedDictを使用したレスポンス型の定義を提供します。
これにより、IDEの補完機能が向上し、型安全性が確保されます。
"""

from typing import TypedDict, List, Dict, Any, Optional


class KnowledgeBaseResponseDict(TypedDict):
    """Knowledge Base作成/更新のレスポンス型"""
    knowledge_base_id: str
    status: str
    arn: Optional[str]


class KnowledgeBaseListResponseDict(TypedDict):
    """Knowledge Base一覧のレスポンス型"""
    count: int
    knowledge_bases: List[Dict[str, Any]]


class KnowledgeBaseDetailDict(TypedDict):
    """Knowledge Base詳細情報の型"""
    id: str
    name: str
    status: str
    description: Optional[str]
    arn: Optional[str]


class DataSourceResponseDict(TypedDict):
    """データソース作成のレスポンス型"""
    data_source_id: str
    status: str


class DataSourceListResponseDict(TypedDict):
    """データソース一覧のレスポンス型"""
    count: int
    data_sources: List[Dict[str, Any]]


class IngestionJobResponseDict(TypedDict):
    """取り込みジョブのレスポンス型"""
    ingestion_job_id: str
    status: str
    statistics: Optional[Dict[str, Any]]


class RetrieveResponseDict(TypedDict):
    """RAGクエリのレスポンス型"""
    results: List[Dict[str, Any]]
    query: str


class S3UploadResponseDict(TypedDict):
    """S3アップロードのレスポンス型"""
    s3_uri: str
    status: str


class S3DocumentListResponseDict(TypedDict):
    """S3ドキュメント一覧のレスポンス型"""
    count: int
    bucket: str
    prefix: str
    documents: List[Dict[str, Any]]


class S3BucketCreateResponseDict(TypedDict):
    """S3バケット作成のレスポンス型"""
    bucket_name: str
    region: str
    arn: str
    status: str


class IAMRoleCreateResponseDict(TypedDict):
    """IAMロール作成のレスポンス型"""
    role_name: str
    role_arn: str
    path: str
    status: str


class ErrorResponseDict(TypedDict):
    """エラーレスポンスの型"""
    error: str
    code: str
    details: Optional[str]
    request_id: Optional[str]


