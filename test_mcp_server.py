#!/usr/bin/env python3
"""
MCP Serverの動作確認用スクリプト

このスクリプトは、MCP Serverが正常に起動し、リクエストに応答できることを確認します。
"""

import json
import subprocess
import sys
import os

def test_mcp_server():
    """MCP Serverにリクエストを送信してテスト"""
    
    print("=" * 60)
    print("MCP Server 動作確認テスト")
    print("=" * 60)
    print()
    
    # 利用可能なツールをリストアップするリクエスト
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    print("1. リクエストを送信:")
    print(json.dumps(request, indent=2, ensure_ascii=False))
    print()
    
    # サーバーを起動してリクエストを送信
    try:
        process = subprocess.Popen(
            ["uv", "run", "bedrock-kb-mcp-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        # リクエストを送信（改行を追加）
        request_json = json.dumps(request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=10)
        
        print("2. サーバーの応答:")
        print("-" * 60)
        
        if stdout:
            print("STDOUT:")
            print(stdout)
            print()
            
            # レスポンスをパース
            try:
                # 複数行のレスポンスがある場合、最初のJSONをパース
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        response = json.loads(line)
                        print("3. パースされたレスポンス:")
                        print(json.dumps(response, indent=2, ensure_ascii=False))
                        
                        # ツールのリストを表示
                        if "result" in response and "tools" in response["result"]:
                            tools = response["result"]["tools"]
                            print()
                            print(f"4. 利用可能なツール数: {len(tools)}")
                            print()
                            print("ツール一覧:")
                            for i, tool in enumerate(tools, 1):
                                print(f"  {i}. {tool.get('name', 'Unknown')}")
                                if 'description' in tool:
                                    desc = tool['description'][:50] + "..." if len(tool['description']) > 50 else tool['description']
                                    print(f"     説明: {desc}")
                        break
            except json.JSONDecodeError as e:
                print(f"JSONパースエラー: {e}")
                print(f"生の出力: {stdout}")
        
        if stderr:
            print("STDERR:")
            print(stderr)
            print()
        
        # プロセスの終了コードを確認
        return_code = process.returncode
        if return_code == 0:
            print("✅ サーバーは正常に終了しました")
        else:
            print(f"⚠️  サーバーの終了コード: {return_code}")
        
    except subprocess.TimeoutExpired:
        print("⏱️  タイムアウト: サーバーが10秒以内に応答しませんでした")
        process.kill()
    except FileNotFoundError:
        print("❌ エラー: 'uv'コマンドが見つかりません")
        print("   uvをインストールしてください: https://github.com/astral-sh/uv")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mcp_server()

