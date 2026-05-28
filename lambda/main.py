"""LINE じゃんけん Bot — AWS Lambda エントリーポイント"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import random
from typing import Any

import requests

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_REPLY_ENDPOINT = "https://api.line.me/v2/bot/message/reply"

COMMAND_PREFIX = "/janken"
HANDS = ["✊", "✌", "✋"]
MAX_PLAYERS = 10


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """API Gateway からの Webhook を受ける Lambda ハンドラー"""
    body = event.get("body", "") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    signature = event.get("headers", {}).get("x-line-signature", "")
    if not _verify_signature(body, signature):
        return {"statusCode": 403, "body": json.dumps({"error": "invalid signature"})}

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "invalid json"})}

    for line_event in payload.get("events", []):
        _handle_event(line_event)

    return {"statusCode": 200, "body": json.dumps({"status": "ok"})}


def _verify_signature(body: str, signature: str) -> bool:
    """X-Line-Signature ヘッダーを検証"""
    if not signature:
        return False
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(signature, expected)


def _handle_event(line_event: dict[str, Any]) -> None:
    """LINE のイベントを処理してテキストコマンドに応答"""
    if line_event.get("type") != "message":
        return

    message = line_event.get("message", {})
    if message.get("type") != "text":
        return

    text: str = message.get("text", "").strip()
    if not text.startswith(COMMAND_PREFIX):
        return

    reply_token = line_event.get("replyToken")
    if not reply_token:
        return

    args = text[len(COMMAND_PREFIX):].split()
    reply = _build_reply(args)
    _send_reply(reply_token, reply)


def _build_reply(players: list[str]) -> dict[str, Any]:
    """コマンド引数からじゃんけん結果 or ヘルプを生成"""
    if not players:
        return _text_message(
            "使い方: /janken 太郎 花子 次郎\n"
            f"2人以上 {MAX_PLAYERS}人以下で名前を指定してください。"
        )
    if len(players) < 2:
        return _text_message("2人以上指定してください。")
    if len(players) > MAX_PLAYERS:
        return _text_message(f"{MAX_PLAYERS}人以下にしてください。")
    if len(set(players)) != len(players):
        return _text_message("同じ名前が含まれています。別の名前を指定してください。")

    results = _play_until_winner(players)
    winners = _determine_winners(results)
    return _flex_result(players, results, winners)


def _play_until_winner(players: list[str]) -> dict[str, str]:
    """あいこにならない結果が出るまで抽選"""
    while True:
        results = {player: random.choice(HANDS) for player in players}
        unique_hands = set(results.values())
        # 全員同じ手 or 3種類全部出たらあいこ
        if len(unique_hands) != 1 and len(unique_hands) != 3:
            return results


def _determine_winners(results: dict[str, str]) -> list[str]:
    """勝者を判定"""
    hand_map = {"✊": "rock", "✌": "scissors", "✋": "paper"}
    beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    normalized = {player: hand_map[hand] for player, hand in results.items()}

    winners: list[str] = []
    for player, hand in normalized.items():
        is_winner = all(
            other == player or hand == other_hand or beats[hand] == other_hand
            for other, other_hand in normalized.items()
        )
        if is_winner:
            winners.append(player)
    return winners


def _flex_result(
    players: list[str],
    results: dict[str, str],
    winners: list[str],
) -> dict[str, Any]:
    """じゃんけん結果の Flex Message を組み立てる"""
    player_boxes = [_player_box(p, results[p], p in winners) for p in players]
    return {
        "type": "flex",
        "altText": "じゃんけん結果",
        "contents": {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "じゃんけん結果",
                        "size": "lg",
                        "align": "center",
                        "weight": "bold",
                        "color": "#FCD34D",
                    }
                ],
                "backgroundColor": "#0F172A",
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": player_boxes,
                "paddingAll": "lg",
                "spacing": "sm",
                "background": {
                    "type": "linearGradient",
                    "angle": "180deg",
                    "startColor": "#0F172A",
                    "endColor": "#1E1B4B",
                },
            },
        },
    }


def _player_box(name: str, hand: str, is_winner: bool) -> dict[str, Any]:
    """各プレイヤーの表示用ボックス（勝者・敗者で同サイズ、色のみ差分）"""
    name_color = "#FCD34D" if is_winner else "#94A3B8"
    border_color = "#FBBF24" if is_winner else "#1E293B"
    bg_color = "#1E293B" if is_winner else "#0F172A"

    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {
                "type": "text",
                "text": name,
                "size": "lg",
                "weight": "bold",
                "color": name_color,
                "flex": 1,
                "gravity": "center",
            },
            {
                "type": "text",
                "text": hand,
                "size": "xxl",
                "align": "end",
                "flex": 0,
                "gravity": "center",
            },
        ],
        "backgroundColor": bg_color,
        "borderColor": border_color,
        "borderWidth": "1px",
        "cornerRadius": "md",
        "paddingAll": "md",
    }


def _text_message(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _send_reply(reply_token: str, message: dict[str, Any]) -> None:
    """LINE Reply API でメッセージを送信"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {"replyToken": reply_token, "messages": [message]}
    response = requests.post(LINE_REPLY_ENDPOINT, headers=headers, json=payload, timeout=10)
    if response.status_code != 200:
        print(f"LINE reply failed [{response.status_code}]: {response.text}")
