from __future__ import annotations

import argparse
from pathlib import Path

from awcollector.audit import AuditLog
from awcollector.ocr import ScriptedOCREngine, load_ocr_engine
from awcollector.permit import PermitError, load_permit
from awcollector.pipeline import run_task, session_from_html_file, write_record
from awcollector.task_loader import load_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="awc",
        description="授权范围内的政务网页采集（DOM 优先，OCR 兜底）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check-permit", help="校验采集许可是否有效")
    check.add_argument("--permit", required=True, help="许可 JSON 路径")

    run = sub.add_parser("run", help="按任务剧本采集")
    run.add_argument("--permit", required=True, help="许可 JSON 路径")
    run.add_argument("--task", required=True, help="任务 YAML 路径")
    run.add_argument("--out", default="out", help="输出目录")
    run.add_argument(
        "--mode",
        choices=("html", "cdp"),
        default="html",
        help="html=本地样例；cdp=挂到已登录的 Chrome",
    )
    run.add_argument("--cdp", default="http://127.0.0.1:9222", help="Chrome 调试地址")
    run.add_argument(
        "--ocr-text",
        default="",
        help="演示用：不装 RapidOCR 时，用这段预置文本模拟 OCR 结果",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check-permit":
        permit = load_permit(args.permit)
        from awcollector.permit import assert_permit_active

        assert_permit_active(permit)
        print(f"许可有效: {permit.permit_id} / {permit.operator} / {permit.organization}")
        print(f"范围: {', '.join(permit.allowed_url_prefixes)}")
        print(f"只读: {permit.read_only}；到期: {permit.expires_at.isoformat()}")
        return 0

    permit = load_permit(args.permit)
    task = load_task(args.task)
    out = Path(args.out)
    audit = AuditLog(out / "audit.jsonl")

    if args.mode == "html":
        if not task.html_file:
            raise SystemExit("html 模式需要任务里配置 html_file")
        session = session_from_html_file(task.html_file, task.start_url)
    else:
        from awcollector.browser import connect_existing_chrome

        session = connect_existing_chrome(args.cdp)

    ocr = ScriptedOCREngine(args.ocr_text) if args.ocr_text else load_ocr_engine()
    try:
        record = run_task(permit, task, session, ocr=ocr, audit=audit)
        path = write_record(record, out)
        print(f"采集完成: {path}")
        print(f"来源: {record.source_url}")
        print(f"字段: {', '.join(record.data.keys())}")
        return 0
    except PermitError as exc:
        audit.write("permit_denied", error=str(exc))
        raise SystemExit(f"许可拒绝: {exc}") from exc
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
