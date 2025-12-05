"""
ユーティリティ関数モジュール

設定管理、エラーハンドリング、バリデーションなどの共通機能を提供します。
"""

import json
import logging
import os
import re
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, ParamSpec

import boto3
from botocore.exceptions import ClientError

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

# 型変数の定義
# P: 関数のパラメータ仕様（ParamSpec）
# T: 関数の戻り値の型（TypeVar）
P = ParamSpec('P')
T = TypeVar('T')


def validate_aws_credentials() -> bool:
    """
    AWS認証情報が設定されているか確認します。
    
    環境変数から以下のいずれかが設定されているかを確認します:
    - AWS_PROFILE: AWSプロファイル名
    - AWS_ACCESS_KEY_ID と AWS_SECRET_ACCESS_KEY: アクセスキーとシークレットキー
    
    Returns:
        bool: 常にTrueを返します（認証情報がなくても警告のみで続行）
    
    Note:
        boto3は自動的に認証情報を取得する場合もあるため（例: IAMロール、EC2インスタンスプロファイル）、
        認証情報が明示的に設定されていなくてもエラーにはしません。
    """
    # 環境変数から認証情報の存在を確認
    has_profile = bool(os.getenv("AWS_PROFILE"))
    has_access_key = bool(os.getenv("AWS_ACCESS_KEY_ID"))
    has_secret_key = bool(os.getenv("AWS_SECRET_ACCESS_KEY"))
    
    # プロファイルもアクセスキーも設定されていない場合
    if not has_profile and not (has_access_key and has_secret_key):
        # boto3が自動的に認証情報を取得する場合もあるので、警告のみ
        logger.warning(
            "AWS認証情報が明示的に設定されていません。"
            "AWS_PROFILEまたはAWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEYを設定してください。"
        )
    return True


def get_log_level() -> int:
    """
    環境変数からログレベルを安全に取得します。
    
    環境変数 FASTMCP_LOG_LEVEL からログレベルを取得し、
    無効な値の場合はデフォルトのINFOレベルを返します。
    
    Returns:
        int: loggingモジュールのログレベル定数（logging.DEBUG, logging.INFO等）
    
    Environment Variables:
        FASTMCP_LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
                          デフォルト値: INFO
    """
    # 環境変数からログレベルを取得（デフォルト: INFO）
    log_level = os.getenv("FASTMCP_LOG_LEVEL", "INFO").upper()
    
    # 有効なログレベルのリスト
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # 無効なログレベルの場合は警告を出してデフォルト値を使用
    if log_level not in valid_levels:
        logger.warning(f"無効なログレベル: {log_level}。INFOを使用します。")
        return logging.INFO
    
    # loggingモジュールから対応するログレベル定数を取得
    return getattr(logging, log_level)


def validate_required_string(value: Optional[str], param_name: str) -> str:
    """
    必須文字列パラメータのバリデーション
    
    Args:
        value: 検証する文字列値（Noneまたは空文字列の可能性がある）
        param_name: パラメータ名（エラーメッセージ用）
    
    Returns:
        str: 前後の空白を削除した文字列
    
    Raises:
        ValueError: 値がNone、空文字列、または空白のみの場合
    """
    if not value or not value.strip():
        raise ValueError(f"{param_name} is required")
    return value.strip()


def handle_errors(func: Callable[P, T]) -> Callable[P, Dict[str, Any]]:
    """
    エラーハンドリングデコレータ
    
    関数の実行中に発生したエラーをキャッチし、統一された形式のエラーレスポンスを返します。
    AWS APIのエラーコードに応じて適切な日本語メッセージを提供します。
    
    Args:
        func: エラーハンドリングを適用する関数
    
    Returns:
        デコレートされた関数。常に辞書形式のレスポンスを返します。
    
    Example:
        @handle_errors
        def my_function():
            # 関数の実装
            return {"result": "success"}
    """
    @wraps(func)  # 元の関数のメタデータ（名前、docstringなど）を保持
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Dict[str, Any]:
        """
        ラッパー関数
        
        元の関数を実行し、エラーが発生した場合は適切に処理します。
        すべてのエラーをキャッチし、統一された形式のエラーレスポンスを返します。
        """
        try:
            # 元の関数を実行
            # 関数の実行中にエラーが発生した場合、exceptブロックでキャッチされます
            result = func(*args, **kwargs)
            
            # 結果が既に辞書の場合はそのまま返す
            # MCPツール関数は通常、辞書形式のレスポンスを返すため、そのまま返します
            if isinstance(result, dict):
                return result
            
            # それ以外の場合は辞書にラップ
            # 予期しない型の戻り値の場合、辞書にラップして返します
            # これにより、MCPクライアントが常に辞書形式のレスポンスを受け取ることが保証されます
            return {"result": result}
            
        except ClientError as e:
            # AWS API呼び出し時のエラー（boto3のClientError）
            # ClientErrorは、AWS API呼び出しでエラーが発生した場合に発生します
            # エラーレスポンスからエラーコードとメッセージを抽出します
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # エラーコードに応じた日本語メッセージのマッピング
            # AWS APIのエラーコードを日本語のユーザーフレンドリーなメッセージに変換します
            # これにより、ユーザーがエラーの原因を理解しやすくなります
            error_messages = {
                'AccessDeniedException': 'アクセス権限がありません',
                'ResourceNotFoundException': 'リソースが見つかりません',
                'ValidationException': '入力値が無効です',
                'ConflictException': 'リソースが既に存在するか、競合しています',
                'ThrottlingException': 'リクエストが多すぎます。しばらく待ってから再試行してください',
                'ServiceUnavailableException': 'サービスが一時的に利用できません',
                'InternalServerException': 'サーバー内部エラーが発生しました',
                'InvalidParameterException': 'パラメータが無効です',
                'InvalidRequestException': 'リクエストが無効です',
                'LimitExceededException': 'リソースの制限を超えました',
                'ResourceInUseException': 'リソースが使用中です',
                'TooManyRequestsException': 'リクエストが多すぎます',
                'UnauthorizedException': '認証に失敗しました',
                'BadRequestException': 'リクエストが不正です',
                'NotFoundException': 'リソースが見つかりません',
                'ForbiddenException': 'アクセスが拒否されました',
            }
            
            # エラーコードに対応する日本語メッセージを取得
            # 対応するメッセージがない場合は元のエラーメッセージを使用します
            # これにより、新しいエラーコードが追加されても、少なくとも元のメッセージが返されます
            user_message = error_messages.get(error_code, error_message)
            
            # AWSリクエストIDを取得（デバッグに有用）
            # リクエストIDは、AWSサポートに問い合わせる際に必要です
            request_id = e.response.get('ResponseMetadata', {}).get('RequestId')
            
            # エラーをログに記録（メッセージ内の機密情報は自動的にマスクされる）
            # StructuredFormatterがARNなどの機密情報を自動的にマスクします
            logger.error(
                f"Error in {func.__name__}: {error_code} - {error_message} "
                f"(RequestId: {request_id})"
            )
            
            # 統一されたエラーレスポンス形式で返す
            # すべてのエラーは同じ形式で返されるため、MCPクライアントが一貫して処理できます
            error_response: Dict[str, Any] = {
                "error": user_message,      # ユーザー向けの日本語メッセージ（理解しやすい形式）
                "code": error_code,         # AWSエラーコード（プログラムで処理する場合に使用）
                "details": error_message,   # 詳細なエラーメッセージ（デバッグに有用）
            }
            
            # リクエストIDが存在する場合は追加
            if request_id:
                error_response["request_id"] = request_id
            
            return error_response
            
        except ValueError as e:
            # バリデーションエラー（入力値の検証失敗など）
            # ValueErrorは、入力値が無効な場合に発生します（例: 空の必須パラメータ、範囲外の値など）
            # このエラーは、ユーザーの入力ミスを示すため、詳細なメッセージを返します
            logger.error(f"Validation error in {func.__name__}: {e}")
            return {
                "error": str(e),  # バリデーションエラーのメッセージ（通常は詳細で有用）
                "code": "ValidationError",  # エラータイプを示すコード
            }
            
        except Exception as e:
            # その他の予期しないエラー
            # 上記のエラータイプに該当しない、予期しないエラーをキャッチします
            # exc_info=Trueでスタックトレースもログに記録します
            # これにより、デバッグ時にエラーの発生箇所を特定しやすくなります
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return {
                "error": f"予期しないエラーが発生しました: {str(e)}",  # ユーザー向けのエラーメッセージ
                "code": "InternalError",  # 内部エラーを示すコード
            }
    
    return wrapper


class StructuredFormatter(logging.Formatter):
    """
    構造化ログフォーマッター
    
    JSON形式でログを出力し、機密情報を自動的にマスクします。
    """
    
    # 機密情報としてマスクするキーワードのリスト
    # これらのキーワードを含むログメッセージは、値が自動的にマスクされます
    # セキュリティ上の理由から、認証情報や機密情報がログに出力されないようにします
    SENSITIVE_KEYWORDS = [
        'arn', 'role_arn', 'bucket_arn', 'access_key', 'secret',
        'password', 'token', 'credential', 'authorization',
        'aws_access_key_id', 'aws_secret_access_key', 'session_token'
    ]
    
    # ARNパターン（マスク用）
    # AWS ARN（Amazon Resource Name）の形式を検出するための正規表現パターン
    # 例: arn:aws:s3:::my-bucket や arn:aws:iam::123456789012:role/MyRole
    ARN_PATTERN = re.compile(r'arn:aws:[^:]+:[^:]*:[^:]*:[^:]+')
    
    def format(self, record: logging.LogRecord) -> str:
        """
        ログレコードをJSON形式の文字列に変換します。
        
        Args:
            record: ログレコード
        
        Returns:
            str: JSON形式のログ文字列
        """
        # ログデータの基本構造を作成
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": self._sanitize_message(record.getMessage()),
        }
        
        # 追加のフィールドがある場合は追加
        if hasattr(record, 'funcName'):
            log_data["function"] = record.funcName
        if hasattr(record, 'lineno'):
            log_data["line"] = record.lineno
        if hasattr(record, 'pathname'):
            log_data["path"] = record.pathname
        
        # 例外情報がある場合は追加
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # JSON形式で返す
        return json.dumps(log_data, ensure_ascii=False)
    
    def _sanitize_message(self, message: str) -> str:
        """
        ログメッセージから機密情報をマスクします。
        
        Args:
            message: 元のログメッセージ
        
        Returns:
            str: 機密情報がマスクされたメッセージ
        """
        # ARNをマスク
        # メッセージ内のすべてのARNを検出し、'arn:aws:***MASKED***'に置き換えます
        # これにより、具体的なリソース情報がログに出力されなくなります
        sanitized = self.ARN_PATTERN.sub('arn:aws:***MASKED***', message)
        
        # 機密キーワードを含む値をマスク
        # 機密キーワードリストに含まれるキーワードの値をマスクします
        # 例: "access_key=AKIAIOSFODNN7EXAMPLE" → "access_key=***MASKED***"
        for keyword in self.SENSITIVE_KEYWORDS:
            # キーワード=値のパターンをマスク
            # コロンまたは等号の後に続く値をマスクします
            pattern = re.compile(
                rf'{keyword}\s*[:=]\s*([^\s,}}]+)',  # キーワードの後にコロンまたは等号、その後に値
                re.IGNORECASE  # 大文字小文字を区別しない
            )
            sanitized = pattern.sub(f'{keyword}=***MASKED***', sanitized)
        
        return sanitized


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    辞書データから機密情報をマスクします。
    
    Args:
        data: マスクするデータの辞書
    
    Returns:
        Dict[str, Any]: 機密情報がマスクされた辞書
    """
    sanitized = data.copy()
    sensitive_keys = [
        'arn', 'role_arn', 'bucket_arn', 'access_key', 'secret',
        'password', 'token', 'credential', 'authorization',
        'aws_access_key_id', 'aws_secret_access_key', 'session_token',
        'knowledge_base_id', 'data_source_id', 'ingestion_job_id'
    ]
    
    for key in sanitized.keys():
        # キー名に機密キーワードが含まれている場合
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '***MASKED***'
        # 値がARN形式の場合
        elif isinstance(sanitized[key], str) and sanitized[key].startswith('arn:aws:'):
            sanitized[key] = 'arn:aws:***MASKED***'
    
    return sanitized


def setup_logging(use_structured: bool = None) -> None:
    """
    ロギングを設定します。
    
    Args:
        use_structured: 構造化ログを使用するかどうか
                        Noneの場合は環境変数FASTMCP_STRUCTURED_LOGから取得
                        （デフォルト: False）
    
    Environment Variables:
        FASTMCP_STRUCTURED_LOG: 構造化ログを使用するか（true/false、デフォルト: false）
        FASTMCP_LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    """
    # 既存のハンドラーをクリア
    # ロギング設定をリセットするため、既存のハンドラーをすべて削除します
    # これにより、複数回呼び出された場合でも、重複したハンドラーが追加されません
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:  # スライス[:]でコピーを作成（ループ中に変更されるため）
        root_logger.removeHandler(handler)
        handler.close()  # ハンドラーのリソースを解放
    
    # 構造化ログの使用を決定
    # 環境変数FASTMCP_STRUCTURED_LOGから構造化ログの使用を判断します
    # 構造化ログは、JSON形式で出力され、ログ管理システム（CloudWatch、Datadogなど）で
    # 解析しやすくなります
    if use_structured is None:
        structured_env = os.getenv("FASTMCP_STRUCTURED_LOG", "false").lower()
        use_structured = structured_env in ("true", "1", "yes", "on")  # 複数の形式に対応
    
    # ログレベルを設定
    # 環境変数FASTMCP_LOG_LEVELからログレベルを取得します（デフォルト: INFO）
    log_level = get_log_level()
    root_logger.setLevel(log_level)
    
    # コンソールハンドラーを作成
    # 標準出力（stdout）にログを出力するハンドラーを作成します
    # MCPサーバーは標準入出力を使用するため、コンソールハンドラーが適切です
    handler = logging.StreamHandler()
    handler.setLevel(log_level)  # ハンドラーのログレベルも設定
    
    # フォーマッターを設定
    # 構造化ログを使用する場合はJSON形式、そうでない場合は人間が読みやすい形式を使用します
    if use_structured:
        # 構造化ログフォーマッターを使用
        # JSON形式で出力され、機密情報が自動的にマスクされます
        formatter = StructuredFormatter()
    else:
        # 標準フォーマッターを使用
        # 人間が読みやすい形式で出力されます（例: 2024-01-01 12:00:00 - module - INFO - message）
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # フォーマッターをハンドラーに設定
    handler.setFormatter(formatter)
    # ハンドラーをルートロガーに追加
    root_logger.addHandler(handler)


def get_aws_account_id() -> str:
    """
    AWSアカウントIDを取得します。
    
    boto3のSTS（Security Token Service）を使用して、現在のAWS認証情報に
    紐づくアカウントIDを取得します。
    
    Returns:
        str: AWSアカウントID（12桁の数字）
    
    Raises:
        ClientError: AWS API呼び出しが失敗した場合
        Exception: その他のエラーが発生した場合
    
    Note:
        この関数は初回呼び出し時にAWS APIを呼び出すため、ネットワークアクセスが必要です。
        エラーが発生した場合は、ログに記録されますが、例外を再発生させます。
    """
    try:
        # STSクライアントを作成してアカウントIDを取得
        # get_caller_identity()は、現在の認証情報に紐づくアカウントIDを返します
        sts_client = boto3.client("sts")
        response = sts_client.get_caller_identity()
        account_id = response.get("Account")
        
        if not account_id:
            raise ValueError("Failed to retrieve AWS account ID from STS response")
        
        logger.debug(f"Retrieved AWS account ID: {account_id}")
        return account_id
    except ClientError as e:
        logger.error(f"Error retrieving AWS account ID: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving AWS account ID: {e}")
        raise


def normalize_s3_arn_or_uri(value: str, require_account_id: bool = False) -> str:
    """
    S3 ARNまたはS3 URIを正規化してS3 ARN形式に変換します。
    
    S3 URI形式（s3://bucket-name/path）をS3 ARN形式（arn:aws:s3:::bucket-name）に
    変換します。既にARN形式の場合はそのまま返します。
    
    Args:
        value: S3 ARNまたはS3 URI
            - ARN形式: "arn:aws:s3:::bucket-name"
            - URI形式: "s3://bucket-name" または "s3://bucket-name/path"
        require_account_id: アカウントIDが必要な場合にTrue（現在は未使用、将来の拡張用）
    
    Returns:
        str: 正規化されたS3 ARN形式（arn:aws:s3:::bucket-name）
    
    Raises:
        ValueError: 入力値が無効な形式の場合
    
    Examples:
        >>> normalize_s3_arn_or_uri("s3://my-bucket")
        "arn:aws:s3:::my-bucket"
        >>> normalize_s3_arn_or_uri("s3://my-bucket/path/to/file")
        "arn:aws:s3:::my-bucket"
        >>> normalize_s3_arn_or_uri("arn:aws:s3:::my-bucket")
        "arn:aws:s3:::my-bucket"
    """
    if not value:
        raise ValueError("S3 ARN or URI cannot be empty")
    
    value = value.strip()
    
    # 既にARN形式の場合はそのまま返す
    if value.startswith("arn:aws:s3:::"):
        return value
    
    # S3 URI形式の場合はARN形式に変換
    if value.startswith("s3://"):
        # s3://bucket-name/path から bucket-name を抽出
        # s3:// を削除
        bucket_and_path = value[5:]  # "s3://" の5文字をスキップ
        
        # パス部分を削除（最初のスラッシュ以降を無視）
        bucket_name = bucket_and_path.split("/")[0]
        
        if not bucket_name:
            raise ValueError(f"Invalid S3 URI format: {value}. Bucket name is required.")
        
        # S3バケット名のバリデーション（簡易チェック）
        # S3バケット名は3-63文字、小文字と数字、ハイフン、ピリオドのみ
        if len(bucket_name) < 3 or len(bucket_name) > 63:
            raise ValueError(f"Invalid bucket name length: {bucket_name}. Must be 3-63 characters.")
        
        # ARN形式に変換
        arn = f"arn:aws:s3:::{bucket_name}"
        logger.debug(f"Converted S3 URI '{value}' to ARN '{arn}'")
        return arn
    
    # どちらの形式でもない場合はエラー
    raise ValueError(
        f"Invalid S3 ARN or URI format: {value}. "
        "Must be either 'arn:aws:s3:::bucket-name' or 's3://bucket-name'"
    )


def normalize_iam_role_arn(value: str) -> str:
    """
    IAMロールARNを正規化します。
    
    IAMロールARNにアカウントIDが含まれていない場合（例: "arn:aws:iam::role/MyRole"）、
    AWSアカウントIDを取得して補完します。
    
    Args:
        value: IAMロールARN
            - 完全な形式: "arn:aws:iam::123456789012:role/MyRole"
            - アカウントIDなし: "arn:aws:iam::role/MyRole" または "role/MyRole"
    
    Returns:
        str: 正規化されたIAMロールARN（arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME）
    
    Raises:
        ValueError: 入力値が無効な形式の場合
        ClientError: AWSアカウントIDの取得に失敗した場合
    
    Examples:
        >>> normalize_iam_role_arn("arn:aws:iam::123456789012:role/MyRole")
        "arn:aws:iam::123456789012:role/MyRole"
        >>> normalize_iam_role_arn("arn:aws:iam::role/MyRole")
        "arn:aws:iam::<ACCOUNT_ID>:role/MyRole"  # アカウントIDが補完される
    """
    if not value:
        raise ValueError("IAM role ARN cannot be empty")
    
    value = value.strip()
    
    # 完全なARN形式の場合はそのまま返す
    # arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME の形式
    arn_pattern = r"^arn:aws:iam::(\d{12}):role/(.+)$"
    match = re.match(arn_pattern, value)
    if match:
        account_id, role_name = match.groups()
        return value  # 既に完全な形式
    
    # アカウントIDが欠けているARN形式の場合（arn:aws:iam::role/ROLE_NAME）
    if value.startswith("arn:aws:iam::role/"):
        role_name = value.replace("arn:aws:iam::role/", "")
        account_id = get_aws_account_id()
        normalized_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        logger.debug(f"Normalized IAM role ARN '{value}' to '{normalized_arn}'")
        return normalized_arn
    
    # role/ROLE_NAME 形式の場合
    if value.startswith("role/"):
        role_name = value.replace("role/", "")
        account_id = get_aws_account_id()
        normalized_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        logger.debug(f"Normalized IAM role ARN '{value}' to '{normalized_arn}'")
        return normalized_arn
    
    # どちらの形式でもない場合はエラー
    raise ValueError(
        f"Invalid IAM role ARN format: {value}. "
        "Must be either 'arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME' or 'role/ROLE_NAME'"
    )

